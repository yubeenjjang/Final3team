-- 007·016에 이어 차단 이력과 메시지 열람/보존 정책을 적용한다.
ALTER TABLE public.chat_rooms ADD COLUMN closed_by_block boolean NOT NULL DEFAULT false;
ALTER TABLE public.chat_rooms ADD CONSTRAINT chat_rooms_blocked_closed
  CHECK (NOT closed_by_block OR (room_type = 'direct' AND status = 'closed'));

-- 기존의 닫힌 1:1 방은 닫힌 사유를 알 수 없으므로 보호한다.
UPDATE public.chat_rooms SET closed_by_block = true
WHERE room_type = 'direct' AND status = 'closed';

CREATE FUNCTION public.chat_close_on_block_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE
  a uuid;
  b uuid;
  pair_key text;
BEGIN
  IF TG_OP = 'INSERT' THEN
    a := NEW.blocker;
    b := NEW.blocked;
  ELSE
    a := OLD.blocker;
    b := OLD.blocked;
  END IF;
  pair_key := LEAST(a, b)::text || '|' || GREATEST(a, b)::text;
  PERFORM pg_advisory_xact_lock(hashtextextended('chat:direct:' || pair_key, 0));
  UPDATE public.chat_rooms SET status = 'closed', closed_by_block = true
  WHERE direct_key = pair_key AND status <> 'closed';
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END $$;

REVOKE ALL ON FUNCTION public.chat_close_on_block_change() FROM PUBLIC;
CREATE TRIGGER chat_close_on_block_change
  AFTER INSERT OR DELETE ON public.user_blocks
  FOR EACH ROW EXECUTE FUNCTION public.chat_close_on_block_change();

-- Covers block rows that existed before this migration.
UPDATE public.chat_rooms r SET status = 'closed', closed_by_block = true
WHERE r.room_type = 'direct' AND r.status <> 'closed' AND EXISTS (
  SELECT 1 FROM public.user_blocks b
  WHERE r.direct_key = LEAST(b.blocker, b.blocked)::text || '|' || GREATEST(b.blocker, b.blocked)::text
);

-- Existing app role policies intentionally hide incoming blocks. Expose only
-- the caller's access to this room to the app role, with no block rows returned.
CREATE FUNCTION public.app_chat_can_read(p_room text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.chat_rooms r
    JOIN public.chat_members m ON m.room_id = r.room_id
    WHERE r.room_id = p_room AND m.user_id = public.app_current_user() AND m.status = 'joined'
      AND NOT r.closed_by_block
      AND (r.room_type <> 'direct' OR NOT EXISTS (
        SELECT 1 FROM public.user_blocks b
        JOIN public.chat_members peer ON peer.room_id = r.room_id AND peer.user_id <> m.user_id
        WHERE (b.blocker = m.user_id AND b.blocked = peer.user_id)
           OR (b.blocker = peer.user_id AND b.blocked = m.user_id)
      ))
  )
$$;
REVOKE ALL ON FUNCTION public.app_chat_can_read(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.app_chat_can_read(text) TO noldaga_app;

CREATE POLICY chat_members_own ON public.chat_members FOR SELECT TO noldaga_app
  USING (user_id = public.app_current_user());

ALTER POLICY chat_messages_members ON public.chat_messages USING (
  deleted_at IS NULL AND created_at >= public.app_room_joined_at(room_id)
  AND public.app_chat_can_read(room_id)
  AND EXISTS (
    SELECT 1 FROM public.chat_rooms r WHERE r.room_id = chat_messages.room_id
    AND CASE WHEN r.room_type = 'companion'
      THEN r.read_only_at IS NULL OR r.read_only_at > statement_timestamp() - interval '72 hours'
      ELSE chat_messages.created_at > statement_timestamp() - interval '720 hours'
    END
  )
);
