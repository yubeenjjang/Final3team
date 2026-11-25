\if :applied
BEGIN;
DO $$
BEGIN
  IF to_regclass('public.idx_reports_reporter_target_time') IS NULL THEN
    RAISE EXCEPTION 'T022a: 신고 한도 조회 인덱스 누락';
  END IF;
  IF has_table_privilege('noldaga_app', 'public.report_moderation', 'SELECT') THEN
    RAISE EXCEPTION 'T022a: 앱 역할에 운영 메모 열람 권한이 있음';
  END IF;
END $$;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.report_moderation (report_id, action, note)
VALUES ('rpt_000001', 'dismiss', '시험용 처리 메모');
DO $$
BEGIN
  BEGIN
    DELETE FROM public.chat_admin_access WHERE report_id = 'rpt_000001';
    RAISE EXCEPTION 'T022b: 서비스 역할이 열람 기록을 삭제함';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END $$;
RESET ROLE;
DO $$
BEGIN
  BEGIN
    DELETE FROM public.chat_admin_access WHERE report_id = 'rpt_000001';
    RAISE EXCEPTION 'T022c: 소유자가 열람 기록을 삭제함';
  EXCEPTION WHEN raise_exception THEN
    IF position('추가만 할 수 있습니다' IN SQLERRM) = 0 THEN RAISE; END IF;
  END;
END $$;
SET LOCAL ROLE noldaga_app;
SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.reports WHERE report_id = 'rpt_000001') THEN
    RAISE EXCEPTION 'T022d: 다른 사용자의 신고가 보임';
  END IF;
END $$;
ROLLBACK;
\echo 'T022a–d PASS: 신고 인덱스·메모 권한·열람 기록 보호·신고 RLS'
\else
DO $$
BEGIN
  IF to_regclass('public.report_moderation') IS NOT NULL
     OR to_regclass('public.idx_reports_reporter_target_time') IS NOT NULL THEN
    RAISE EXCEPTION 'T022e: 되돌리기 뒤 022 객체가 남음';
  END IF;
END $$;
\echo 'T022e PASS: 022 적용 전 상태로 되돌림'
\endif
