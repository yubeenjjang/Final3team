-- 닫힌 방을 포함해 중복 키가 있으면 UNIQUE 복원이 실패하며 트랜잭션을 되돌린다. psql -1로 실행한다.
LOCK TABLE public.chat_rooms IN ACCESS EXCLUSIVE MODE;

ALTER TABLE public.chat_rooms ADD CONSTRAINT chat_rooms_direct_key_key UNIQUE (direct_key);
DROP INDEX public.uq_chat_rooms_direct_key_not_closed;
