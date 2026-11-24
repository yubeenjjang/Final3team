\if :applied
BEGIN;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.scheduled_job_runs (job_name, last_success_slot) VALUES ('sql_test', now());
UPDATE public.route_requests SET shared_from = 'rr_T011LEGACY' WHERE route_request_id = 'rr_000002';
DELETE FROM public.route_requests WHERE route_request_id = 'rr_T011LEGACY';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.scheduled_job_runs WHERE job_name = 'sql_test') OR EXISTS (
    SELECT 1 FROM public.route_results WHERE route_request_id = 'rr_T011LEGACY'
  ) OR NOT EXISTS (
    SELECT 1 FROM public.route_requests WHERE route_request_id = 'rr_000002' AND shared_from IS NULL
  ) THEN
    RAISE EXCEPTION 'FAIL T022a: 회차 기록, 결과 연쇄 삭제 또는 공유 참조 해제 오류';
  END IF;
  RAISE NOTICE 'PASS T022a: 서비스 회차 기록, 결과 연쇄 삭제, 공유 참조 해제';
END $$;

RESET ROLE;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.scheduled_job_runs'::regclass)
     OR has_table_privilege(current_user, 'public.scheduled_job_runs', 'SELECT, INSERT, UPDATE, DELETE') THEN
    RAISE EXCEPTION 'FAIL T022b: 회차 테이블 RLS 또는 일반 계정 접근 권한 오류';
  END IF;
  RAISE NOTICE 'PASS T022b: 회차 테이블 RLS 활성, 일반 계정 접근 거부';
END $$;
ROLLBACK;
\else
DO $$
BEGIN
  IF to_regclass('public.scheduled_job_runs') IS NOT NULL
     OR to_regclass('public.idx_route_requests_submitted_at') IS NOT NULL
     OR to_regclass('public.idx_route_requests_shared_from') IS NOT NULL
     OR to_regclass('public.idx_assistant_runs_route_request') IS NOT NULL
     OR (SELECT count(*) FROM pg_constraint WHERE conrelid IN (
          'public.route_requests'::regclass, 'public.route_results'::regclass
        ) AND conname IN ('route_results_route_request_id_fkey', 'route_requests_shared_from_fkey')
          AND confdeltype = 'a') <> 2 THEN
    RAISE EXCEPTION 'FAIL T022c: 회차 테이블·인덱스·외래 키 되돌리기 오류';
  END IF;
  RAISE NOTICE 'PASS T022c: 회차 테이블·인덱스 제거와 기존 외래 키 복원';
END $$;
\endif
