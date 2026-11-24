-- 행과 외래키는 그대로 두고 015에서 추가한 UNIQUE만 제거한다.
ALTER TABLE public.friendships DROP CONSTRAINT friendships_request_id_key;
