-- 놀다가 DB 마이그레이션 007 (2026-11-20, API·DB v0.3.3): 동행·채팅·알림·신고 (FR-COM01~11·15~24)
-- 기준: 기획서 5.18~5.20, WBS W114~W122, 11/20 팀 결정(채팅 WebSocket, 동행 종료 뒤 3일·친구 채팅 30일, 채팅 열람 = 참여자·관리자, 권한 기준안)
-- 적용 순서: 001 → … → 006 → 007. 되돌리기: 007_companion_chat_notifications_down.sql

-- ===== 채팅방 (동행방·1:1·친구 단체방 공통) =====
CREATE TABLE chat_rooms (
  room_id         TEXT PRIMARY KEY CHECK (room_id ~ '^crm_[0-9A-Za-z]{6,26}$'),
  room_type       TEXT NOT NULL CHECK (room_type IN ('companion','direct','friend_group')),
  name            TEXT CHECK (char_length(name) BETWEEN 1 AND 40),
  owner_id        UUID REFERENCES users(user_id),                   -- 방장(direct는 NULL)
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','read_only','closed')),
  direct_key      TEXT UNIQUE,                                      -- 1:1 방 중복 방지: '작은ID|큰ID'
  last_seq        BIGINT NOT NULL DEFAULT 0,                        -- 방별 메시지 순서 발급용
  read_only_at    TIMESTAMPTZ,                                      -- 동행 종료 시각(보존 3일의 기준)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((room_type = 'direct') = (direct_key IS NOT NULL)),
  CHECK (room_type <> 'friend_group' OR name IS NOT NULL),
  CHECK (status = 'active' OR read_only_at IS NOT NULL OR status = 'closed')
);

-- ===== 동행 =====
CREATE TABLE companion_posts (
  post_id         TEXT PRIMARY KEY CHECK (post_id ~ '^cpo_[0-9A-Za-z]{6,26}$'),
  festival_id     TEXT NOT NULL REFERENCES festivals(festival_id),
  author_id       UUID NOT NULL REFERENCES users(user_id),
  room_id         TEXT NOT NULL UNIQUE REFERENCES chat_rooms(room_id),   -- 게시 때 작성자만 있는 동행방 1개(FR-COM04)
  meet_at         TIMESTAMPTZ NOT NULL,
  capacity        INT NOT NULL CHECK (capacity BETWEEN 1 AND 10),         -- 작성자 제외 모집 인원(FR-COM03)
  approved_count  INT NOT NULL DEFAULT 0,
  age_pref        TEXT CHECK (age_pref IN ('any','20s','30s','40s','50s_plus')),
  gender_pref     TEXT NOT NULL DEFAULT 'any' CHECK (gender_pref IN ('any','female','male')),
  memo            TEXT CHECK (char_length(memo) <= 500),
  status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','full','ended','cancelled')),
  ended_at        TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (approved_count BETWEEN 0 AND capacity),                          -- 동시 승인으로 정원 초과 방지(FR-COM06)
  CHECK (status NOT IN ('ended','cancelled') OR ended_at IS NOT NULL)
);
CREATE INDEX idx_companion_posts_festival ON companion_posts (festival_id, status, meet_at);

CREATE TABLE companion_applications (
  application_id  TEXT PRIMARY KEY CHECK (application_id ~ '^cap_[0-9A-Za-z]{6,26}$'),
  post_id         TEXT NOT NULL REFERENCES companion_posts(post_id),
  applicant_id    UUID NOT NULL REFERENCES users(user_id),
  message         TEXT CHECK (char_length(message) <= 200),
  status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','cancelled')),
  decided_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (status = 'pending' OR decided_at IS NOT NULL)
);
-- 재신청 규칙: 취소하면 다시 신청 가능, 대기·승인·거절 상태가 있으면 같은 글에 또 신청 불가(FR-COM05)
CREATE UNIQUE INDEX uq_companion_applications_active ON companion_applications (post_id, applicant_id)
  WHERE status IN ('pending','approved','rejected');

