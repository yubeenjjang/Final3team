-- 놀다가 DB 마이그레이션 004 (2026-11-20, API·DB v0.3.3)
-- ① 지금 핫한 축제(A42): 외부 사이트 크롤링 결과 저장 테이블 festival_trends (11/20 팀장 결정, LLM 사용 안 함)
-- ② 개인정보(11/20 한태경 검토): 목적지 원문 라벨을 DB에서 빼고(Redis 24시간만), 장소 해시는 행과 함께 지울 수 있게
-- 적용 순서: 001 → 002 → 003 → 004. 되돌리기: 004_trends_and_privacy_down.sql

-- ① 크롤링 결과: 공개 페이지에서 '축제 이름·순위·언급 수·주소'만 저장(본문·이미지·작성자 정보 저장 안 함)
CREATE TABLE festival_trends (
  trend_id        BIGSERIAL PRIMARY KEY,
  source_id       TEXT NOT NULL REFERENCES data_sources(source_id),       -- 크롤링한 사이트(예: trend_<사이트>)
  job_id          TEXT REFERENCES ingestion_jobs(job_id),                  -- 크롤링 작업 1회(A23 이력과 같은 표)
  crawled_at      TIMESTAMPTZ NOT NULL,
  raw_title       TEXT NOT NULL CHECK (char_length(raw_title) BETWEEN 1 AND 200),   -- 사이트에 적힌 축제 이름 그대로
  source_rank     INT CHECK (source_rank >= 1),                            -- 사이트의 순위(없으면 NULL)
  mention_count   INT CHECK (mention_count >= 0),                          -- 언급·검색 수(없으면 NULL)
  source_url      TEXT,
  festival_id     TEXT REFERENCES festivals(festival_id),                  -- 규칙으로 연결된 우리 축제
  match_status    TEXT NOT NULL CHECK (match_status IN ('matched','unmatched','ambiguous')),
  match_rule      TEXT,                                                    -- 예: 'name_norm+period'
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, crawled_at, raw_title),
  CHECK (match_status <> 'matched' OR festival_id IS NOT NULL),
  CHECK (source_rank IS NOT NULL OR mention_count IS NOT NULL)            -- 순위나 언급 수 중 하나는 있어야 '핫함'을 셈
);
CREATE INDEX idx_festival_trends_recent ON festival_trends (crawled_at DESC) WHERE match_status = 'matched';
ALTER TABLE festival_trends ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON festival_trends TO noldaga_service;
GRANT USAGE ON SEQUENCE festival_trends_trend_id_seq TO noldaga_service;
GRANT SELECT ON festival_trends TO noldaga_app;
-- 공개 API는 우리 축제와 연결된 행만 볼 수 있음(연결 안 된 이름은 화면에 안 나감)
CREATE POLICY festival_trends_public ON festival_trends FOR SELECT TO noldaga_app USING (match_status = 'matched');

-- ② 목적지·출발지 원문 라벨: DB에 두면 24시간 안에 지워도 매일 백업(7일)에 남음 → Redis route:label:{route_request_id}(24시간)로 옮김
ALTER TABLE route_requests DROP COLUMN user_place_label;
-- 장소 해시: 서버 비밀키를 섞은 HMAC-SHA256으로 만들고(역산 방지), 사건에 연결돼 30일 뒤에도 남는 행은 NULL로 지울 수 있게
ALTER TABLE route_requests ALTER COLUMN user_place_hash DROP NOT NULL;
COMMENT ON COLUMN route_requests.user_place_hash IS 'HMAC-SHA256(서버 비밀키, 정규화 장소). 30일 뒤 행 삭제, 사건 연결 행은 이 칸만 NULL';
