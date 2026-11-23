-- 009 되돌리기 — 반드시 파일 단위 트랜잭션으로 실행: psql -1 -v ON_ERROR_STOP=1 -f 009_scenario_v1_down.sql
-- 손실(복구 불가): app_guide 문서·chat_room 신고 삭제, 출생연도·성별 칸 삭제, 출발·도착 둘 다 사용자인 경로는 장소 해시 한 개만 남음
ALTER TABLE rag_documents DROP CONSTRAINT IF EXISTS rag_documents_app_guide_check;
ALTER TABLE rag_documents DROP COLUMN IF EXISTS authored_by, DROP COLUMN IF EXISTS app_version;
DELETE FROM rag_documents WHERE category = 'app_guide';
ALTER TABLE rag_documents DROP CONSTRAINT rag_documents_category_check;
ALTER TABLE rag_documents ADD CONSTRAINT rag_documents_category_check CHECK (category IN ('operation_notice','safety','transport_guide','faq','tip'));
DELETE FROM reports WHERE target_type = 'chat_room';
ALTER TABLE reports DROP CONSTRAINT reports_target_type_check;
ALTER TABLE reports ADD CONSTRAINT reports_target_type_check CHECK (target_type IN ('companion_post','chat_message','user'));
ALTER TABLE route_requests ADD COLUMN user_place_hash TEXT;
-- 출발·도착이 둘 다 사용자 장소인 행은 한 칸으로 되돌릴 수 없어 사용자 쪽 대표 칸(귀가=도착, 가는 길=출발)만 남김
UPDATE route_requests SET user_place_hash = COALESCE(CASE WHEN direction = 'visit' THEN origin_place_hash ELSE destination_place_hash END, origin_place_hash, destination_place_hash);
ALTER TABLE route_requests DROP CONSTRAINT IF EXISTS route_requests_festival_point_check;
-- (11/23 보완, T47) 009 뒤 생긴 '출발·도착 둘 다 사용자 장소' 행은 축제 좌표가 비어 있어 NOT NULL로 못 되돌림.
-- 축제 좌표로 채우고, 그래도 비면(좌표 없는 축제) 멈춘다 — 몰래 지우지 않음. 그런 행은 30일 보존 규칙으로 사라진 뒤 되돌리거나 직접 처리.
UPDATE route_requests r SET festival_lat = f.latitude, festival_lng = f.longitude
  FROM festivals f WHERE f.festival_id = r.festival_id AND (r.festival_lat IS NULL OR r.festival_lng IS NULL);
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM route_requests WHERE festival_lat IS NULL OR festival_lng IS NULL) THEN
    RAISE EXCEPTION '009 되돌리기 중지: 축제 좌표가 없는 귀가 요청 %건 — 먼저 처리하세요', (SELECT count(*) FROM route_requests WHERE festival_lat IS NULL OR festival_lng IS NULL);
  END IF;
END $$;
ALTER TABLE route_requests ALTER COLUMN festival_lat SET NOT NULL, ALTER COLUMN festival_lng SET NOT NULL;
ALTER TABLE route_requests DROP CONSTRAINT IF EXISTS route_requests_endpoints_check,
  DROP CONSTRAINT IF EXISTS route_requests_origin_hash_check, DROP CONSTRAINT IF EXISTS route_requests_destination_hash_check;
ALTER TABLE route_requests DROP COLUMN origin_type, DROP COLUMN destination_type, DROP COLUMN origin_place_hash, DROP COLUMN destination_place_hash;
DROP FUNCTION IF EXISTS app_find_user_by_nickname(TEXT), app_applicant_profile(TEXT);
ALTER TABLE profiles ADD COLUMN friend_code TEXT UNIQUE CHECK (friend_code ~ '^[A-Z0-9]{8}$'),
  ADD COLUMN nickname_searchable BOOLEAN NOT NULL DEFAULT false;
GRANT UPDATE (nickname_searchable) ON profiles TO noldaga_app;
DROP INDEX IF EXISTS uq_profiles_nickname;
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_nickname_length;
ALTER TABLE profiles DROP COLUMN birth_year, DROP COLUMN gender;
