-- psql -1 -v ON_ERROR_STOP=1로 적용한다.
-- 004 제약을 만족하지 않는 행이 있으면 전체 되돌리기가 실패한다.
ALTER TABLE public.festival_trends
  ADD CONSTRAINT festival_trends_check1 CHECK (source_rank IS NOT NULL OR mention_count IS NOT NULL),
  DROP CONSTRAINT festival_trends_measurement_check,
  DROP COLUMN trend_ratio,
  DROP COLUMN signal;
