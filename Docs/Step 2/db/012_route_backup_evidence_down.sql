LOCK TABLE public.route_requests, public.route_results IN ACCESS EXCLUSIVE MODE;

DROP TRIGGER record_route_result_metadata ON public.route_results;
DROP FUNCTION public.record_route_result_metadata();
ALTER TABLE public.route_requests
  DROP CONSTRAINT route_requests_result_metadata_check,
  DROP COLUMN result_queried_at,
  DROP COLUMN result_provider;
