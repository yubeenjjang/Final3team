LOCK TABLE public.report_moderation IN ACCESS EXCLUSIVE MODE;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.report_moderation) THEN
    RAISE EXCEPTION '022_notify: 운영 조치 기록이 있어 되돌릴 수 없습니다';
  END IF;
END $$;
DROP TABLE public.report_moderation;
DROP INDEX public.idx_reports_reporter_target_time;
