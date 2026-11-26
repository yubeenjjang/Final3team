\if :{?applied}
\else
\set applied true
\endif

BEGIN;

INSERT INTO public.users (user_id, email, password_hash) VALUES
 ('01900000-0000-0000-0000-000000000001', 'chat019a@example.test', '!'),
 ('01900000-0000-0000-0000-000000000002', 'chat019b@example.test', '!'),
 ('01900000-0000-0000-0000-000000000003', 'chat019c@example.test', '!');

INSERT INTO public.chat_rooms (room_id, room_type, direct_key, status, read_only_at) VALUES
 ('crm_T02101', 'direct', '01900000-0000-0000-0000-000000000001|01900000-0000-0000-0000-000000000002', 'active', NULL),
 ('crm_T02102', 'companion', NULL, 'read_only', now() - interval '4 days');

INSERT INTO public.chat_members (room_id, user_id, status, joined_at) VALUES
 ('crm_T02101', '01900000-0000-0000-0000-000000000001', 'joined', now() - interval '32 days'),
 ('crm_T02101', '01900000-0000-0000-0000-000000000002', 'joined', now() - interval '1 day'),
 ('crm_T02102', '01900000-0000-0000-0000-000000000002', 'joined', now() - interval '5 days');

INSERT INTO public.chat_messages (room_id, seq, msg_type, body, created_at) VALUES
 ('crm_T02101', 1, 'system', '만료', now() - interval '31 days'),
 ('crm_T02101', 2, 'system', '입장 전', now() - interval '2 days'),
 ('crm_T02101', 3, 'system', '입장 후', now()),
 ('crm_T02102', 1, 'system', '만료된 동행방', now() - interval '5 days');

\if :applied
SET LOCAL ROLE noldaga_app;
SET LOCAL app.user_id = '01900000-0000-0000-0000-000000000002';
DO $$
BEGIN
  IF (SELECT array_agg(seq) FROM public.chat_messages WHERE room_id = 'crm_T02101')
      IS DISTINCT FROM ARRAY[3::bigint]
      OR EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_T02102') THEN
    RAISE EXCEPTION 'T021a FAIL: 입장 이전 또는 만료 본문 노출';
  END IF;
END $$;
SET LOCAL app.user_id = '01900000-0000-0000-0000-000000000003';
DO $$
BEGIN
  IF public.app_chat_can_read('crm_T02101')
      OR EXISTS (SELECT 1 FROM public.chat_members WHERE room_id = 'crm_T02101')
      OR EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_T02101') THEN
    RAISE EXCEPTION 'T021b FAIL: 비회원 열람 허용';
  END IF;
END $$;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.user_blocks (blocker, blocked)
VALUES ('01900000-0000-0000-0000-000000000002', '01900000-0000-0000-0000-000000000001');
DELETE FROM public.user_blocks WHERE blocker = '01900000-0000-0000-0000-000000000002';
INSERT INTO public.chat_rooms (room_id, room_type, direct_key)
SELECT 'crm_T02103', 'direct', direct_key FROM public.chat_rooms WHERE room_id = 'crm_T02101';
SET LOCAL ROLE noldaga_app;
SET LOCAL app.user_id = '01900000-0000-0000-0000-000000000001';
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.chat_rooms WHERE room_id = 'crm_T02101'
                   AND status = 'closed' AND closed_by_block)
      OR EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_T02101') THEN
    RAISE EXCEPTION 'T021c FAIL: 차단 해제 후 닫힌 방 상태 또는 이력';
  END IF;
END $$;
\echo 'T021a~c PASS: 입장 시각·보존·비회원·차단 해제 뒤 RLS 및 새 방 생성'
\else
DO $$
BEGIN
  -- One outer statement shares its timestamp with both checks.
  UPDATE public.chat_rooms SET read_only_at = statement_timestamp() - interval '72 hours' + interval '1 microsecond'
  WHERE room_id = 'crm_T02102';
  SET LOCAL ROLE noldaga_app;
  PERFORM set_config('app.user_id', '01900000-0000-0000-0000-000000000002', true);
  IF NOT EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_T02102') THEN
    RAISE EXCEPTION 'T021d FAIL: 되돌리기 후 72시간 직전 메시지 미노출';
  END IF;
  RESET ROLE;
  UPDATE public.chat_rooms SET read_only_at = statement_timestamp() - interval '72 hours'
  WHERE room_id = 'crm_T02102';
  SET LOCAL ROLE noldaga_app;
  IF EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_T02102') THEN
    RAISE EXCEPTION 'T021d FAIL: 되돌리기 후 정확히 72시간 지난 메시지 노출';
  END IF;
END $$;
\echo 'T021d PASS: 되돌리기 후 72시간 경계에서 채팅 이력 RLS 적용'
\endif
ROLLBACK;
