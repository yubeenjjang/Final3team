-- 놀다가 DB 마이그레이션 010 (2026-11-23, 축제 실제 조회 A03 `source_ref`)
-- 적용 순서: 001 → … → 009 → 010. 되돌리기: 010_festival_sources_public_down.sql
-- 이유: A03 응답의 `source_ref`(TourAPI contentid)는 festival_sources에 있는데, API 계정(noldaga_app)에는 이 표 권한이 없었다.
--       사용자 요청 안에서 noldaga_service를 섞지 않는다는 규칙(DB 설계서 3절 ⑥) 때문에, 공개 축제의 원본 번호 칸만 읽게 한다.
-- 데이터 변경 없음(권한·정책만). 손실 없음.
BEGIN;
-- 원본 번호·주소만. raw_checksum·fetched_at·last_job_id(수집 내부 정보)는 열지 않는다.
GRANT SELECT (festival_id, source_id, source_item_id, source_url) ON festival_sources TO noldaga_app;
-- 공개된 축제의 원본만 보인다(festivals는 noldaga_app에게 published_at IS NOT NULL만 보이므로 EXISTS도 그 범위).
CREATE POLICY festival_sources_public ON festival_sources FOR SELECT TO noldaga_app
  USING (EXISTS (SELECT 1 FROM festivals f WHERE f.festival_id = festival_sources.festival_id));
COMMIT;
