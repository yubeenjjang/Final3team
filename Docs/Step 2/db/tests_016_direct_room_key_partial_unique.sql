-- -v applied=true|false -v probe_down=true|false.
BEGIN;

INSERT INTO public.chat_rooms (room_id, room_type, direct_key, status)
VALUES ('crm_T01601', 'direct', '00000000-0000-0000-0000-000000016001|00000000-0000-0000-0000-000000016002', 'closed');

\if :applied
INSERT INTO public.chat_rooms (room_id, room_type, direct_key, status)
SELECT 'crm_T01602', 'direct', direct_key, 'closed'
FROM public.chat_rooms WHERE room_id = 'crm_T01601';

INSERT INTO public.chat_rooms (room_id, room_type, direct_key)
SELECT 'crm_T01603', 'direct', direct_key
FROM public.chat_rooms WHERE room_id = 'crm_T01601';
\echo 'T016a PASS: 닫힌 방을 보존한 채 같은 사용자 쌍의 새 방 생성'

\if :probe_down
-- 같은 세션에서 사전 검사와 down을 실행한다. 실패 시 연결 종료로 시험 행도 되돌린다.
\else
DO $$
DECLARE
  failed_constraint text;
BEGIN
  BEGIN
    INSERT INTO public.chat_rooms (room_id, room_type, direct_key)
    SELECT 'crm_T01604', 'direct', direct_key
    FROM public.chat_rooms WHERE room_id = 'crm_T01601';
    RAISE EXCEPTION 'T016b FAIL: 두 번째 활성 방이 허용되었습니다';
  EXCEPTION WHEN unique_violation THEN
    GET STACKED DIAGNOSTICS failed_constraint = CONSTRAINT_NAME;
    IF failed_constraint IS DISTINCT FROM 'uq_chat_rooms_direct_key_not_closed' THEN
      RAISE;
    END IF;
  END;
  RAISE NOTICE 'T016b PASS: 활성 방 중복 거부';

  UPDATE public.chat_rooms SET status = 'read_only', read_only_at = now() WHERE room_id = 'crm_T01603';
  BEGIN
    UPDATE public.chat_rooms SET status = 'active' WHERE room_id = 'crm_T01601';
    RAISE EXCEPTION 'T016c FAIL: 읽기 전용 방과 같은 키의 방이 재개되었습니다';
  EXCEPTION WHEN unique_violation THEN
    GET STACKED DIAGNOSTICS failed_constraint = CONSTRAINT_NAME;
    IF failed_constraint IS DISTINCT FROM 'uq_chat_rooms_direct_key_not_closed' THEN
      RAISE;
    END IF;
  END;
  RAISE NOTICE 'T016c PASS: 읽기 전용 방과 충돌하는 상태 변경 거부';
END $$;
ROLLBACK;
\endif
\else
DO $$
DECLARE
  failed_constraint text;
BEGIN
  BEGIN
    INSERT INTO public.chat_rooms (room_id, room_type, direct_key)
    SELECT 'crm_T01603', 'direct', direct_key
    FROM public.chat_rooms WHERE room_id = 'crm_T01601';
    RAISE EXCEPTION 'T016d FAIL: 전역 UNIQUE가 복원되지 않았습니다';
  EXCEPTION WHEN unique_violation THEN
    GET STACKED DIAGNOSTICS failed_constraint = CONSTRAINT_NAME;
    IF failed_constraint IS DISTINCT FROM 'chat_rooms_direct_key_key' THEN
      RAISE;
    END IF;
  END;
  RAISE NOTICE 'T016d PASS: 되돌리기 후 닫힌 방도 전역 UNIQUE 적용';
END $$;
ROLLBACK;
\endif
