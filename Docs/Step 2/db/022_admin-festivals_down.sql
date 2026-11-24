-- 감사 사유와 작업자 정보가 기록된 DB에서는 이력을 보존한다.
LOCK TABLE public.festival_change_history IN ACCESS EXCLUSIVE MODE;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.festival_change_history WHERE actor_user_id IS NOT NULL) THEN
    RAISE EXCEPTION '022_admin-festivals: 등록·수정 감사 이력이 있습니다';
  END IF;
END $$;

DROP INDEX public.idx_festivals_registration_identity;
ALTER TABLE public.festival_change_history DROP COLUMN reason, DROP COLUMN actor_user_id;
-- admin_manual은 공지에서도 참조할 수 있는 공용 공급원으로 유지한다.
