-- 11/24 A42 최종안. 016 다음에 psql -1 -v ON_ERROR_STOP=1로 적용한다.
-- 004의 festival_trends_check1은 순위 또는 언급 수를 요구하는 제약이다.
ALTER TABLE public.festival_trends
  DROP CONSTRAINT festival_trends_check1,
  ADD COLUMN trend_ratio NUMERIC(10,4)
    CONSTRAINT festival_trends_trend_ratio_check CHECK (trend_ratio >= 0),
  ADD COLUMN signal TEXT NOT NULL DEFAULT 'ok'
    CONSTRAINT festival_trends_signal_check CHECK (signal IN ('ok', 'no_signal')),
  ADD CONSTRAINT festival_trends_measurement_check CHECK (
    source_rank IS NOT NULL OR mention_count IS NOT NULL
    OR trend_ratio IS NOT NULL OR signal = 'no_signal'
  );
