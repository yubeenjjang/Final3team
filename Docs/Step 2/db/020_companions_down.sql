DROP POLICY chat_messages_members ON public.chat_messages;
CREATE POLICY chat_messages_members ON public.chat_messages FOR SELECT TO noldaga_app
  USING (deleted_at IS NULL AND created_at >= public.app_room_joined_at(room_id));

DROP POLICY meeting_places_members ON public.meeting_places;
CREATE POLICY meeting_places_members ON public.meeting_places FOR SELECT TO noldaga_app
  USING (public.app_room_joined_at((SELECT room_id FROM public.companion_posts p
                                 WHERE p.post_id = meeting_places.post_id)) IS NOT NULL);

DROP INDEX public.idx_companion_posts_retention;
DROP INDEX public.idx_companion_posts_auto_end;
DROP TRIGGER trg_keep_companion_recruitment_closed ON public.companion_posts;
DROP FUNCTION public.keep_companion_recruitment_closed();
ALTER TABLE public.companion_posts DROP CONSTRAINT companion_posts_manual_close_status,
  DROP COLUMN recruitment_closed_at;
