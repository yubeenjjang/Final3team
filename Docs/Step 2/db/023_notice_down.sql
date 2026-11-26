-- 종료 이력을 버리지 않도록 006 형식으로 표현할 수 있을 때만 되돌린다.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.notice_events WHERE action = 'end')
    OR EXISTS (SELECT 1 FROM public.official_notices WHERE ended_at IS NOT NULL) THEN
    RAISE EXCEPTION '023_notice: 보존해야 하는 공지 종료 이력이 있습니다';
  END IF;
END;
$$;

DROP TRIGGER trg_notice_cache_validity ON public.route_cache_entries;
DROP FUNCTION public.limit_notice_cache_validity();
DROP TRIGGER trg_notice_control_changes ON public.official_notices;
DROP FUNCTION public.record_notice_control_change();
DROP TABLE public.notice_control_changes;
DROP INDEX public.idx_official_notices_approved_scope;

ALTER POLICY notices_public ON public.official_notices USING (approval_status = 'approved');
ALTER TABLE public.notice_events DROP CONSTRAINT notice_events_action_check,
  ADD CONSTRAINT notice_events_action_check CHECK (action IN ('create','update','approve','reject'));
ALTER TABLE public.official_notices DROP COLUMN ended_at;
