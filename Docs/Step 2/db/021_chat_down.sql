DROP POLICY chat_members_own ON public.chat_members;
ALTER POLICY chat_messages_members ON public.chat_messages
  USING (deleted_at IS NULL AND created_at >= public.app_room_joined_at(room_id)
    AND EXISTS (
      SELECT 1 FROM public.chat_rooms r WHERE r.room_id = chat_messages.room_id
        AND (r.room_type <> 'companion' OR r.read_only_at IS NULL
             OR r.read_only_at > statement_timestamp() - interval '72 hours')
    ));
DROP FUNCTION public.app_chat_can_read(text);
DROP TRIGGER chat_close_on_block_change ON public.user_blocks;
DROP FUNCTION public.chat_close_on_block_change();
ALTER TABLE public.chat_rooms DROP CONSTRAINT chat_rooms_blocked_closed, DROP COLUMN closed_by_block;
-- Existing closed rooms stay closed on rollback.
