-- run_tests.sh에서 tests_v0.3.2.sql의 시험 도우미와 T27 행을 준비한 뒤 실행한다.
-- -v applied=true|false -v probe_down=true|false
BEGIN;

\if :applied
SELECT t.expect_count('T017a 기존 순위·언급 수와 기본 신호 보존', $q$
  SELECT 1 FROM public.festival_trends
  WHERE source_id = 'trend_test' AND trend_ratio IS NULL AND signal = 'ok'
    AND (source_rank = 1 OR mention_count = 120)
$q$, 2);

INSERT INTO public.data_sources (source_id, name, scope, is_realtime)
VALUES ('trend_naver_datalab', '네이버 데이터랩', 'national', false);

INSERT INTO public.festival_trends (
  source_id, crawled_at, raw_title, festival_id, match_status, trend_ratio, signal
) VALUES
  ('trend_naver_datalab', now(), 'T017 증가율', 'fst_000001', 'matched', 1.2500, 'ok'),
  ('trend_naver_datalab', now(), 'T017 신호 없음', 'fst_000001', 'matched', NULL, 'no_signal'),
  ('trend_naver_datalab', now(), 'T017 미연결', NULL, 'unmatched', NULL, 'no_signal');

SET LOCAL ROLE noldaga_app;
SELECT t.expect_count('T017b 증가율·신호 저장 및 연결된 행만 공개', $q$
  SELECT 1 FROM public.festival_trends WHERE source_id = 'trend_naver_datalab'
    AND ((signal = 'ok' AND trend_ratio = 1.2500)
         OR (signal = 'no_signal' AND trend_ratio IS NULL))
$q$, 2);
RESET ROLE;

SELECT t.expect_error('T017c 음수 증가율 거부', $q$
  UPDATE public.festival_trends SET trend_ratio = -0.0001
  WHERE source_id = 'trend_naver_datalab' AND signal = 'ok'
$q$, 'festival_trends_trend_ratio_check');
SELECT t.expect_error('T017c 미정의 신호 거부', $q$
  UPDATE public.festival_trends SET signal = 'unknown'
  WHERE source_id = 'trend_naver_datalab' AND signal = 'ok'
$q$, 'festival_trends_signal_check');
SELECT t.expect_error('T017c NULL 신호 거부', $q$
  UPDATE public.festival_trends SET signal = NULL
  WHERE source_id = 'trend_naver_datalab' AND signal = 'ok'
$q$, 'null value in column "signal"');
SELECT t.expect_error('T017c 지표가 없는 ok 거부', $q$
  UPDATE public.festival_trends SET trend_ratio = NULL
  WHERE source_id = 'trend_naver_datalab' AND signal = 'ok'
$q$, 'festival_trends_measurement_check');
\else
SELECT t.expect_count('T017d 되돌리기 후 두 추가 컬럼 제거', $q$
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'festival_trends'
    AND column_name IN ('trend_ratio', 'signal')
$q$, 0);
SELECT t.expect_count('T017d 되돌리기 후 기존 행 보존', $q$
  SELECT 1 FROM public.festival_trends
  WHERE source_id = 'trend_test' AND (source_rank = 1 OR mention_count = 120)
$q$, 2);
SELECT t.expect_error('T017d 004 제약 복원', $q$
  INSERT INTO public.festival_trends (source_id, crawled_at, raw_title, match_status)
  VALUES ('trend_test', now(), 'T017 지표 없음', 'unmatched')
$q$, 'festival_trends_check1');
\endif

\if :probe_down
-- 같은 세션의 down SQL이 실패하면 연결이 닫히면서 시험 행도 롤백된다.
\else
ROLLBACK;
\endif
