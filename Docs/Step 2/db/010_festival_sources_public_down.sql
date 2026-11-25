-- 010 되돌리기: 정책·권한만 지운다(데이터 손실 없음)
BEGIN;
DROP POLICY IF EXISTS festival_sources_public ON festival_sources;
REVOKE SELECT (festival_id, source_id, source_item_id, source_url) ON festival_sources FROM noldaga_app;
COMMIT;
