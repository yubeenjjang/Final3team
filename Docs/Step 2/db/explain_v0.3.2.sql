-- 축제 검색(A02) 인덱스 전후 실행 계획 — 다시 실행할 수 있는 측정 SQL (강사 DB 피드백 1)
-- 데이터: 가짜 축제 20,000건(7개 시·도, 2026년 1년에 고르게, 95% 게시). 실제 분포와 다를 수 있음 → 실제 수집 뒤 다시 잼
-- 쿼리: A02 기본 조회 "서울 · 11/21~22에 열리는 게시된 축제"
INSERT INTO festivals (festival_id, title, region_code, start_date, end_date, published_at)
SELECT 'fst_x' || lpad(g::text, 6, '0'),
       '모의 축제 ' || g,
       (ARRAY['SEOUL','BUSAN','DAEGU','INCHEON','GWANGJU','DAEJEON','GYEONGGI'])[1 + (g % 7)],
       date '2026-01-01' + ((g * 37) % 365),                -- 시작일: 1년에 고르게(같은 값이 다시 나오게 g로 계산)
       date '2026-01-01' + ((g * 37) % 365) + (g % 4),      -- 기간 1~4일
       CASE WHEN g % 20 <> 0 THEN now() END                 -- 95% 게시
FROM generate_series(1, 20000) g;
ANALYZE festivals;

\echo '--- (1) 인덱스를 쓰지 않게 했을 때 (enable_indexscan/bitmapscan off) ---'
BEGIN;
SET LOCAL enable_indexscan = off; SET LOCAL enable_bitmapscan = off;
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT festival_id, title, start_date, end_date FROM festivals
WHERE region_code = 'SEOUL' AND published_at IS NOT NULL
  AND start_date <= date '2026-11-22' AND end_date >= date '2026-11-21'
ORDER BY start_date;
COMMIT;

\echo '--- (2) idx_festivals_search (region_code, start_date, end_date) WHERE published_at IS NOT NULL 사용 ---'
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT festival_id, title, start_date, end_date FROM festivals
WHERE region_code = 'SEOUL' AND published_at IS NOT NULL
  AND start_date <= date '2026-11-22' AND end_date >= date '2026-11-21'
ORDER BY start_date;
