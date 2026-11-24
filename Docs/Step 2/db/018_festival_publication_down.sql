-- 018 적용 뒤 승인·분류 변경이 없는 행만 이전 게시 상태로 복원한다.
LOCK TABLE public.festivals IN ACCESS EXCLUSIVE MODE;
UPDATE public.festivals f
SET review_status = h.before_value->>'review_status',
    published_at = (h.before_value->>'published_at')::timestamptz
FROM public.festival_change_history h
WHERE f.festival_id = h.festival_id
  AND h.field = 'source_classification'
  AND h.after_value @> '{"reason":"class_unverified","migration":"018"}'::jsonb
  AND f.category = 'festival' AND f.review_status = 'pending' AND f.published_at IS NULL
  AND nullif(btrim(f.source_class_level2), '') IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM public.festival_change_history later
    WHERE later.festival_id = h.festival_id AND later.change_id > h.change_id
      AND later.field IN ('review_status', 'published_at', 'source_class_level2', 'source_classification')
  );

DELETE FROM public.festival_change_history
WHERE field = 'source_classification'
  AND after_value @> '{"reason":"class_unverified","migration":"018"}'::jsonb;

ALTER POLICY festivals_public ON public.festivals
  USING (category = 'festival' AND review_status = 'approved' AND published_at IS NOT NULL);

ALTER TABLE public.festivals DROP COLUMN coords_source;
