BEGIN;

INSERT INTO public.users (user_id, email, password_hash)
VALUES ('02200000-0000-0000-0000-000000000001', 'notice022@example.test', '!'),
       ('02200000-0000-0000-0000-000000000002', 'notice022-other@example.test', '!');
INSERT INTO public.profiles (user_id, role)
VALUES ('02200000-0000-0000-0000-000000000001', 'operator'),
       ('02200000-0000-0000-0000-000000000002', 'user');
INSERT INTO public.festivals (festival_id, title, region_code, category, source_class_level2, review_status, published_at)
VALUES ('fst_T02301', '공개 축제', 'SEOUL', 'festival', 'EV01', 'approved', now()),
       ('fst_T02302', '숨긴 축제', 'SEOUL', 'festival', 'EV01', 'hidden', NULL);

SET LOCAL ROLE noldaga_service;
INSERT INTO public.official_notices (notice_id, festival_id, type, title, source_id, effective_from, effective_to)
VALUES ('ntc_T02301', 'fst_T02301', 'no_stop', '효력 예정', 'admin_manual', now() + interval '1 hour', now() + interval '2 hours'),
       ('ntc_T02302', 'fst_T02301', 'road_closure', '승인 대기', 'admin_manual', now(), now() + interval '2 hours'),
       ('ntc_T02303', 'fst_T02302', 'operation', '숨긴 축제 공지', 'admin_manual', now(), now() + interval '2 hours');
INSERT INTO public.route_cache_entries (cache_key, festival_id, route_hash, provider, valid_until)
VALUES ('notice022-before', 'fst_T02301', 'hash', 'tmap', now() + interval '3 hours'),
       ('notice022-other', 'fst_T02302', 'hash', 'tmap', now() + interval '3 hours');
UPDATE public.official_notices SET approval_status = 'approved' WHERE notice_id = 'ntc_T02301';

DO $$
BEGIN
  IF (SELECT count(*) FROM public.notice_control_changes WHERE notice_id = 'ntc_T02301' AND effective_at <= clock_timestamp()) <> 1
    OR (SELECT count(*) FROM public.notice_control_changes WHERE notice_id = 'ntc_T02301' AND effective_at <= now() + interval '1 hour') <> 2
    OR (SELECT count(*) FROM public.notice_control_changes WHERE notice_id = 'ntc_T02301' AND effective_at <= now() + interval '2 hours') <> 3
    OR (SELECT valid_until FROM public.route_cache_entries WHERE cache_key = 'notice022-before') > clock_timestamp()
    OR (SELECT valid_until FROM public.route_cache_entries WHERE cache_key = 'notice022-other') <> now() + interval '3 hours'
  THEN RAISE EXCEPTION 'T023a FAIL: 승인·효력 전이 또는 축제별 캐시 무효화';
  END IF;
END $$;
INSERT INTO public.route_cache_entries (cache_key, festival_id, route_hash, provider, valid_until)
VALUES ('notice022-after', 'fst_T02301', 'hash', 'tmap', now() + interval '3 hours');
DO $$
BEGIN
  IF (SELECT valid_until FROM public.route_cache_entries WHERE cache_key = 'notice022-after') <> now() + interval '1 hour'
  THEN RAISE EXCEPTION 'T023b FAIL: 예정 효력 전이에 맞춘 캐시 만료';
  END IF;
END $$;

UPDATE public.official_notices SET approval_status = 'approved' WHERE notice_id = 'ntc_T02303';
UPDATE public.official_notices SET ended_at = clock_timestamp() WHERE notice_id = 'ntc_T02301';
INSERT INTO public.notice_events (notice_id, action, actor)
VALUES ('ntc_T02301', 'end', '02200000-0000-0000-0000-000000000001');

DO $$
BEGIN
  IF (SELECT count(*) FROM public.notice_control_changes WHERE notice_id = 'ntc_T02301') <> 2
  THEN RAISE EXCEPTION 'T023c FAIL: 수동 종료 이후 이전 일정이 남음';
  END IF;
END $$;

SET LOCAL ROLE noldaga_app;
SET LOCAL app.user_id = '02200000-0000-0000-0000-000000000002';
DO $$
BEGIN
  IF (SELECT array_agg(notice_id) FROM public.official_notices WHERE notice_id LIKE 'ntc_T023%')
      IS DISTINCT FROM ARRAY['ntc_T02301'::text]
      OR EXISTS (SELECT 1 FROM public.profiles WHERE user_id = '02200000-0000-0000-0000-000000000001')
      OR has_table_privilege('public.notice_events', 'SELECT')
      OR has_table_privilege('public.official_notices', 'UPDATE')
      OR has_table_privilege('public.notice_control_changes', 'SELECT')
  THEN RAISE EXCEPTION 'T023d FAIL: 일반 사용자에게 비공개 행 또는 내부 권한 노출';
  END IF;
END $$;
RESET ROLE;

DO $$
BEGIN
  BEGIN
    UPDATE public.notice_events SET reason = '변경' WHERE notice_id = 'ntc_T02301';
    RAISE EXCEPTION 'T023e FAIL: 공지 종료 이력 수정 허용';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM NOT LIKE '%추가만 할 수 있습니다%' THEN RAISE; END IF;
  END;
END $$;

\echo 'T023a~e PASS: 효력 전이·축제별 캐시·수동 종료·RLS·이력 보존'
ROLLBACK;
