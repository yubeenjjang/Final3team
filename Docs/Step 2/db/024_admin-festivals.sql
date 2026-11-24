-- A55·A56 감사 이력과 등록 중복 확인. 021 다음 파일 단위 트랜잭션에서 실행한다.
INSERT INTO public.data_sources (source_id, name, scope, is_realtime, status)
VALUES ('admin_manual', '관리자 직접 등록', 'national', false, 'verified')
ON CONFLICT (source_id) DO NOTHING;

ALTER TABLE public.festival_change_history
  ADD COLUMN reason TEXT,
  ADD COLUMN actor_user_id UUID,
  ADD CONSTRAINT festival_change_history_admin_audit_check CHECK (
    (reason IS NULL AND actor_user_id IS NULL)
    OR (actor = 'admin' AND reason IS NOT NULL AND btrim(reason) <> '' AND actor_user_id IS NOT NULL)
  );

CREATE INDEX idx_festivals_registration_identity
  ON public.festivals (start_date, end_date)
  WHERE category = 'festival';
