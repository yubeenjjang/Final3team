-- T011: 010 상태에서 기존 행을 심고 011 적용/되돌리기에 걸친 보존을 확인한다.
-- run_tests.sh가 phase를 넘긴다. 일회용 DB에서 실행한다.
\if :seed
INSERT INTO public.festivals (festival_id, title, region_code)
VALUES ('fst_T011LEGACY', '011 기존 축제', '11');
INSERT INTO public.route_requests (
  route_request_id, request_id, festival_id, origin_type, destination_type,
  travel_mode, route_key, status, is_mock
) VALUES ('rr_T011LEGACY', 't011-legacy', 'fst_T011LEGACY', 'user', 'user',
          'transit', 'legacy-key', 'ready', true);
INSERT INTO public.route_results (
  route_request_id, provider, provider_tier, candidates, route_hash, source_type,
  queried_at, validation_status, is_mock
) VALUES ('rr_T011LEGACY', 'tmap', 'primary', '[]', 'legacy-result', 'fresh',
          now(), 'control_unverified', true);
\elif :applied
BEGIN;
DO $$
BEGIN
  IF to_regclass('public.idx_route_results_tmap_pending_purge') IS NULL
     OR EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
                 AND table_name = 'route_requests' AND column_name = 'user_id')
     OR NOT EXISTS (SELECT 1 FROM public.route_requests JOIN public.route_results USING (route_request_id)
                    WHERE route_request_id = 'rr_T011LEGACY' AND request_id = 't011-legacy'
                      AND access_token_hash ~ '^[0-9a-f]{64}$' AND request_body_hash IS NULL
                      AND route_hash = 'legacy-result' AND candidates = '[]') THEN
    RAISE EXCEPTION 'FAIL T011a: 칸·색인 또는 기존 행 보존';
  END IF;
  RAISE NOTICE 'PASS T011a: 칸·색인과 기존 요청·결과 보존';
END $$;
SET LOCAL ROLE noldaga_service;
DO $$
BEGIN
  UPDATE public.route_requests SET access_token_hash = repeat('a', 64)
  WHERE route_request_id = 'rr_T011LEGACY';
  BEGIN
    UPDATE public.route_requests SET access_token_hash = NULL WHERE route_request_id = 'rr_T011LEGACY';
    RAISE EXCEPTION 'FAIL T011b: NULL 허용';
  EXCEPTION WHEN not_null_violation THEN NULL;
  END;
  BEGIN
    UPDATE public.route_requests SET access_token_hash = 'rrt_SYNTHETIC' WHERE route_request_id = 'rr_T011LEGACY';
    RAISE EXCEPTION 'FAIL T011b: 잘못된 해시 형식 허용';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  RAISE NOTICE 'PASS T011b: 서비스 계정·토큰 해시 제약';
END $$;
RESET ROLE;
SET LOCAL ROLE noldaga_app;
DO $$
BEGIN
  BEGIN
    PERFORM access_token_hash FROM public.route_requests;
    RAISE EXCEPTION 'FAIL T011c: 일반 계정에서 요청 해시를 읽음';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  BEGIN
    PERFORM candidates FROM public.route_results;
    RAISE EXCEPTION 'FAIL T011c: 일반 계정에서 결과를 읽음';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  RAISE NOTICE 'PASS T011c: 일반 계정 조회 거부';
END $$;
ROLLBACK;
\else
DO $$
BEGIN
  IF to_regclass('public.idx_route_results_tmap_pending_purge') IS NOT NULL
     OR EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
                 AND table_name = 'route_requests'
                 AND column_name IN ('access_token_hash', 'request_body_hash', 'error_detail'))
     OR NOT EXISTS (SELECT 1 FROM public.route_requests JOIN public.route_results USING (route_request_id)
                    WHERE route_request_id = 'rr_T011LEGACY' AND request_id = 't011-legacy'
                      AND route_hash = 'legacy-result' AND candidates = '[]') THEN
    RAISE EXCEPTION 'FAIL T011d: 되돌리기 또는 기존 행 보존';
  END IF;
  RAISE NOTICE 'PASS T011d: 되돌리기와 기존 요청·결과 보존';
END $$;
\endif
