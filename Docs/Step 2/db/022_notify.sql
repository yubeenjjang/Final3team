-- 처리 메모는 운영자용이며 기존 reports 행과 앱 역할의 조회 권한을 유지한다.
CREATE TABLE public.report_moderation (
  report_id TEXT PRIMARY KEY REFERENCES public.reports(report_id),
  action TEXT NOT NULL CHECK (action IN ('dismiss', 'hide_message', 'hide_post', 'close_room', 'block_user')),
  note TEXT NOT NULL
);
ALTER TABLE public.report_moderation ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT ON public.report_moderation TO noldaga_service;

CREATE INDEX idx_reports_reporter_target_time
  ON public.reports (reporter_id, target_type, target_id, created_at);
