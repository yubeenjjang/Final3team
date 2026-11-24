-- 수동 모집 마감은 정원 충족과 같은 공개 상태(full)를 사용한다.
ALTER TABLE public.companion_posts ADD COLUMN recruitment_closed_at timestamptz;
ALTER TABLE public.companion_posts ADD CONSTRAINT companion_posts_manual_close_status
  CHECK (recruitment_closed_at IS NULL OR status <> 'open');

-- A80의 정원 반환으로 수동 마감한 모집이 다시 열리지 않도록 한다.
CREATE FUNCTION public.keep_companion_recruitment_closed() RETURNS trigger
  LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
  IF NEW.recruitment_closed_at IS NOT NULL AND NEW.status = 'open' THEN
    NEW.status := 'full';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_keep_companion_recruitment_closed
  BEFORE UPDATE OF status ON public.companion_posts
  FOR EACH ROW EXECUTE FUNCTION public.keep_companion_recruitment_closed();

CREATE INDEX idx_companion_posts_auto_end ON public.companion_posts (meet_at)
  WHERE status IN ('open', 'full');
CREATE INDEX idx_companion_posts_retention ON public.companion_posts (ended_at)
  WHERE status IN ('ended', 'cancelled');

-- 참가자 조회는 정리 워커의 다음 실행 전에도 72시간 경계를 적용한다.
DROP POLICY meeting_places_members ON public.meeting_places;
CREATE POLICY meeting_places_members ON public.meeting_places FOR SELECT TO noldaga_app
  USING (EXISTS (
    SELECT 1 FROM public.companion_posts p WHERE p.post_id = meeting_places.post_id
      AND public.app_room_joined_at(p.room_id) IS NOT NULL
      AND (p.ended_at IS NULL OR p.ended_at > statement_timestamp() - interval '72 hours')
  ));

DROP POLICY chat_messages_members ON public.chat_messages;
CREATE POLICY chat_messages_members ON public.chat_messages FOR SELECT TO noldaga_app
  USING (deleted_at IS NULL AND created_at >= public.app_room_joined_at(room_id)
    AND EXISTS (
      SELECT 1 FROM public.chat_rooms r WHERE r.room_id = chat_messages.room_id
        AND (r.room_type <> 'companion' OR r.read_only_at IS NULL
             OR r.read_only_at > statement_timestamp() - interval '72 hours')
    ));
