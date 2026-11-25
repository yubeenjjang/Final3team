-- 실행 기록·인덱스와 외래 키 정책을 되돌린다. 정리된 데이터의 복구는 별도 백업을 사용한다.
DROP INDEX public.idx_assistant_runs_route_request, public.idx_route_requests_shared_from,
  public.idx_route_requests_submitted_at;

ALTER TABLE public.route_requests
  DROP CONSTRAINT route_requests_shared_from_fkey,
  ADD CONSTRAINT route_requests_shared_from_fkey
    FOREIGN KEY (shared_from) REFERENCES public.route_requests(route_request_id);

ALTER TABLE public.route_results
  DROP CONSTRAINT route_results_route_request_id_fkey,
  ADD CONSTRAINT route_results_route_request_id_fkey
    FOREIGN KEY (route_request_id) REFERENCES public.route_requests(route_request_id);

DROP TABLE public.scheduled_job_runs;
