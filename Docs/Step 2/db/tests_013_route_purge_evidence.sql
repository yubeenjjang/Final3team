-- run_tests.sh가 단계별로 실행한다. T25a·b의 본문 표식 행은 백업 전까지 유지한다.
\if :seed
BEGIN;
SET LOCAL ROLE noldaga_service;
UPDATE public.route_results
SET candidates = NULL, evidence = '{}',
    queried_at = '2026-11-22 16:40:00+09', purged_at = '2026-11-23 16:40:00+09'
WHERE route_request_id = 'rr_T011LEGACY';
COMMIT;
\elif :restored
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.route_requests
    WHERE route_request_id = 'rr_T011LEGACY' AND result_provider = 'tmap'
      AND result_queried_at = '2026-11-22 16:40:00+09'
      AND result_purged_at = '2026-11-23 16:40:00+09'
  ) OR (
    SELECT count(*) FROM public.route_requests
    WHERE route_request_id IN ('rr_000002', 'rr_000004') AND result_purged_at IS NULL
  ) <> 2 THEN
    RAISE EXCEPTION 'FAIL T25c: 복원 뒤 삭제 시각이 누락되거나 잘못 기록됨';
  END IF;
  RAISE NOTICE 'PASS T25c: 복원 뒤 실제 삭제 시각 보존, 미정리·결과 없는 요청은 NULL';
END $$;
\elif :applied
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.route_requests JOIN public.route_results USING (route_request_id)
    WHERE route_request_id = 'rr_T011LEGACY' AND candidates IS NULL
      AND purged_at = '2026-11-23 16:40:00+09' AND result_purged_at = purged_at
  ) OR (
    SELECT count(*) FROM public.route_requests
    WHERE route_request_id IN ('rr_000002', 'rr_000004') AND result_purged_at IS NULL
  ) <> 2 THEN
    RAISE EXCEPTION 'FAIL T013a: 기존 삭제 시각 이관 또는 미정리 요청 NULL';
  END IF;
  RAISE NOTICE 'PASS T013a: 기존 삭제 시각 이관 및 미정리·결과 없는 요청의 NULL 유지';
END $$;

BEGIN;
SET LOCAL ROLE noldaga_service;
UPDATE public.route_results
SET candidates = NULL, evidence = '{}', provider_ref = NULL,
    purged_at = '2026-11-24 16:40:00+09'
WHERE route_request_id = 'rr_000002';
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.route_requests JOIN public.route_results USING (route_request_id)
    WHERE route_request_id = 'rr_000002' AND candidates IS NULL
      AND purged_at = '2026-11-24 16:40:00+09' AND result_purged_at = purged_at
  ) THEN
    RAISE EXCEPTION 'FAIL T013b: 서비스 계정의 정리 트랜잭션에서 삭제 시각이 다름';
  END IF;
  RAISE NOTICE 'PASS T013b: 서비스 계정의 정리 트랜잭션에서 두 삭제 시각 일치';
END $$;
ROLLBACK;

BEGIN;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  IF (SELECT count(*) FROM pg_class
      WHERE oid IN ('public.route_requests'::regclass, 'public.route_results'::regclass)
        AND relrowsecurity) <> 2 THEN
    RAISE EXCEPTION 'FAIL T013c: 경로 테이블 RLS가 꺼짐';
  END IF;
  BEGIN
    PERFORM result_purged_at FROM public.route_requests;
    RAISE EXCEPTION 'FAIL T013c: 일반 계정이 삭제 시각을 읽음';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  BEGIN
    UPDATE public.route_requests SET result_purged_at = NULL WHERE false;
    RAISE EXCEPTION 'FAIL T013c: 일반 계정에 삭제 시각 수정 권한이 있음';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  RAISE NOTICE 'PASS T013c: RLS 유지, 일반 계정의 삭제 시각 읽기·수정 거부';
END $$;
ROLLBACK;
\else
DO $$
BEGIN
  IF to_regprocedure('public.record_route_result_purge()') IS NOT NULL OR EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'route_requests' AND column_name = 'result_purged_at'
  ) OR NOT EXISTS (
    SELECT 1 FROM public.route_requests JOIN public.route_results USING (route_request_id)
    WHERE route_request_id = 'rr_T011LEGACY' AND result_provider = 'tmap'
      AND result_queried_at = queried_at AND purged_at = '2026-11-23 16:40:00+09'
  ) THEN
    RAISE EXCEPTION 'FAIL T013d: 013 되돌리기 또는 기존 증빙 보존';
  END IF;
  RAISE NOTICE 'PASS T013d: 013 되돌리기 뒤 결과 삭제 시각과 012 증빙 유지';
END $$;
\endif
