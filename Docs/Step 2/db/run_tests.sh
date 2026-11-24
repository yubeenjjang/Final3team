#!/usr/bin/env bash
# 놀다가 DB 시험 실행기 — 운영과 같은 이미지(pgvector/pgvector:pg17)를 새로 띄워 DDL·시험·백업 시험·실행 계획을 순서대로 실행하고 지움
# 사용법: ./run_tests.sh  (결과는 화면과 results_YYYY-MM-DD.log에 남음)
set -euo pipefail
cd "$(dirname "$0")"
IMG=pgvector/pgvector:pg17
NAME=noldaga-dbtest-$$
LOG="results_$(date +%F).log"
PSQL=(docker exec -i "$NAME" psql -U postgres -d noldaga -v ON_ERROR_STOP=1 -X)
# 마이그레이션은 파일 단위 트랜잭션으로 실행한다. psql -1은 -f 또는 -c와 함께 쓴다.
# 시험 SQL(tests_*.sql)은 파일 안에서 BEGIN/ROLLBACK을 직접 쓰므로 -1 없이 실행
PSQL_TX=(docker exec -i "$NAME" psql -U postgres -d noldaga -1 -v ON_ERROR_STOP=1 -X -f -)
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
"${PSQL_TX[@]}" -q < 001_schema_v0.3.1.sql
"${PSQL[@]}" -tAc "SELECT 'extensions: ' || string_agg(extname || ' ' || extversion, ', ') FROM pg_extension WHERE extname IN ('vector','pg_trgm')"
"${PSQL[@]}" -tAc "SELECT '001 뒤 테이블 ' || count(*) FROM pg_tables WHERE schemaname='public'"
"${PSQL[@]}" -tAc "SELECT '001 뒤 외래키 ' || count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND contype='f'"

echo "## 2. 002 마이그레이션 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 002_assistant_runs.sql
"${PSQL_TX[@]}" -q < 002_assistant_runs_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 assistant_runs 있음? ' || (to_regclass('public.assistant_runs') IS NOT NULL)"
"${PSQL_TX[@]}" -q < 002_assistant_runs.sql
echo "## 2-1. 003 마이그레이션(축제 이미지 칸) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 003_festival_images.sql
"${PSQL_TX[@]}" -q < 003_festival_images_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 thumbnail_url 있음? ' || EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='festivals' AND column_name='thumbnail_url')"
"${PSQL_TX[@]}" -q < 003_festival_images.sql
echo "## 2-2. 004 마이그레이션(핫한 축제·개인정보) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 004_trends_and_privacy.sql
"${PSQL_TX[@]}" -q < 004_trends_and_privacy_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 festival_trends 있음? ' || (to_regclass('public.festival_trends') IS NOT NULL)"
"${PSQL_TX[@]}" -q < 004_trends_and_privacy.sql
echo "## 2-3. 005 마이그레이션(추천·친구) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 005_recommend_and_friends.sql
"${PSQL_TX[@]}" -q < 005_recommend_and_friends_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 friendships 있음? ' || (to_regclass('public.friendships') IS NOT NULL)"
"${PSQL_TX[@]}" -q < 005_recommend_and_friends.sql
echo "## 2-4. 006 마이그레이션(방문 코스·공지 이력) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 006_visit_course_and_notices.sql
"${PSQL_TX[@]}" -q < 006_visit_course_and_notices_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 notice_events 있음? ' || (to_regclass('public.notice_events') IS NOT NULL)"
"${PSQL_TX[@]}" -q < 006_visit_course_and_notices.sql
echo "## 2-5. 007 마이그레이션(동행·채팅·알림·신고) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 007_companion_chat_notifications.sql
"${PSQL_TX[@]}" -q < 007_companion_chat_notifications_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 chat_messages 있음? ' || (to_regclass('public.chat_messages') IS NOT NULL)"
"${PSQL_TX[@]}" -q < 007_companion_chat_notifications.sql
"${PSQL[@]}" -tAc "SELECT '007까지 적용 뒤 테이블 ' || count(*) || ', RLS 켜진 테이블 ' || count(*) FILTER (WHERE rowsecurity) FROM pg_tables WHERE schemaname='public'"
echo "## 2-6. 008 마이그레이션(교차 검토 반영) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 008_review_fixes.sql
"${PSQL_TX[@]}" -q < 008_review_fixes_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 companion_posts.hidden_at 있음? ' || EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='companion_posts' AND column_name='hidden_at')"
"${PSQL_TX[@]}" -q < 008_review_fixes.sql
"${PSQL[@]}" -tAc "SELECT '008까지 적용 뒤 테이블 ' || count(*) || ', RLS 켜진 테이블 ' || count(*) FILTER (WHERE rowsecurity) FROM pg_tables WHERE schemaname='public'"
"${PSQL[@]}" -tAc "SELECT '008 뒤 외래키 ' || count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND contype='f'"
echo "## 2-7. 009 마이그레이션(기능 상세 시나리오) 적용 → 되돌리기 → 다시 적용"
"${PSQL_TX[@]}" -q < 009_scenario_v1.sql
"${PSQL_TX[@]}" -q < 009_scenario_v1_down.sql
"${PSQL[@]}" -tAc "SELECT '되돌린 뒤 route_requests.origin_type 있음? ' || EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='route_requests' AND column_name='origin_type')"
"${PSQL_TX[@]}" -q < 009_scenario_v1.sql
"${PSQL[@]}" -tAc "SELECT '009까지 적용 뒤 테이블 ' || count(*) || ', RLS 켜진 테이블 ' || count(*) FILTER (WHERE rowsecurity) FROM pg_tables WHERE schemaname='public'"