-- 정확한 만남 장소: 작성자만 쓰고, 작성자·승인 참여자만 봄(FR-COM08·10·11)
CREATE TABLE meeting_places (
  post_id         TEXT PRIMARY KEY REFERENCES companion_posts(post_id),
  name            TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 60),
  address         TEXT,
  lat             NUMERIC(9,6) CHECK (lat BETWEEN 33 AND 39),
  lng             NUMERIC(9,6) CHECK (lng BETWEEN 124 AND 132),
  guide           TEXT CHECK (char_length(guide) <= 300),
  updated_by      UUID NOT NULL REFERENCES users(user_id),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((lat IS NULL) = (lng IS NULL))                                   -- 지도 오류 시 이름·주소만(텍스트)으로도 가능
);

-- ===== 채팅 멤버·메시지 =====
CREATE TABLE chat_members (
  room_id         TEXT NOT NULL REFERENCES chat_rooms(room_id),
  user_id         UUID NOT NULL REFERENCES users(user_id),
  role            TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','member')),
  status          TEXT NOT NULL CHECK (status IN ('invited','joined','declined','left','removed')),
  invited_by      UUID REFERENCES users(user_id),
  invited_at      TIMESTAMPTZ,
  joined_at       TIMESTAMPTZ,                                            -- 이 시각 이후 메시지만 보임(FR-COM16)
  left_at         TIMESTAMPTZ,
  last_read_seq   BIGINT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (room_id, user_id),
  CHECK (status <> 'joined' OR joined_at IS NOT NULL),
  CHECK (status NOT IN ('left','removed') OR left_at IS NOT NULL)
);
CREATE INDEX idx_chat_members_user ON chat_members (user_id, status);

CREATE TABLE chat_messages (
  message_id      BIGSERIAL PRIMARY KEY,
  room_id         TEXT NOT NULL REFERENCES chat_rooms(room_id),
  seq             BIGINT NOT NULL,                                        -- 방별 순서(chat_rooms.last_seq에서 발급)
  sender_id       UUID REFERENCES users(user_id),                         -- 시스템 메시지는 NULL
  msg_type        TEXT NOT NULL CHECK (msg_type IN ('text','system')),
  body            TEXT CHECK (char_length(body) BETWEEN 1 AND 1000),
  client_message_id TEXT CHECK (char_length(client_message_id) BETWEEN 8 AND 64),   -- 재전송 중복 방지
  deleted_at      TIMESTAMPTZ,                                            -- 보존 기간 정리·신고 처리
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (room_id, seq),
  UNIQUE (room_id, sender_id, client_message_id),
  CHECK (msg_type <> 'text' OR (sender_id IS NOT NULL AND client_message_id IS NOT NULL)),
  CHECK (deleted_at IS NOT NULL OR body IS NOT NULL)
);
CREATE INDEX idx_chat_messages_room_time ON chat_messages (room_id, created_at);

