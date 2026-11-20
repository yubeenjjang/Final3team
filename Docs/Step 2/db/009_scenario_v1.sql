-- 놀다가 DB 마이그레이션 009 (2026-11-20, 기능 상세 시나리오 초안 16:43 반영 — 사용자 결정)
-- 적용 순서: 001 → … → 008 → 009. 되돌리기: 009_scenario_v1_down.sql
-- 기준: 놀다가_기능_상세시나리오_초안.md S03·S05·S06·S07·S08, 11/20 사용자 결정(나이·성별 필수, 닉네임 중복 금지·정확히 일치 검색, 귀갓길 출발·도착 선택)

-- ① 회원가입 닉네임·출생연도·성별 (S03). 가입 때 API가 셋 다 필수로 받음. 탈퇴하면 NULL(A80)이라 DB 칸은 NULL 허용
ALTER TABLE profiles
  ADD COLUMN birth_year SMALLINT CHECK (birth_year BETWEEN 1900 AND 2100),
  ADD COLUMN gender     TEXT CHECK (gender IN ('male','female'));
-- 닉네임 = display_name. 2~12자, 대소문자 구분 없이 겹치지 않음(S08 정확히 일치 검색)
ALTER TABLE profiles ADD CONSTRAINT profiles_nickname_length CHECK (display_name IS NULL OR char_length(display_name) BETWEEN 2 AND 12);
CREATE UNIQUE INDEX uq_profiles_nickname ON profiles (lower(display_name)) WHERE display_name IS NOT NULL;
-- 친구 코드·닉네임 검색 허용 칸 삭제(친구 코드 없음, 닉네임은 항상 정확히 일치로 검색 — 11/20 결정)
ALTER TABLE profiles DROP COLUMN friend_code, DROP COLUMN nickname_searchable;

-- 동행 신청자 정보(닉네임·나이·성별)는 그 모집 글 작성자에게만(S03·S07). 다른 사람·친구 검색에는 나이·성별 안 보임
CREATE FUNCTION app_applicant_profile(p_application TEXT) RETURNS TABLE (display_name text, birth_year smallint, gender text)
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS
  $$ SELECT pr.display_name, pr.birth_year, pr.gender
       FROM companion_applications a
       JOIN companion_posts p ON p.post_id = a.post_id
       JOIN profiles pr ON pr.user_id = a.applicant_id
       JOIN users u ON u.user_id = a.applicant_id
      WHERE a.application_id = p_application AND p.author_id = app_current_user() AND u.status = 'active' $$;
REVOKE ALL ON FUNCTION app_applicant_profile(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_applicant_profile(TEXT) TO noldaga_app;
-- 닉네임 정확히 일치 검색(A43): 2자 이상, 대소문자 무시, 활성 계정만, 나이·성별은 돌려주지 않음
CREATE FUNCTION app_find_user_by_nickname(p_nickname TEXT) RETURNS TABLE (user_id uuid, display_name text)
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp AS
  $$ SELECT pr.user_id, pr.display_name FROM profiles pr JOIN users u ON u.user_id = pr.user_id
      WHERE char_length(p_nickname) >= 2 AND lower(pr.display_name) = lower(p_nickname) AND u.status = 'active'
        AND pr.user_id <> app_current_user() $$;
REVOKE ALL ON FUNCTION app_find_user_by_nickname(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_find_user_by_nickname(TEXT) TO noldaga_app;

-- ② 귀갓길·가는 길 출발·도착 선택 (S06). 축제 연결(festival_id)은 그대로 필수
--    귀가 기본: 출발 = 축제 장소(바꿀 수 있음), 도착 = 사용자 입력 / 가는 길 기본: 출발 = 사용자 입력, 도착 = 축제 장소(바꿀 수 있음)
--    사용자가 고른 곳은 좌표·이름을 DB에 두지 않고 HMAC 해시만(표시 이름은 Redis route:label 24시간)
ALTER TABLE route_requests
  ADD COLUMN origin_type TEXT NOT NULL DEFAULT 'festival' CHECK (origin_type IN ('festival','user')),
  ADD COLUMN destination_type TEXT NOT NULL DEFAULT 'user' CHECK (destination_type IN ('festival','user')),
  ADD COLUMN origin_place_hash TEXT,
  ADD COLUMN destination_place_hash TEXT;
UPDATE route_requests SET destination_place_hash = user_place_hash WHERE direction = 'return';
UPDATE route_requests SET origin_type = 'user', destination_type = 'festival', origin_place_hash = user_place_hash WHERE direction = 'visit';
ALTER TABLE route_requests DROP COLUMN user_place_hash;
ALTER TABLE route_requests
  ADD CONSTRAINT route_requests_endpoints_check CHECK (NOT (origin_type = 'festival' AND destination_type = 'festival')),
  ADD CONSTRAINT route_requests_origin_hash_check CHECK (origin_type = 'user' OR origin_place_hash IS NULL),
  ADD CONSTRAINT route_requests_destination_hash_check CHECK (destination_type = 'user' OR destination_place_hash IS NULL);
COMMENT ON COLUMN route_requests.origin_place_hash IS 'HMAC-SHA256(서버 비밀키, 정규화 장소). 30일 뒤 행 삭제, 사건 연결 행은 이 칸만 NULL';
COMMENT ON COLUMN route_requests.destination_place_hash IS 'HMAC-SHA256(서버 비밀키, 정규화 장소). 30일 뒤 행 삭제, 사건 연결 행은 이 칸만 NULL';

-- ③ 동행방 '채팅방 신고하기'(S07) — 신고 대상에 chat_room 추가
ALTER TABLE reports DROP CONSTRAINT reports_target_type_check;
ALTER TABLE reports ADD CONSTRAINT reports_target_type_check CHECK (target_type IN ('companion_post','chat_message','chat_room','user'));

-- ④ 챗봇 '앱 사용법' 답변(S05): 팀이 LLM으로 초안을 만들고 관리자가 승인한 문서만 RAG 검색
ALTER TABLE rag_documents DROP CONSTRAINT rag_documents_category_check;
ALTER TABLE rag_documents ADD CONSTRAINT rag_documents_category_check
  CHECK (category IN ('operation_notice','safety','transport_guide','faq','tip','app_guide'));
ALTER TABLE rag_documents
  ADD COLUMN authored_by TEXT NOT NULL DEFAULT 'source' CHECK (authored_by IN ('source','team','llm_draft')),
  ADD COLUMN app_version TEXT,
  ADD CONSTRAINT rag_documents_app_guide_check CHECK (category <> 'app_guide' OR (festival_id IS NULL AND app_version IS NOT NULL));
