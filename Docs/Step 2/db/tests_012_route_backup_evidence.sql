-- run_tests.sh에서 단계별로 실행한다. 표식은 합성 데이터에만 쓴다.
\if :seed
BEGIN;
SET LOCAL ROLE noldaga_service;
UPDATE public.route_results
SET queried_at = '2026-11-23 16:40:00+09',
    provider_ref = 'TMAP_RAW_MARKER',
    evidence = '{"provider_original":"TMAP_RAW_MARKER"}'
WHERE route_request_id = 'rr_000002';
UPDATE public.route_requests
SET status = 'unavailable', error_code = 'ROUTE_UPSTREAM_ERROR',
    submitted_at = '2026-11-23 16:41:00+09'
WHERE route_request_id = 'rr_000004';
COMMIT;
\elif :restored
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.route_results) THEN
    RAISE EXCEPTION 'FAIL T25a: 복원된 route_results에 데이터가 있음';
  END IF;
  RAISE NOTICE 'PASS T25a: 복원된 route_results에 공급원 원본·후보 등 데이터 0행';

  IF NOT EXISTS (
    SELECT 1 FROM public.route_requests
    WHERE route_request_id = 'rr_000002' AND status = 'ready'
      AND result_provider = 'tmap' AND result_queried_at = '2026-11-23 16:40:00+09'
      AND error_code IS NULL
  ) OR NOT EXISTS (
    SELECT 1 FROM public.route_requests
    WHERE route_request_id = 'rr_000004' AND status = 'unavailable'
      AND error_code = 'ROUTE_UPSTREAM_ERROR' AND submitted_at = '2026-11-23 16:41:00+09'
      AND result_provider IS NULL AND result_queried_at IS NULL
  ) THEN
    RAISE EXCEPTION 'FAIL T25b: 복원된 경로 요청의 증빙이 누락되거나 값이 바뀜';
  END IF;
  RAISE NOTICE 'PASS T25b: 복원 뒤 공급원·조회 시각·요청 상태·오류 코드 보존';
END $$;
\elif :applied
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.route_requests JOIN public.route_results USING (route_request_id)
    WHERE route_request_id = 'rr_000002' AND result_provider = 'tmap'
      AND result_queried_at = '2026-11-23 16:40:00+09'
      AND result_queried_at = queried_at
      AND candidates->0->>'summary' = 'TMAP_ROUTE_MARKER'
      AND provider_ref = 'TMAP_RAW_MARKER'
      AND evidence->>'provider_original' = 'TMAP_RAW_MARKER'
  ) THEN
    RAISE EXCEPTION 'FAIL T012a: 기존 증빙 이관 또는 원본 시험 데이터 누락';
  END IF;
  RAISE NOTICE 'PASS T012a: 기존 증빙 이관 및 원본 DB 본문 유지';
END $$;

BEGIN;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.route_results (
  route_request_id, provider, provider_tier, candidates, route_hash,
  source_type, queried_at, validation_status, is_mock
) VALUES (
  'rr_000001', 'mock_adapter', 'mock', '[]', 'backup-test-result',
  'fresh', '2026-11-23 16:42:00+09', 'verified_basic', true
);
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.route_requests WHERE route_request_id = 'rr_000001'
      AND result_provider = 'mock_adapter' AND result_queried_at = '2026-11-23 16:42:00+09'
  ) THEN
    RAISE EXCEPTION 'FAIL T012b: 서비스 계정의 신규 결과 증빙 누락';
  END IF;
  RAISE NOTICE 'PASS T012b: 서비스 계정의 신규 결과 증빙 동기화';
END $$;
ROLLBACK;
\else
DO $$
BEGIN
  IF to_regprocedure('public.record_route_result_metadata()') IS NOT NULL OR EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'route_requests'
      AND column_name IN ('result_provider', 'result_queried_at')
  ) OR NOT EXISTS (
    SELECT 1 FROM public.route_results WHERE route_request_id = 'rr_000002'
      AND candidates->0->>'summary' = 'TMAP_ROUTE_MARKER' AND provider_ref = 'TMAP_RAW_MARKER'
  ) THEN
    RAISE EXCEPTION 'FAIL T012c: 012 되돌리기 또는 원래 경로 결과 보존';
  END IF;
  RAISE NOTICE 'PASS T012c: 증빙 칸·트리거 제거, 원래 경로 결과 유지';
END $$;
\endif
