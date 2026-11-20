-- 놀다가 DB 마이그레이션 008 (2026-11-20, API·DB v0.3.3 제출 전 교차 검토 반영)
-- 적용 순서: 001 → … → 007 → 008. 되돌리기: 008_review_fixes_down.sql
-- 기준: 검토결과/종합.md 나-1~7 (Claude·Codex·agy 교차 검토)

-- 나-1. 프로필 '닉네임 검색 허용'을 본인이 바꿀 수 있게(A78). 001은 display_name만 허용했음
GRANT UPDATE (nickname_searchable) ON profiles TO noldaga_app;

-- 나-2. 숨긴 축제(review_status='hidden')는 게시 시각이 있어도 공개 목록에서 빠짐(A24·A56).
--       최초 공개 시각(published_at)은 지우지 않고 그대로 둠(A41 최신순 기준 유지)
DROP POLICY festivals_public ON festivals;
CREATE POLICY festivals_public ON festivals FOR SELECT TO noldaga_app
  USING (published_at IS NOT NULL AND review_status <> 'hidden');

-- 나-3. SECURITY DEFINER 함수의 검색 경로 고정: 임시 스키마(pg_temp)를 맨 뒤로 → 같은 이름의 임시 테이블로 끼어들 수 없음
ALTER FUNCTION app_room_joined_at(TEXT) SET search_path = pg_catalog, public, pg_temp;
ALTER FUNCTION app_room_visible(TEXT)   SET search_path = pg_catalog, public, pg_temp;

-- 나-4. 신고 처리로 동행 글 숨김(A77 hide_post). 숨긴 글은 작성자 본인만 보임
ALTER TABLE companion_posts
  ADD COLUMN hidden_at TIMESTAMPTZ,
  ADD COLUMN hidden_by UUID REFERENCES profiles(user_id),
  ADD CHECK (hidden_at IS NULL OR hidden_by IS NOT NULL);
DROP POLICY companion_posts_public ON companion_posts;
CREATE POLICY companion_posts_public ON companion_posts FOR SELECT TO noldaga_app
  USING (hidden_at IS NULL OR author_id = app_current_user());

-- 나-5. 복구 시도: 'improved' 판정 뒤에도 조치를 끈 시각·이유는 한 번 기록할 수 있게(최대 시간 만료·시뮬레이션 중단, A21)
--       판정·재측정 값은 여전히 바꿀 수 없음
CREATE OR REPLACE FUNCTION recovery_attempt_complete_once() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.attempt_id, NEW.plan_id, NEW.incident_id, NEW.action, NEW.action_enabled_at, NEW.created_at)
     IS DISTINCT FROM (OLD.attempt_id, OLD.plan_id, OLD.incident_id, OLD.action, OLD.action_enabled_at, OLD.created_at) THEN
    RAISE EXCEPTION 'recovery_attempts: 결과 칸만 채울 수 있습니다';
  END IF;
  IF OLD.validation_result = 'pending' THEN
    RETURN NEW;
  END IF;
  IF OLD.validation_result = 'improved' AND OLD.action_disabled_at IS NULL AND NEW.action_disabled_at IS NOT NULL
     AND (NEW.validation_result, NEW.after_metrics, NEW.stop_reason, NEW.validated_at)
         IS NOT DISTINCT FROM (OLD.validation_result, OLD.after_metrics, OLD.stop_reason, OLD.validated_at) THEN
    RETURN NEW;   -- 유지하던 조치를 나중에 끔: action_disabled_at·rollback_reason만 1회
  END IF;
  RAISE EXCEPTION 'recovery_attempts: 판정이 끝난 시도는 바꿀 수 없습니다';
END $$;

-- 나-6. 부하 시험: 시작 때 적용한 제한값 버전, 중단 요청 시각, 실패 원인(A20·A21·A31)
ALTER TABLE load_simulations
  ADD COLUMN limits_version    TEXT,
  ADD COLUMN stop_requested_at TIMESTAMPTZ,
  ADD COLUMN error             JSONB,
  ADD CHECK (status <> 'failed' OR error IS NOT NULL);

-- 나-7. 다른 사람의 표시 이름만 공개(동행 글·신청·채팅 A57·A61·A71). profiles RLS는 본인 행만이라 조인하면 이름이 안 보임
--       탈퇴·정지 계정은 NULL → 화면은 "알 수 없음"
CREATE FUNCTION app_public_display_name(p_user UUID) RETURNS text
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS
  $$ SELECT p.display_name FROM profiles p JOIN users u ON u.user_id = p.user_id WHERE p.user_id = p_user AND u.status = 'active' $$;
REVOKE ALL ON FUNCTION app_public_display_name(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_public_display_name(UUID) TO noldaga_app;
