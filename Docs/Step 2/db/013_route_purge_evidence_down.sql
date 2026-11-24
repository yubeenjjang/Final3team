-- 파일 단위 트랜잭션으로 되돌린다. route_results의 삭제 시각은 보존한다.
LOCK TABLE public.route_requests, public.route_results IN ACCESS EXCLUSIVE MODE;

DROP TRIGGER record_route_result_purge ON public.route_results;
DROP FUNCTION public.record_route_result_purge();
ALTER TABLE public.route_requests DROP COLUMN result_purged_at;
