-- 놀다가 DB 마이그레이션 005 (2026-11-20, API·DB v0.3.3): 맞춤 추천(취향·축제 태그·일간 지표) + 친구(신청·관계·차단)
-- 적용 순서: 001 → 002 → 003 → 004 → 005. 되돌리기: 005_recommend_and_friends_down.sql
-- 기준: 기획서 FR-REC01~16, FR-COM12~14, 11/20 팀 결정(취향 5개, 권한 기준안), API 설계서 6-4절

-- ===== 맞춤 추천 =====
-- 사용자 취향(A36·A37): 5개 중 여러 개(FR-REC03). 반려견은 취향 값 'pet' 하나(별도 칸 없음), 아기(영유아) 동반은 뺌 — 기획서 11/20 15:32
CREATE TABLE user_festival_preferences (
  user_id         UUID PRIMARY KEY REFERENCES users(user_id),
  scenarios       TEXT[] NOT NULL DEFAULT '{}'
                    CHECK (scenarios <@ ARRAY['family_relaxed','friends_activity','couple_photo','pet','solo']::text[]),
  onboarding_status TEXT NOT NULL DEFAULT 'pending' CHECK (onboarding_status IN ('pending','completed','skipped')),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (onboarding_status <> 'completed' OR cardinality(scenarios) >= 1)   -- 아무것도 안 고르고 완료 = 건너뛰기(FR-REC04)
);

-- 축제 태그(분류 결과): 규칙이 후보를 만들고 LLM이 공식 원문 근거로 검증. 검증된 것만 추천에 씀(FR-REC08·09)
CREATE TABLE festival_tags (
  tag_id          BIGSERIAL PRIMARY KEY,
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  tag             TEXT NOT NULL CHECK (tag IN ('family_program','relaxed','activity','photo_spot',
                    'pet_allowed','solo_friendly')),
  status          TEXT NOT NULL DEFAULT 'candidate'
                    CHECK (status IN ('candidate','verified','rejected','insufficient','revoked')),
  rule_id         TEXT NOT NULL,                        -- 후보를 만든 규칙(예: kw_photo_v1)
  evidence_field  TEXT CHECK (evidence_field IN ('overview','program','subevent','agelimit','playtime','festivaltype','cat3','visit_forecast')),
  evidence_quote  TEXT CHECK (char_length(evidence_quote) <= 300),   -- 공식 원문에서 그대로 옮긴 근거 문장
  source_checksum TEXT NOT NULL,                        -- 분류에 쓴 원문 버전(festival_sources.raw_checksum). 원문이 바뀌면 다시 분류
  verified_by     TEXT CHECK (verified_by IN ('llm','rule','admin')),
  model           TEXT,                                 -- LLM 모델 ID
  prompt_version  TEXT,
  decided_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (festival_id, tag, source_checksum),
  CHECK (status <> 'verified' OR (evidence_quote IS NOT NULL AND evidence_field IS NOT NULL AND verified_by IS NOT NULL AND decided_at IS NOT NULL)),
  CHECK (verified_by <> 'llm' OR (model IS NOT NULL AND prompt_version IS NOT NULL)),
  -- 반려견 동반은 공식 원문에 명시된 경우만(수치·예측 데이터로 추정 금지)
  CHECK (tag <> 'pet_allowed' OR status <> 'verified' OR evidence_field IN ('overview','program','subevent','agelimit'))
);
CREATE INDEX idx_festival_tags_verified ON festival_tags (tag, festival_id) WHERE status = 'verified';

-- 일간 지표(A39 인기): 사람 1명 = 하루 1회만 셈(중복·봇은 Redis에서 거른 뒤 숫자만 저장)
CREATE TABLE festival_engagement_daily (
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  day             DATE NOT NULL,
  detail_views    INT NOT NULL DEFAULT 0 CHECK (detail_views >= 0),
  favorites_added INT NOT NULL DEFAULT 0 CHECK (favorites_added >= 0),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (festival_id, day)
);

