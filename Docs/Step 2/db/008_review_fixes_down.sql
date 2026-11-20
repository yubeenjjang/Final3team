-- 008 되돌리기
DROP FUNCTION IF EXISTS app_public_display_name(UUID);
ALTER TABLE load_simulations DROP CONSTRAINT IF EXISTS load_simulations_check;
ALTER TABLE load_simulations DROP COLUMN IF EXISTS limits_version, DROP COLUMN IF EXISTS stop_requested_at, DROP COLUMN IF EXISTS error;
CREATE OR REPLACE FUNCTION recovery_attempt_complete_once() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.validation_result <> 'pending' THEN
    RAISE EXCEPTION 'recovery_attempts: 판정이 끝난 시도는 바꿀 수 없습니다';
  END IF;
  IF (NEW.attempt_id, NEW.plan_id, NEW.incident_id, NEW.action, NEW.action_enabled_at, NEW.created_at)
     IS DISTINCT FROM (OLD.attempt_id, OLD.plan_id, OLD.incident_id, OLD.action, OLD.action_enabled_at, OLD.created_at) THEN
    RAISE EXCEPTION 'recovery_attempts: 결과 칸만 채울 수 있습니다';
  END IF;
  RETURN NEW;
END $$;
DROP POLICY companion_posts_public ON companion_posts;
CREATE POLICY companion_posts_public ON companion_posts FOR SELECT TO noldaga_app USING (true);
ALTER TABLE companion_posts DROP COLUMN IF EXISTS hidden_by, DROP COLUMN IF EXISTS hidden_at;
ALTER FUNCTION app_room_joined_at(TEXT) SET search_path = public;
ALTER FUNCTION app_room_visible(TEXT)   SET search_path = public;
DROP POLICY festivals_public ON festivals;
CREATE POLICY festivals_public ON festivals FOR SELECT TO noldaga_app USING (published_at IS NOT NULL);
REVOKE UPDATE (nickname_searchable) ON profiles FROM noldaga_app;
