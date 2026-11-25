-- 009 적용 전 검사 (2026-11-23, 강사 11/20 DB 피드백 1). ①·② 검사 결과가 0행이 아니면 009를 적용하지 말고 먼저 데이터를 고친다. ③ 손실 안내는 참고용이다.
-- 실행: psql -v ON_ERROR_STOP=1 -f 009_precheck.sql   (읽기만 함, 데이터 변경 없음)
-- ① 닉네임 길이 2~12자 위반(009 CHECK profiles_nickname_length에서 실패)
SELECT 'nickname_length' AS check, user_id::text AS ref, display_name FROM profiles
 WHERE display_name IS NOT NULL AND char_length(display_name) NOT BETWEEN 2 AND 12
UNION ALL
-- ② 대소문자 무시 닉네임 중복(009 UNIQUE uq_profiles_nickname에서 실패)
SELECT 'nickname_duplicate', string_agg(user_id::text, ','), lower(display_name) FROM profiles
 WHERE display_name IS NOT NULL GROUP BY lower(display_name) HAVING count(*) > 1;
-- ③ 손실 안내(실패는 아님): 009가 지우는 칸에 값이 있는 행 수 — friend_code·nickname_searchable은 009에서 삭제(복구 불가)
SELECT 'drops_friend_code' AS loss, count(*) FROM profiles WHERE friend_code IS NOT NULL
UNION ALL SELECT 'drops_nickname_searchable_true', count(*) FROM profiles WHERE nickname_searchable;