-- ===== 친구 =====
-- 친구 코드(검색 기본)·닉네임 공개 동의(FR-COM12, 11/20 권한 기준안)
ALTER TABLE profiles
  ADD COLUMN friend_code TEXT UNIQUE CHECK (friend_code ~ '^[A-Z0-9]{8}$'),
  ADD COLUMN nickname_searchable BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE friend_requests (
  request_id      TEXT PRIMARY KEY CHECK (request_id ~ '^frq_[0-9A-Za-z]{6,26}$'),
  from_user       UUID NOT NULL REFERENCES users(user_id),
  to_user         UUID NOT NULL REFERENCES users(user_id),
  status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','rejected','cancelled')),
  responded_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (from_user <> to_user),
  CHECK (status = 'pending' OR responded_at IS NOT NULL)
);
-- 같은 두 사람 사이에 대기 중 신청은 방향과 상관없이 1개만
CREATE UNIQUE INDEX uq_friend_requests_pending ON friend_requests (LEAST(from_user, to_user), GREATEST(from_user, to_user)) WHERE status = 'pending';

-- 친구 관계: 한 쌍 = 한 행(작은 ID가 user_a). 동행 승인으로 자동 생성하지 않음(친구 추가로만)
CREATE TABLE friendships (
  user_a          UUID NOT NULL REFERENCES users(user_id),
  user_b          UUID NOT NULL REFERENCES users(user_id),
  request_id      TEXT REFERENCES friend_requests(request_id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_a, user_b),
  CHECK (user_a < user_b)
);

-- 차단: 방향 있음(blocker → blocked). 차단하면 친구 관계 해제, 해제해도 자동 복원 안 함
CREATE TABLE user_blocks (
  blocker         UUID NOT NULL REFERENCES users(user_id),
  blocked         UUID NOT NULL REFERENCES users(user_id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (blocker, blocked),
  CHECK (blocker <> blocked)
);

-- ===== 권한 =====
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['user_festival_preferences','festival_tags','festival_engagement_daily','friend_requests','friendships','user_blocks'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %I TO noldaga_service', t);
  END LOOP;
END $$;
GRANT USAGE ON SEQUENCE festival_tags_tag_id_seq TO noldaga_service;
-- 취향: 본인만 조회·저장(FR-REC16)
GRANT SELECT, INSERT, UPDATE ON user_festival_preferences TO noldaga_app;
CREATE POLICY prefs_own ON user_festival_preferences FOR ALL TO noldaga_app
  USING (user_id = app_current_user()) WITH CHECK (user_id = app_current_user());
-- 태그: 검증된 것만 공개. 분류·검증 기록은 워커(noldaga_service)만
GRANT SELECT ON festival_tags TO noldaga_app;
CREATE POLICY festival_tags_public ON festival_tags FOR SELECT TO noldaga_app USING (status = 'verified');
-- 일간 지표: 숫자만이라 공개 조회, 쓰기는 서버 코드만
GRANT SELECT ON festival_engagement_daily TO noldaga_app;
CREATE POLICY engagement_public ON festival_engagement_daily FOR SELECT TO noldaga_app USING (true);
-- 친구 신청·관계·차단: 당사자만 조회. 쓰기는 두 사람이 얽혀 있어 서버 코드(noldaga_service)가 한 트랜잭션으로
GRANT SELECT ON friend_requests, friendships, user_blocks TO noldaga_app;
CREATE POLICY friend_requests_party ON friend_requests FOR SELECT TO noldaga_app
  USING (app_current_user() IN (from_user, to_user));
CREATE POLICY friendships_party ON friendships FOR SELECT TO noldaga_app
  USING (app_current_user() IN (user_a, user_b));
CREATE POLICY user_blocks_own ON user_blocks FOR SELECT TO noldaga_app
  USING (blocker = app_current_user());               -- 차단당한 사람은 차단 사실을 볼 수 없음