-- ===== 알림 (앱 안 알림만, 외부 푸시는 범위 밖) =====
CREATE TABLE notifications (
  notification_id BIGSERIAL PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(user_id),
  type            TEXT NOT NULL CHECK (type IN ('companion_applied','companion_approved','companion_rejected','companion_ended',
                    'companion_cancelled','meeting_place_changed','friend_requested','friend_accepted','room_invited')),
  ref_type        TEXT NOT NULL CHECK (ref_type IN ('companion_post','companion_application','friend_request','chat_room')),
  ref_id          TEXT NOT NULL,
  read_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user ON notifications (user_id, created_at DESC);

-- ===== 신고·관리자 열람 기록 (FR-COM23, 11/20 '채팅 열람 = 참여자·관리자') =====
CREATE TABLE reports (
  report_id       TEXT PRIMARY KEY CHECK (report_id ~ '^rpt_[0-9A-Za-z]{6,26}$'),
  reporter_id     UUID NOT NULL REFERENCES users(user_id),
  target_type     TEXT NOT NULL CHECK (target_type IN ('companion_post','chat_message','user')),
  target_id       TEXT NOT NULL,
  reason          TEXT NOT NULL CHECK (reason IN ('spam','abuse','harassment','fraud','privacy','other')),
  detail          TEXT CHECK (char_length(detail) <= 500),
  status          TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received','reviewing','actioned','dismissed')),
  handled_by      UUID REFERENCES profiles(user_id),
  handled_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (status IN ('received','reviewing') OR (handled_by IS NOT NULL AND handled_at IS NOT NULL))
);
-- 관리자가 채팅을 볼 때마다 한 줄(누가·어느 방·왜). 추가만 가능
CREATE TABLE chat_admin_access (
  access_id       BIGSERIAL PRIMARY KEY,
  admin_id        UUID NOT NULL REFERENCES profiles(user_id),
  room_id         TEXT NOT NULL REFERENCES chat_rooms(room_id),
  report_id       TEXT REFERENCES reports(report_id),
  reason          TEXT NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 200),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_chat_admin_access_append_only BEFORE UPDATE OR DELETE ON chat_admin_access
  FOR EACH ROW EXECUTE FUNCTION forbid_change();

-- ===== 권한 =====
-- RLS 정책 안에서 chat_members를 다시 읽으면 무한 반복이 되므로, 멤버 확인은 함수 하나로(SECURITY DEFINER, 읽기만)
CREATE FUNCTION app_room_joined_at(p_room TEXT) RETURNS timestamptz
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS
  $$ SELECT joined_at FROM chat_members WHERE room_id = p_room AND user_id = app_current_user() AND status = 'joined' $$;
CREATE FUNCTION app_room_visible(p_room TEXT) RETURNS boolean
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS
  $$ SELECT EXISTS (SELECT 1 FROM chat_members WHERE room_id = p_room AND user_id = app_current_user() AND status IN ('invited','joined')) $$;
REVOKE ALL ON FUNCTION app_room_joined_at(TEXT), app_room_visible(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_room_joined_at(TEXT), app_room_visible(TEXT) TO noldaga_app;

DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['chat_rooms','companion_posts','companion_applications','meeting_places','chat_members',
                           'chat_messages','notifications','reports','chat_admin_access'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %I TO noldaga_service', t);
  END LOOP;
END $$;
GRANT USAGE ON SEQUENCE chat_messages_message_id_seq, notifications_notification_id_seq, chat_admin_access_access_id_seq TO noldaga_service;
REVOKE UPDATE, DELETE ON chat_admin_access FROM noldaga_service;

-- 앱 역할(noldaga_app)은 조회만(읽음 표시 제외). 쓰기는 정원·멤버·순서가 함께 바뀌어 서버 코드가 noldaga_service로 한 트랜잭션에서
GRANT SELECT ON companion_posts, companion_applications, meeting_places, chat_rooms, chat_members, chat_messages, notifications, reports TO noldaga_app;
GRANT UPDATE (read_at) ON notifications TO noldaga_app;
CREATE POLICY companion_posts_public ON companion_posts FOR SELECT TO noldaga_app USING (true);      -- 공개 정보(장소 제외)
CREATE POLICY companion_applications_party ON companion_applications FOR SELECT TO noldaga_app
  USING (applicant_id = app_current_user()
         OR EXISTS (SELECT 1 FROM companion_posts p WHERE p.post_id = companion_applications.post_id AND p.author_id = app_current_user()));
CREATE POLICY meeting_places_members ON meeting_places FOR SELECT TO noldaga_app
  USING (app_room_joined_at((SELECT room_id FROM companion_posts p WHERE p.post_id = meeting_places.post_id)) IS NOT NULL);
CREATE POLICY chat_rooms_members ON chat_rooms FOR SELECT TO noldaga_app USING (app_room_visible(room_id));
CREATE POLICY chat_members_same_room ON chat_members FOR SELECT TO noldaga_app USING (app_room_visible(room_id));
-- 메시지: 지금 입장한 멤버만, 입장한 뒤 메시지만, 지운 메시지는 안 보임
CREATE POLICY chat_messages_members ON chat_messages FOR SELECT TO noldaga_app
  USING (deleted_at IS NULL AND created_at >= app_room_joined_at(room_id));
CREATE POLICY notifications_own ON notifications FOR SELECT TO noldaga_app USING (user_id = app_current_user());
CREATE POLICY notifications_read_own ON notifications FOR UPDATE TO noldaga_app
  USING (user_id = app_current_user()) WITH CHECK (user_id = app_current_user());
CREATE POLICY reports_own ON reports FOR SELECT TO noldaga_app USING (reporter_id = app_current_user());
-- 관리자 채팅 열람은 앱 정책에 넣지 않음: 관리자 API가 권한·신고를 확인하고 chat_admin_access에 기록한 뒤 noldaga_service로 읽음
