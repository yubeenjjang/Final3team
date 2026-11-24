-- 파일 단위 트랜잭션에서 실행한다. 새 사유로 처리된 결정이 있으면 롤백을 중단한다.
LOCK TABLE public.festival_review_queue IN ACCESS EXCLUSIVE MODE;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.festival_review_queue
    WHERE reason IN ('not_festival_class', 'class_unverified', 'missing_from_source', 'coords_out_of_range')
      AND approval_status <> 'pending'
  ) THEN
    RAISE EXCEPTION '019_admin-review: 새 사유로 처리된 검토 이력이 있어 되돌릴 수 없습니다';
  END IF;
END $$;

DELETE FROM public.festival_review_queue
WHERE reason IN ('not_festival_class', 'class_unverified', 'missing_from_source', 'coords_out_of_range');

DROP INDEX public.idx_festival_review_queue_listing, public.idx_festival_review_queue_pending_reason;
ALTER TABLE public.festival_review_queue
  DROP CONSTRAINT festival_review_queue_reason_check,
  ADD CONSTRAINT festival_review_queue_reason_check
    CHECK (reason IN ('duplicate', 'conflict', 'missing_location', 'date_unclear'));
