BEGIN;
SET LOCAL ROLE noldaga_service;
INSERT INTO public.festivals (festival_id, title, region_code)
VALUES ('fst_T028CACHE', '시험 축제', 'SEOUL');
INSERT INTO public.route_cache_entries (cache_key, festival_id, route_hash, provider, valid_until)
VALUES ('test-028', 'fst_T028CACHE', 'test', 'mock_adapter', now());
INSERT INTO public.route_requests
  (route_request_id, request_id, festival_id, origin_type, destination_type, travel_mode,
   route_key, status, access_token_hash, is_mock)
VALUES ('rr_T028CACHE', 'test-028', 'fst_T028CACHE', 'user', 'user', 'walk',
        'test', 'ready', repeat('a', 64), true);
INSERT INTO public.route_results
  (route_request_id, provider, provider_tier, candidates, route_hash, source_type, cache_key,
   validity_check, queried_at, validation_status, is_mock)
VALUES ('rr_T028CACHE', 'mock_adapter', 'mock', '[]', 'test', 'cache', 'test-028',
        '{}', now(), 'verified_basic', true);

\if :applied
DELETE FROM public.route_cache_entries WHERE cache_key = 'test-028';
DO $$
BEGIN
  IF to_regclass('public.idx_route_results_cache_key') IS NULL
     OR EXISTS (SELECT 1 FROM public.route_cache_entries WHERE cache_key = 'test-028')
     OR NOT EXISTS (SELECT 1 FROM public.route_results WHERE route_request_id = 'rr_T028CACHE'
                    AND cache_key IS NULL AND candidates = '[]') THEN
    RAISE EXCEPTION 'T028a FAIL: 캐시 메타 삭제 또는 경로 결과 보존 실패';
  END IF;
END $$;
\echo 'T028a PASS: 서비스 역할로 캐시 메타 삭제 시 경로 결과와 본문 보존'
\else
DO $$
BEGIN
  IF to_regclass('public.idx_route_results_cache_key') IS NOT NULL THEN
    RAISE EXCEPTION 'T028b FAIL: 되돌리기 후 추가 인덱스가 남음';
  END IF;
  DELETE FROM public.route_cache_entries WHERE cache_key = 'test-028';
  RAISE EXCEPTION 'T028b FAIL: 되돌리기 후 기존 외래키 동작 미복원';
EXCEPTION WHEN foreign_key_violation THEN
  RAISE NOTICE 'T028b PASS: 되돌리기 후 참조 중인 캐시 메타 삭제 거부';
END $$;
\endif
ROLLBACK;
