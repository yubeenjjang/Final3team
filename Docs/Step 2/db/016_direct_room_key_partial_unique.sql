-- A49·A50·A67: 닫힌 1:1 방은 보존하고 같은 사용자 쌍의 새 방을 허용한다. psql -1로 적용한다.
LOCK TABLE public.chat_rooms IN ACCESS EXCLUSIVE MODE;

CREATE UNIQUE INDEX uq_chat_rooms_direct_key_not_closed
  ON public.chat_rooms (direct_key)
  WHERE status <> 'closed';

ALTER TABLE public.chat_rooms DROP CONSTRAINT chat_rooms_direct_key_key;
