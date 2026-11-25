-- 0이면 적용 가능. 중복이 있으면 관계를 검토한 뒤 다시 검사한다.
SELECT count(*) AS duplicate_request_id_count
FROM (
  SELECT request_id
  FROM public.friendships
  WHERE request_id IS NOT NULL
  GROUP BY request_id
  HAVING count(*) > 1
) AS duplicates;
