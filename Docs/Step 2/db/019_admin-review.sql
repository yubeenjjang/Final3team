-- 018 뒤 파일 단위 트랜잭션으로 적용한다.
ALTER TABLE public.festival_review_queue
  DROP CONSTRAINT festival_review_queue_reason_check,
  ADD CONSTRAINT festival_review_queue_reason_check CHECK (reason IN (
    'duplicate', 'conflict', 'missing_location', 'date_unclear',
    'not_festival_class', 'class_unverified', 'missing_from_source', 'coords_out_of_range'
  ));

CREATE INDEX idx_festival_review_queue_listing
  ON public.festival_review_queue (approval_status, created_at DESC, queue_id DESC);
CREATE INDEX idx_festival_review_queue_pending_reason
  ON public.festival_review_queue (festival_id, reason) WHERE approval_status = 'pending';

-- 이번 이전에 검토 대기로 저장된 TourAPI 행은 현재 품질과 마지막 원본 확인 이력을 사용한다.
WITH pending AS (
  SELECT f.*,
    (SELECT h.after_value ->> 'reason'
       FROM public.festival_change_history h
      WHERE h.festival_id = f.festival_id AND h.source_id = 'tourapi' AND h.field = 'source_presence'
      ORDER BY h.change_id DESC LIMIT 1) AS source_presence
  FROM public.festivals f
  WHERE f.review_status = 'pending' AND (
    EXISTS (SELECT 1 FROM public.festival_sources s
             WHERE s.festival_id = f.festival_id AND s.source_id = 'tourapi')
    OR EXISTS (SELECT 1 FROM public.festival_change_history h
               WHERE h.festival_id = f.festival_id AND h.source_id = 'tourapi'
                 AND h.field IN ('source_classification', 'source_presence'))
  )
)
INSERT INTO public.festival_review_queue (festival_id, reason)
SELECT p.festival_id, candidate.reason
FROM pending p
CROSS JOIN LATERAL (VALUES
  ('class_unverified', nullif(btrim(p.source_class_level2), '') IS NULL),
  ('not_festival_class', nullif(btrim(p.source_class_level2), '') <> 'EV01'),
  ('missing_from_source', p.source_presence = 'missing_from_source'),
  ('coords_out_of_range', p.source_class_level2 = 'EV01' AND nullif(btrim(p.address), '') IS NOT NULL
    AND (p.latitude IS NULL OR p.longitude IS NULL))
) candidate(reason, holds)
WHERE candidate.holds AND NOT EXISTS (
  SELECT 1 FROM public.festival_review_queue q
  WHERE q.festival_id = p.festival_id AND q.reason = candidate.reason
);
