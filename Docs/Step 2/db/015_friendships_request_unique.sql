-- A46: 수락한 신청 1건에서 친구 관계는 최대 1건. psql -1로 적용한다.
-- 검사와 제약 추가 사이에 다른 트랜잭션이 중복 행을 쓰지 못하게 한다.
LOCK TABLE public.friendships IN ACCESS EXCLUSIVE MODE;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.friendships
    WHERE request_id IS NOT NULL
    GROUP BY request_id
    HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION '015: 중복된 friendships.request_id가 있어 적용을 중단합니다'
      USING HINT = 'precheck_015_friendships_request_unique.sql로 확인하세요';
  END IF;
END $$;

ALTER TABLE public.friendships
  ADD CONSTRAINT friendships_request_id_key UNIQUE (request_id);
