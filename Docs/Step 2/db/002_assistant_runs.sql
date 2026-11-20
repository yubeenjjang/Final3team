-- 놀다가 DB 마이그레이션 002: 챗봇 작업 테이블 assistant_runs (API 설계서 v0.3.2 7-6, A06 비동기 작업)
-- 적용 순서: 001(= 04_DDL_v0.3.sql, 기본 30개 테이블) 다음. 되돌리기: 002_assistant_runs_down.sql
-- 작업 1건 = 1행. 상태 머신 queued → running → succeeded / retrying / failed (강사 11/19 워커 구조)

CREATE TABLE assistant_runs (
  run_id          TEXT PRIMARY KEY CHECK (run_id ~ '^run_[0-9A-Za-z]{6,26}$'),
  request_id      TEXT NOT NULL UNIQUE,                         -- A06 멱등 키(같은 질문 두 번 전송 방지)
  conversation_id TEXT NOT NULL CHECK (conversation_id ~ '^cv_[0-9A-Za-z]{6,26}$'),
  user_id         UUID REFERENCES users(user_id),               -- 로그인 사용자면 주인, 비로그인이면 NULL
  run_token_hash  TEXT,                                         -- 비로그인 조회 토큰(rat_…)의 해시. 원문 저장 안 함
  run_status      TEXT NOT NULL DEFAULT 'queued'
                    CHECK (run_status IN ('queued','running','retrying','succeeded','failed')),
  attempt         INT  NOT NULL DEFAULT 0 CHECK (attempt BETWEEN 0 AND 2),   -- 실행 횟수(재시도 1회까지)
  message         TEXT CHECK (char_length(message) BETWEEN 1 AND 500),     -- 질문. 보존 30일 뒤 NULL
  answer          TEXT,                                         -- 답변. 경로 구간·정류장 내용 금지(04 문서 7-0)
  error_code      TEXT,
  route_request_id TEXT REFERENCES route_requests(route_request_id) ON DELETE SET NULL,
  is_mock         BOOLEAN NOT NULL DEFAULT false,
  queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at      TIMESTAMPTZ,
  ended_at        TIMESTAMPTZ,
  purged_at       TIMESTAMPTZ,                                  -- 보존 기간이 지나 질문·답변을 지운 시각
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (user_id IS NOT NULL OR run_token_hash IS NOT NULL),    -- 주인을 확인할 방법이 반드시 하나
  CHECK (purged_at IS NOT NULL OR message IS NOT NULL),         -- 지우기 전에는 질문이 있어야 함
  CHECK (purged_at IS NULL OR (message IS NULL AND answer IS NULL)),
  CHECK (run_status <> 'succeeded' OR answer IS NOT NULL OR purged_at IS NOT NULL),
  CHECK (run_status <> 'failed' OR error_code IS NOT NULL)
);
CREATE INDEX idx_assistant_runs_status ON assistant_runs (run_status, started_at);   -- 멈춘 작업 정리
CREATE INDEX idx_assistant_runs_conversation ON assistant_runs (conversation_id, queued_at);

ALTER TABLE assistant_runs ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON assistant_runs TO noldaga_service;
-- API 서버(noldaga_app)는 로그인 사용자 본인 작업만 조회. 기록·상태 변경은 워커·서버 코드(noldaga_service)만.
-- 비로그인 작업은 서버가 run_token_hash를 확인한 뒤 noldaga_service로 읽음.
GRANT SELECT ON assistant_runs TO noldaga_app;
CREATE POLICY assistant_runs_select_own ON assistant_runs FOR SELECT TO noldaga_app
  USING (user_id IS NOT NULL AND user_id = app_current_user());
