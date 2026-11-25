-- 012 뒤에 파일 단위 트랜잭션으로 적용한다.
LOCK TABLE public.route_requests, public.route_results IN ACCESS EXCLUSIVE MODE;

ALTER TABLE public.route_requests
  ADD COLUMN result_purged_at TIMESTAMPTZ;

UPDATE public.route_requests AS request
SET result_purged_at = result.purged_at
FROM public.route_results AS result
WHERE request.route_request_id = result.route_request_id
  AND result.purged_at IS NOT NULL;

CREATE FUNCTION public.record_route_result_purge()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  UPDATE public.route_requests
  SET result_purged_at = NEW.purged_at
  WHERE route_request_id = NEW.route_request_id;
  RETURN NEW;
END;
$$;

CREATE TRIGGER record_route_result_purge
AFTER INSERT OR UPDATE OF purged_at ON public.route_results
FOR EACH ROW WHEN (NEW.purged_at IS NOT NULL)
EXECUTE FUNCTION public.record_route_result_purge();
