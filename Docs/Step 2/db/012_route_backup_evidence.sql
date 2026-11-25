-- 7일 백업에서 route_results 행을 제외해도 요청별 공급원·조회 시각을 보존한다.
-- 011 뒤에 파일 단위 트랜잭션으로 적용한다.
LOCK TABLE public.route_requests, public.route_results IN ACCESS EXCLUSIVE MODE;

ALTER TABLE public.route_requests
  ADD COLUMN result_provider TEXT CHECK (result_provider IN ('tmap', 'kakao', 'mock_adapter')),
  ADD COLUMN result_queried_at TIMESTAMPTZ,
  ADD CONSTRAINT route_requests_result_metadata_check
    CHECK ((result_provider IS NULL) = (result_queried_at IS NULL));

UPDATE public.route_requests AS request
SET result_provider = result.provider,
    result_queried_at = result.queried_at
FROM public.route_results AS result
WHERE request.route_request_id = result.route_request_id;

CREATE FUNCTION public.record_route_result_metadata()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  UPDATE public.route_requests
  SET result_provider = NEW.provider,
      result_queried_at = NEW.queried_at
  WHERE route_request_id = NEW.route_request_id;
  RETURN NEW;
END;
$$;

CREATE TRIGGER record_route_result_metadata
AFTER INSERT OR UPDATE OF provider, queried_at ON public.route_results
FOR EACH ROW EXECUTE FUNCTION public.record_route_result_metadata();
