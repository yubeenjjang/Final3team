-- 적용 전에 duplicate_keys_for_up, 되돌리기 전에 duplicate_keys_for_down이 0인지 확인한다.
SELECT count(*) FILTER (WHERE open_count > 1) AS duplicate_keys_for_up,
       count(*) FILTER (WHERE total_count > 1) AS duplicate_keys_for_down
FROM (
  SELECT count(*) FILTER (WHERE status <> 'closed') AS open_count,
         count(*) AS total_count
  FROM public.chat_rooms
  WHERE direct_key IS NOT NULL
  GROUP BY direct_key
) AS key_counts;
