\if :applied
BEGIN;
INSERT INTO public.users (user_id, email, password_hash)
VALUES ('aaaa0019-0000-0000-0000-000000000001', 'owner-019@example.test', '!'),
       ('bbbb0019-0000-0000-0000-000000000002', 'guest-019@example.test', '!');
INSERT INTO public.festivals (festival_id, title, region_code)
VALUES ('fst_test019', '동행 시험 축제', 'SEOUL');
INSERT INTO public.chat_rooms (room_id, room_type, owner_id)
VALUES ('crm_test019', 'companion', 'aaaa0019-0000-0000-0000-000000000001');
INSERT INTO public.companion_posts (post_id, festival_id, author_id, room_id, meet_at, capacity,
                                    status, recruitment_closed_at)
VALUES ('cpo_test019', 'fst_test019', 'aaaa0019-0000-0000-0000-000000000001', 'crm_test019',
        now(), 3, 'full', now());
INSERT INTO public.meeting_places (post_id, name, updated_by)
VALUES ('cpo_test019', '정문', 'aaaa0019-0000-0000-0000-000000000001');
INSERT INTO public.chat_members (room_id, user_id, role, status, joined_at)
VALUES ('crm_test019', 'aaaa0019-0000-0000-0000-000000000001', 'owner', 'joined', now()),
       ('crm_test019', 'bbbb0019-0000-0000-0000-000000000002', 'member', 'joined', now());
INSERT INTO public.chat_messages (room_id, seq, msg_type, body)
VALUES ('crm_test019', 1, 'system', '동행 시험 메시지');

UPDATE public.companion_posts SET status = 'open' WHERE post_id = 'cpo_test019';
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.companion_posts WHERE post_id = 'cpo_test019' AND status = 'full') THEN
    RAISE EXCEPTION 'T020a FAIL: 수동 마감 글이 다시 열렸습니다';
  END IF;
  RAISE NOTICE 'T020a PASS: 수동 마감 상태 유지';
END $$;

UPDATE public.companion_posts SET status = 'ended', ended_at = now() - interval '71 hours'
WHERE post_id = 'cpo_test019';
UPDATE public.chat_rooms SET status = 'read_only', read_only_at = now() - interval '71 hours'
WHERE room_id = 'crm_test019';
SET LOCAL ROLE noldaga_app;
SET LOCAL app.user_id = 'bbbb0019-0000-0000-0000-000000000002';
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.meeting_places WHERE post_id = 'cpo_test019')
     OR NOT EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_test019') THEN
    RAISE EXCEPTION 'T020b FAIL: 72시간 전에 내용이 사라졌습니다';
  END IF;
  RAISE NOTICE 'T020b PASS: 72시간 전 참가자 열람';
END $$;

RESET ROLE;
UPDATE public.companion_posts SET ended_at = now() - interval '72 hours' WHERE post_id = 'cpo_test019';
UPDATE public.chat_rooms SET read_only_at = now() - interval '72 hours' WHERE room_id = 'crm_test019';
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.meeting_places WHERE post_id = 'cpo_test019')
     OR EXISTS (SELECT 1 FROM public.chat_messages WHERE room_id = 'crm_test019') THEN
    RAISE EXCEPTION 'T020c FAIL: 72시간이 지난 내용이 보입니다';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.chat_rooms WHERE room_id = 'crm_test019' AND status = 'read_only') THEN
    RAISE EXCEPTION 'T020c FAIL: 지난 동행방 이력이 사라졌습니다';
  END IF;
  RAISE NOTICE 'T020c PASS: 72시간 이후 내용 접근 차단과 방 이력 보존';
END $$;
ROLLBACK;
\else
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'companion_posts'
               AND column_name = 'recruitment_closed_at')
     OR to_regprocedure('public.keep_companion_recruitment_closed()') IS NOT NULL
     OR to_regclass('public.idx_companion_posts_auto_end') IS NOT NULL
     OR to_regclass('public.idx_companion_posts_retention') IS NOT NULL
     OR EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                 AND policyname IN ('meeting_places_members', 'chat_messages_members')
                 AND qual LIKE '%statement_timestamp%') THEN
    RAISE EXCEPTION 'T020d FAIL: 마이그레이션 변경이 남았습니다';
  END IF;
  RAISE NOTICE 'T020d PASS: 마감 상태와 만료 정책 되돌리기';
END $$;
\endif
