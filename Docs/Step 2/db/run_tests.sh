#!/usr/bin/env bash
# 놀다가 DB 시험 실행기 — 운영과 같은 이미지(pgvector/pgvector:pg17)를 새로 띄워 DDL·시험·백업 시험·실행 계획을 순서대로 실행하고 지움
# 사용법: ./run_tests.sh  (결과는 화면과 results_YYYY-MM-DD.log에 남음)
set -euo pipefail
cd "$(dirname "$0")"
IMG=pgvector/pgvector:pg17
NAME=noldaga-dbtest-$$
LOG="results_$(date +%F).log"
PSQL=(docker exec -i "$NAME" psql -U postgres -d noldaga -v ON_ERROR_STOP=1 -X)
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

{
echo "# 놀다가 DB 시험 결과 — $(date '+%F %T %Z')"
docker run -d --name "$NAME" -e POSTGRES_PASSWORD=test -e POSTGRES_DB=noldaga "$IMG" >/dev/null
for i in $(seq 1 60); do docker exec "$NAME" pg_isready -U postgres -d noldaga >/dev/null 2>&1 && break; sleep 1; done
sleep 2
echo "## 환경"
"${PSQL[@]}" -tAc "SELECT version()"
echo "이미지: $IMG ($(docker image inspect "$IMG" --format '{{index .RepoDigests 0}}'))"

echo "## 1. 001 기본 DDL (001_schema_v0.3.1.sql = 04_DDL_v0.3.sql)"
"${PSQL[@]}" -q < 001_schema_v0.3.1.sql
"${PSQL[@]}" -tAc "SELECT 'extensions: ' || string_agg(extname || ' ' || extversion, ', ') FROM pg_extension WHERE extname IN ('vector','pg_trgm')"
"${PSQL[@]}" -tAc "SELECT '001 뒤 테이블 ' || count(*) FROM pg_tables WHERE schemaname='public'"
"${PSQL[@]}" -tAc "SELECT '001 뒤 외래키 ' || count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND contype='f'"

echo "## 2. 002 마이그레이션 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 002_assistant_runs.sql
"${PSQL[@]}" -q < 002_assistant_runs_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 assistant_runs 있음? ' || (to_regclass('public.assistant_runs') IS NOT NULL)"
"${PSQL[@]}" -q < 002_assistant_runs.sql
echo "## 2-1. 003 마이그레이션(축제 이미지 칸) 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 003_festival_images.sql
"${PSQL[@]}" -q < 003_festival_images_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 thumbnail_url 있음? ' || EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='festivals' AND column_name='thumbnail_url')"
"${PSQL[@]}" -q < 003_festival_images.sql
echo "## 2-2. 004 마이그레이션(핫한 축제·개인정보) 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 004_trends_and_privacy.sql
"${PSQL[@]}" -q < 004_trends_and_privacy_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 festival_trends 있음? ' || (to_regclass('public.festival_trends') IS NOT NULL)"
"${PSQL[@]}" -q < 004_trends_and_privacy.sql
echo "## 2-3. 005 마이그레이션(추천·친구) 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 005_recommend_and_friends.sql
"${PSQL[@]}" -q < 005_recommend_and_friends_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 friendships 있음? ' || (to_regclass('public.friendships') IS NOT NULL)"
"${PSQL[@]}" -q < 005_recommend_and_friends.sql
echo "## 2-4. 006 마이그레이션(방문 코스·공지 이력) 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 006_visit_course_and_notices.sql
"${PSQL[@]}" -q < 006_visit_course_and_notices_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 notice_events 있음? ' || (to_regclass('public.notice_events') IS NOT NULL)"
"${PSQL[@]}" -q < 006_visit_course_and_notices.sql
echo "## 2-5. 007 마이그레이션(동행·채팅·알림·신고) 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 007_companion_chat_notifications.sql
"${PSQL[@]}" -q < 007_companion_chat_notifications_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 chat_messages 있음? ' || (to_regclass('public.chat_messages') IS NOT NULL)"
"${PSQL[@]}" -q < 007_companion_chat_notifications.sql
"${PSQL[@]}" -tAc "SELECT '007까지 적용 뒤 테이블 ' || count(*) || ', RLS 켜진 테이블 ' || count(*) FILTER (WHERE rowsecurity) FROM pg_tables WHERE schemaname='public'"
echo "## 2-6. 008 마이그레이션(교차 검토 반영) 적용 → 되돌리기 → 다시 적용"
"${PSQL[@]}" -q < 008_review_fixes.sql
"${PSQL[@]}" -q < 008_review_fixes_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 companion_posts.hidden_at 있음? ' || EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='companion_posts' AND column_name='hidden_at')"
"${PSQL[@]}" -q < 008_review_fixes.sql
"${PSQL[@]}" -tAc "SELECT '008까지 적용 뒤 테이블 ' || count(*) || ', RLS 켜진 테이블 ' || count(*) FILTER (WHERE rowsecurity) FROM pg_tables WHERE schemaname='public'"
"${PSQL[@]}" -tAc "SELECT '008 뒤 외래키 ' || count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND contype='f'"

echo "## 3. 시험 SQL (tests_v0.3.2.sql)"
"${PSQL[@]}" < tests_v0.3.2.sql 2>&1 | sed -n 's/^.*NOTICE:  //p; /ALL SQL TESTS PASSED/p'

echo "## 4. T25 백업에 TMAP 경로 내용이 들어가지 않는지 (04 문서 7-0 ④)"
full=$(docker exec "$NAME" pg_dump -U postgres -d noldaga | grep -c TMAP_ROUTE_MARKER || true)
excl=$(docker exec "$NAME" pg_dump -U postgres -d noldaga --exclude-table-data=route_results | grep -c TMAP_ROUTE_MARKER || true)
echo "전체 백업에서 표식 ${full}건 (1 이상이어야 시험이 의미 있음) / route_results 데이터 제외 백업에서 ${excl}건"
if [ "$full" -ge 1 ] && [ "$excl" -eq 0 ]; then echo "PASS T25 — 제외 백업에 TMAP 경로 내용 없음"; else echo "FAIL T25"; exit 1; fi
"${PSQL[@]}" < tests_v0.3.2_after_backup.sql 2>&1 | sed -n 's/^.*NOTICE:  //p; /PASSED/p'

echo "## 5. 실행 계획 (explain_v0.3.2.sql)"
"${PSQL[@]}" -q < explain_v0.3.2.sql 2>&1 | grep -E '^--- |Scan|Rows Removed|Execution Time|Planning Time|Buffers' | sed 's/^ *//'

echo "## 끝 — 시험용 컨테이너는 지움 (AWS 서버 실행 아님)"
} 2>&1 | tee "$LOG"
