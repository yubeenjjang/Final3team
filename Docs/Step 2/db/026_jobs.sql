-- 마지막 성공 회차(작업별 1행)와 경로 요청 30일 보존에 필요한 외래 키.
CREATE TABLE public.scheduled_job_runs (
  job_name TEXT PRIMARY KEY,
  last_success_slot TIMESTAMPTZ NOT NULL
);
ALTER TABLE public.scheduled_job_runs ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON public.scheduled_job_runs TO noldaga_service;

ALTER TABLE public.route_results
  DROP CONSTRAINT route_results_route_request_id_fkey,
  ADD CONSTRAINT route_results_route_request_id_fkey
    FOREIGN KEY (route_request_id) REFERENCES public.route_requests(route_request_id) ON DELETE CASCADE;

ALTER TABLE public.route_requests
  DROP CONSTRAINT route_requests_shared_from_fkey,
  ADD CONSTRAINT route_requests_shared_from_fkey
    FOREIGN KEY (shared_from) REFERENCES public.route_requests(route_request_id) ON DELETE SET NULL;

CREATE INDEX idx_route_requests_submitted_at ON public.route_requests (submitted_at);
CREATE INDEX idx_route_requests_shared_from ON public.route_requests (shared_from) WHERE shared_from IS NOT NULL;
CREATE INDEX idx_assistant_runs_route_request ON public.assistant_runs (route_request_id) WHERE route_request_id IS NOT NULL;