echo "## 3. 시험 SQL (tests_v0.3.2.sql)"
"${PSQL[@]}" < tests_v0.3.2.sql 2>&1 | sed -n 's/^.*NOTICE:  //p; /ALL SQL TESTS PASSED/p'

echo "## 4. 010 → 기존 귀가 데이터 → 011 적용·되돌리기·재적용"
# 010에는 자체 BEGIN/COMMIT이 있고, 011은 -1로 적용한다.
"${PSQL[@]}" -q -f - < 010_festival_sources_public.sql
"${PSQL_TX[@]}" -q -v seed=true -v applied=false < tests_011_route_access_token.sql
"${PSQL[@]}" -t -f - < precheck_011_route_access_token.sql
"${PSQL_TX[@]}" -q < 011_route_access_token.sql
"${PSQL[@]}" -q -v seed=false -v applied=true -f - < tests_011_route_access_token.sql
"${PSQL_TX[@]}" -q < 011_route_access_token_down.sql
"${PSQL[@]}" -q -v seed=false -v applied=false -f - < tests_011_route_access_token.sql
"${PSQL_TX[@]}" -q < 011_route_access_token.sql
"${PSQL[@]}" -q -v seed=false -v applied=true -f - < tests_011_route_access_token.sql

echo "## 5. 012·013 적용·되돌리기·재적용 및 T25 7일 백업 복원 검증"
"${PSQL[@]}" -q -v seed=true -v applied=false -v restored=false -f - < tests_012_route_backup_evidence.sql
"${PSQL_TX[@]}" -q < 012_route_backup_evidence.sql
"${PSQL[@]}" -q -v seed=false -v applied=true -v restored=false -f - < tests_012_route_backup_evidence.sql
"${PSQL_TX[@]}" -q < 012_route_backup_evidence_down.sql
"${PSQL[@]}" -q -v seed=false -v applied=false -v restored=false -f - < tests_012_route_backup_evidence.sql
"${PSQL_TX[@]}" -q < 012_route_backup_evidence.sql
"${PSQL[@]}" -q -v seed=false -v applied=true -v restored=false -f - < tests_012_route_backup_evidence.sql

"${PSQL[@]}" -q -v seed=true -v applied=false -v restored=false -f - < tests_013_route_purge_evidence.sql
"${PSQL_TX[@]}" -q < 013_route_purge_evidence.sql
"${PSQL[@]}" -q -v seed=false -v applied=true -v restored=false -f - < tests_013_route_purge_evidence.sql
"${PSQL_TX[@]}" -q < 013_route_purge_evidence_down.sql
"${PSQL[@]}" -q -v seed=false -v applied=false -v restored=false -f - < tests_013_route_purge_evidence.sql
"${PSQL_TX[@]}" -q < 013_route_purge_evidence.sql
"${PSQL[@]}" -q -v seed=false -v applied=true -v restored=false -f - < tests_013_route_purge_evidence.sql

archive=/tmp/noldaga_long_term.dump
restore_db=noldaga_backup_restore
docker exec -i "$NAME" bash -s -- -U postgres -d noldaga --file="$archive" < backup_long_term.sh
docker exec "$NAME" createdb -U postgres -T template0 "$restore_db"
docker exec "$NAME" pg_restore -U postgres -d "$restore_db" --single-transaction "$archive"
docker exec -i "$NAME" psql -U postgres -d "$restore_db" -v ON_ERROR_STOP=1 -X -q \
  -v seed=false -v applied=false -v restored=true -f - < tests_012_route_backup_evidence.sql
docker exec -i "$NAME" psql -U postgres -d "$restore_db" -v ON_ERROR_STOP=1 -X -q \
  -v seed=false -v applied=false -v restored=true -f - < tests_013_route_purge_evidence.sql
"${PSQL[@]}" < tests_v0.3.2_after_backup.sql 2>&1 | sed -n 's/^.*NOTICE:  //p; /PASSED/p'

echo "## 6. 실행 계획 (explain_v0.3.2.sql)"
"${PSQL[@]}" -q < explain_v0.3.2.sql 2>&1 | grep -E '^--- |Scan|Rows Removed|Execution Time|Planning Time|Buffers' | sed 's/^ *//'

echo "## 끝 — 시험용 컨테이너는 지움 (AWS 서버 실행 아님)"
} 2>&1 | tee "$LOG"
