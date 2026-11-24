-- 021 다음에 파일 단위 트랜잭션으로 적용한다.
INSERT INTO public.data_sources (source_id, name, scope, is_realtime)
VALUES ('admin_manual', '운영자 등록', 'national', false)
ON CONFLICT (source_id) DO NOTHING;

ALTER TABLE public.official_notices ADD COLUMN ended_at TIMESTAMPTZ;

ALTER TABLE public.notice_events DROP CONSTRAINT notice_events_action_check,
  ADD CONSTRAINT notice_events_action_check CHECK (action IN ('create','update','approve','reject','end'));

ALTER POLICY notices_public ON public.official_notices USING (
  approval_status = 'approved' AND (
    festival_id IS NULL OR EXISTS (
      SELECT 1 FROM public.festivals f WHERE f.festival_id = official_notices.festival_id
    )
  )
);

-- 이미 효력이 발생한 변경은 남기고, 변경된 일정의 미래 전이만 교체한다.
-- 원본 공지가 정리돼도 해당 축제의 버전이 되돌아가지 않도록 공지 ID는 참조값으로 보존한다.
CREATE TABLE public.notice_control_changes (
  change_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  notice_id TEXT NOT NULL,
  festival_id TEXT REFERENCES public.festivals(festival_id) ON DELETE CASCADE,
  effective_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notice_control_scope_time ON public.notice_control_changes (festival_id, effective_at);
CREATE INDEX idx_notice_control_notice_time ON public.notice_control_changes (notice_id, effective_at);
ALTER TABLE public.notice_control_changes ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, DELETE ON public.notice_control_changes TO noldaga_service;
GRANT USAGE ON SEQUENCE public.notice_control_changes_change_id_seq TO noldaga_service;

CREATE INDEX idx_official_notices_approved_scope ON public.official_notices (festival_id, effective_from)
  WHERE approval_status = 'approved';

-- 기존 승인 공지의 버전과 남은 전이도 초기화한다.
INSERT INTO public.notice_control_changes (notice_id, festival_id, effective_at)
SELECT n.notice_id, n.festival_id, t.effective_at
FROM public.official_notices n
CROSS JOIN LATERAL (VALUES
  (statement_timestamp()),
  (CASE WHEN n.effective_from > statement_timestamp() THEN n.effective_from END),
  (CASE WHEN n.effective_to > statement_timestamp() THEN n.effective_to END)
) AS t(effective_at)
WHERE n.approval_status = 'approved' AND t.effective_at IS NOT NULL;

UPDATE public.route_cache_entries c SET valid_until = statement_timestamp()
WHERE c.valid_until > statement_timestamp()
  AND EXISTS (
    SELECT 1 FROM public.notice_control_changes nc
    WHERE nc.festival_id IS NULL OR nc.festival_id = c.festival_id
  );

CREATE FUNCTION public.record_notice_control_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE
  old_approved BOOLEAN := false;
  new_approved BOOLEAN := false;
  old_scope TEXT;
  new_scope TEXT;
  changed_notice TEXT;
  changed_at TIMESTAMPTZ;
  ends_at TIMESTAMPTZ;
  scope TEXT;
BEGIN
  IF TG_OP <> 'INSERT' THEN
    old_approved := OLD.approval_status = 'approved';
    old_scope := OLD.festival_id;
    changed_notice := OLD.notice_id;
  END IF;
  IF TG_OP <> 'DELETE' THEN
    new_approved := NEW.approval_status = 'approved';
    new_scope := NEW.festival_id;
    changed_notice := NEW.notice_id;
  END IF;
  IF NOT (old_approved OR new_approved) THEN
    RETURN NULL;
  END IF;

  -- 같은 축제의 승인/재검토를 직렬화하고, 범위가 바뀌면 동일 순서로 잠근다.
  FOR scope IN
    SELECT DISTINCT scope_id
    FROM (VALUES (old_approved, old_scope), (new_approved, new_scope)) v(approved, scope_id)
    WHERE approved ORDER BY scope_id NULLS FIRST
  LOOP
    PERFORM pg_advisory_xact_lock(hashtextextended('noldaga.notice:' || coalesce(scope, ''), 0));
  END LOOP;
  changed_at := clock_timestamp();

  DELETE FROM public.notice_control_changes WHERE notice_id = changed_notice AND effective_at > changed_at;

  IF old_approved AND (NOT new_approved OR old_scope IS DISTINCT FROM new_scope) THEN
    INSERT INTO public.notice_control_changes (notice_id, festival_id, effective_at)
    VALUES (changed_notice, old_scope, changed_at);
  END IF;
  IF new_approved THEN
    INSERT INTO public.notice_control_changes (notice_id, festival_id, effective_at)
    VALUES (changed_notice, new_scope, changed_at);
    ends_at := least(NEW.effective_to, NEW.ended_at);
    INSERT INTO public.notice_control_changes (notice_id, festival_id, effective_at)
    SELECT changed_notice, new_scope, t.effective_at
    FROM (VALUES (NEW.effective_from), (ends_at)) AS t(effective_at)
    WHERE t.effective_at > changed_at
      AND (ends_at IS NULL OR NEW.effective_from IS NULL OR NEW.effective_from < ends_at);
  END IF;

  UPDATE public.route_cache_entries c
  SET valid_until = changed_at
  WHERE c.valid_until > changed_at
    AND ((old_approved AND (old_scope IS NULL OR c.festival_id = old_scope))
      OR (new_approved AND (new_scope IS NULL OR c.festival_id = new_scope)));
  RETURN NULL;
END;
$$;

CREATE TRIGGER trg_notice_control_changes
AFTER INSERT OR UPDATE OF approval_status, festival_id, type, title, content, source_id, source_url,
  effective_from, effective_to, ended_at, geometry OR DELETE
ON public.official_notices FOR EACH ROW EXECUTE FUNCTION public.record_notice_control_change();

-- 새 캐시 행은 입력 당시 알려진 다음 효력 전이까지 쓸 수 있다.
CREATE FUNCTION public.limit_notice_cache_validity() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE
  observed_at TIMESTAMPTZ;
  next_change TIMESTAMPTZ;
  revision BIGINT;
  current_version TEXT;
BEGIN
  PERFORM pg_advisory_xact_lock_shared(hashtextextended('noldaga.notice:', 0));
  PERFORM pg_advisory_xact_lock_shared(hashtextextended('noldaga.notice:' || NEW.festival_id, 0));
  observed_at := clock_timestamp();

  SELECT min(nc.effective_at) FILTER (WHERE nc.effective_at > observed_at),
         count(*) FILTER (WHERE nc.effective_at <= observed_at)
  INTO next_change, revision
  FROM public.notice_control_changes nc
  WHERE nc.festival_id IS NULL OR nc.festival_id = NEW.festival_id;

  current_version := CASE WHEN revision = 0 THEN 'none' ELSE 'cv' || revision END;
  IF NEW.control_version IS NOT NULL AND NEW.control_version <> current_version THEN
    NEW.valid_until := least(NEW.valid_until, observed_at);
  ELSE
    NEW.valid_until := least(NEW.valid_until, next_change);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_notice_cache_validity
BEFORE INSERT ON public.route_cache_entries FOR EACH ROW EXECUTE FUNCTION public.limit_notice_cache_validity();
