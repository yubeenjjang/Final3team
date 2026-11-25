-- psql -X -v ON_ERROR_STOP=1 -1 -f 로 실행. 먼저 API의 ROUTE_STORE를 memory로 전환한다.
-- 기존 요청·결과 행은 보존한다. 011 조회 토큰은 폐기되며, 정리한 결과 본문은 복원되지 않는다.
LOCK TABLE public.route_requests, public.route_results IN ACCESS EXCLUSIVE MODE;

DROP INDEX public.idx_route_results_tmap_pending_purge;
ALTER TABLE public.route_requests
  DROP COLUMN error_detail,
  DROP COLUMN request_body_hash,
  DROP COLUMN access_token_hash;
