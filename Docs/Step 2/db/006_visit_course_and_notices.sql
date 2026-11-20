-- 놀다가 DB 마이그레이션 006 (2026-11-20, API·DB v0.3.3): AI 방문 코스(FR-P01·P03) + 공식 공지 관리자 등록·승인 이력(FR-O06·D05)
-- 적용 순서: 001 → … → 005 → 006. 되돌리기: 006_visit_course_and_notices_down.sql

-- ① AI 방문 코스: 챗봇과 같은 작업 테이블을 쓰고 종류만 구분(A51 → A06-1·A06-2로 조회)
ALTER TABLE assistant_runs
  ADD COLUMN run_kind TEXT NOT NULL DEFAULT 'chat' CHECK (run_kind IN ('chat','visit_course')),
  ADD COLUMN result   JSONB;                      -- 방문 코스 결과(장소 ID·시간·검증 여부). 경로 구간·카카오 장소 내용은 넣지 않음
ALTER TABLE assistant_runs
  ADD CONSTRAINT assistant_runs_result_kind CHECK (run_kind = 'visit_course' OR result IS NULL),
  ADD CONSTRAINT assistant_runs_result_purge CHECK (purged_at IS NULL OR result IS NULL);

-- ② 공식 공지 관리자 등록·수정·승인 이력: 추가만 가능(누가 언제 무엇을 바꿨는지)
CREATE TABLE notice_events (
  event_id        BIGSERIAL PRIMARY KEY,
  notice_id       TEXT NOT NULL REFERENCES official_notices(notice_id),
  action          TEXT NOT NULL CHECK (action IN ('create','update','approve','reject')),
  actor           UUID NOT NULL REFERENCES profiles(user_id),   -- 관리자
  before_value    JSONB,
  after_value     JSONB,
  reason          TEXT CHECK (char_length(reason) <= 300),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (action <> 'reject' OR reason IS NOT NULL)        -- 반려하면 이유 필수
);
CREATE INDEX idx_notice_events_notice ON notice_events (notice_id, created_at);
CREATE TRIGGER trg_notice_events_append_only BEFORE UPDATE OR DELETE ON notice_events
  FOR EACH ROW EXECUTE FUNCTION forbid_change();
ALTER TABLE notice_events ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT ON notice_events TO noldaga_service;
GRANT USAGE ON SEQUENCE notice_events_event_id_seq TO noldaga_service;
-- API 역할(noldaga_app)에는 권한 없음: 관리자 API가 권한 확인 뒤 noldaga_service로 기록
