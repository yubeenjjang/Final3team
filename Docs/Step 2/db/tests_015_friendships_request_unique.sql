-- -v applied=true|false -v probe_duplicate=true|false.
-- probe_duplicate=true일 때는 같은 세션에서 사전 검사와 015를 이어 실행한다.
BEGIN;

INSERT INTO public.users (user_id, email, password_hash)
VALUES
  ('00000000-0000-0000-0000-000000015001', 't015a@example.invalid', '!'),
  ('00000000-0000-0000-0000-000000015002', 't015b@example.invalid', '!'),
  ('00000000-0000-0000-0000-000000015003', 't015c@example.invalid', '!');

INSERT INTO public.friend_requests (request_id, from_user, to_user, status, responded_at)
VALUES ('frq_T01501', '00000000-0000-0000-0000-000000015001',
        '00000000-0000-0000-0000-000000015002', 'accepted', now());

INSERT INTO public.friendships (user_a, user_b, request_id)
VALUES ('00000000-0000-0000-0000-000000015001',
        '00000000-0000-0000-0000-000000015002', 'frq_T01501');

\if :applied
DO $$
DECLARE
  failed_constraint text;
BEGIN
  BEGIN
    INSERT INTO public.friendships (user_a, user_b, request_id)
    VALUES ('00000000-0000-0000-0000-000000015001',
            '00000000-0000-0000-0000-000000015003', 'frq_T01501');
    RAISE EXCEPTION 'T015a FAIL: 다른 친구 쌍이 같은 신청을 참조했습니다';
  EXCEPTION WHEN unique_violation THEN
    GET STACKED DIAGNOSTICS failed_constraint = CONSTRAINT_NAME;
    IF failed_constraint IS DISTINCT FROM 'friendships_request_id_key' THEN
      RAISE;
    END IF;
  END;
  RAISE NOTICE 'T015a PASS: 같은 신청을 참조하는 두 번째 관계 거부';
END $$;

INSERT INTO public.friendships (user_a, user_b)
VALUES
  ('00000000-0000-0000-0000-000000015001', '00000000-0000-0000-0000-000000015003'),
  ('00000000-0000-0000-0000-000000015002', '00000000-0000-0000-0000-000000015003');
\echo 'T015b PASS: request_id가 NULL인 관계를 여러 건 허용'
\else
INSERT INTO public.friendships (user_a, user_b, request_id)
VALUES ('00000000-0000-0000-0000-000000015001',
        '00000000-0000-0000-0000-000000015003', 'frq_T01501');
\if :probe_duplicate
-- 중복 행을 유지한 채 사전 검사와 적용 SQL을 실행한다.
\else
DO $$
BEGIN
  BEGIN
    UPDATE public.friendships SET request_id = 'frq_T01599' WHERE request_id = 'frq_T01501';
    RAISE EXCEPTION 'T015c FAIL: 되돌리기 후 존재하지 않는 신청 ID가 허용되었습니다';
  EXCEPTION WHEN foreign_key_violation THEN
    NULL;
  END;
  RAISE NOTICE 'T015c PASS: 되돌리기 후 UNIQUE 제거·외래키 유지';
END $$;
\endif
\endif

\if :probe_duplicate
-- 015 적용 실패 시 연결이 닫히면서 시험 행도 롤백된다.
\else
ROLLBACK;
\endif
