-- 009 되돌리기
ALTER TABLE rag_documents DROP CONSTRAINT IF EXISTS rag_documents_app_guide_check;
ALTER TABLE rag_documents DROP COLUMN IF EXISTS authored_by, DROP COLUMN IF EXISTS app_version;
DELETE FROM rag_documents WHERE category = 'app_guide';
ALTER TABLE rag_documents DROP CONSTRAINT rag_documents_category_check;
ALTER TABLE rag_documents ADD CONSTRAINT rag_documents_category_check CHECK (category IN ('operation_notice','safety','transport_guide','faq','tip'));
DELETE FROM reports WHERE target_type = 'chat_room';
ALTER TABLE reports DROP CONSTRAINT reports_target_type_check;
ALTER TABLE reports ADD CONSTRAINT reports_target_type_check CHECK (target_type IN ('companion_post','chat_message','user'));
ALTER TABLE route_requests ADD COLUMN user_place_hash TEXT;
UPDATE route_requests SET user_place_hash = CASE WHEN direction = 'visit' THEN origin_place_hash ELSE destination_place_hash END;
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
