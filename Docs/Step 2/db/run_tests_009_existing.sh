#!/usr/bin/env bash
# T44~T48: 데이터가 있는 DB에서 009 적용 전 검사 → 적용 → 실패 시 전부 취소 → 되돌리기 → 다시 적용 (강사 11/20 DB 피드백 1)
# 실행: bash run_tests_009_existing.sh   (로컬 Docker 일회용 컨테이너, AWS 아님. 끝나면 컨테이너 지움)
set -u; cd "$(dirname "$0")"; N=noldaga-t009-$$; IMG=pgvector/pgvector:pg17
docker run -d --name $N -e POSTGRES_PASSWORD=test -e POSTGRES_DB=noldaga $IMG >/dev/null; trap 'docker rm -f $N >/dev/null' EXIT
for i in $(seq 1 30); do docker exec $N pg_isready -U postgres -d noldaga >/dev/null 2>&1 && break; sleep 1; done; sleep 2
P(){ docker exec -i $N psql -U postgres -v ON_ERROR_STOP=1 -tA -d "$@"; }
for f in 001_schema_v0.3.1.sql 002_assistant_runs.sql 003_festival_images.sql 004_trends_and_privacy.sql 005_recommend_and_friends.sql 006_visit_course_and_notices.sql 007_companion_chat_notifications.sql 008_review_fixes.sql; do P noldaga -q < $f >/dev/null; done
P noldaga -q < tests_009_existing_data.sql >/dev/null
docker exec $N psql -U postgres -qc "CREATE DATABASE base008 TEMPLATE noldaga" >/dev/null
mk(){ docker exec $N psql -U postgres -qc "CREATE DATABASE $1 TEMPLATE base008" >/dev/null; }
col(){ P $1 -c "select count(*) from information_schema.columns where table_name='$2' and column_name='$3'"; }
ok(){ if [ "$2" = "$3" ]; then echo "PASS $1 — $2"; else echo "FAIL $1 — 기대 $3, 실제 $2"; fi; }
echo "## 환경: 로컬 Docker $IMG 일회용 컨테이너 (AWS 아님) · $(date '+%F %T')"
mk t44; out=$(P t44 < 009_precheck.sql | tr '\n' ' '); ok "T44 사전 검사(정상 데이터): 실패 원인 0건, 손실 안내 friend_code 1·검색 허용 1" "$out" "drops_friend_code|1 drops_nickname_searchable_true|1 "
mk t45; P t45 -c "INSERT INTO users(user_id,email,password_hash) VALUES ('00000000-0000-0000-0000-0000000000a4','a4@t.t','x'); INSERT INTO profiles(user_id,display_name) VALUES ('00000000-0000-0000-0000-0000000000a4','dayoung')" >/dev/null
ok "T45a 사전 검사가 대소문자 중복 닉네임을 찾음" "$(P t45 < 009_precheck.sql | grep -c nickname_duplicate)" "1"
P t45 -1 < 009_scenario_v1.sql >/dev/null 2>&1; ok "T45b 중복 있는 DB에 -1로 적용 → 실패" "$?" "3"
ok "T45c 실패 뒤 전부 취소(birth_year 칸 없음·friend_code 칸 그대로)" "$(col t45 profiles birth_year)$(col t45 profiles friend_code)" "01"
mk t45x; P t45x -c "INSERT INTO users(user_id,email,password_hash) VALUES ('00000000-0000-0000-0000-0000000000a4','a4@t.t','x'); INSERT INTO profiles(user_id,display_name) VALUES ('00000000-0000-0000-0000-0000000000a4','dayoung')" >/dev/null; P t45x < 009_scenario_v1.sql >/dev/null 2>&1
ok "T45d (대조) -1 없이 적용하면 일부만 바뀐 상태로 남음 → -1 필수" "$(col t45x profiles birth_year)" "1"
mk t46; P t46 -1 < 009_scenario_v1.sql >/dev/null; ok "T46a 정상 데이터에 -1로 적용 성공" "$?" "0"
ok "T46b 기존 귀가·가는 길 행의 장소 해시가 새 칸으로 옮겨짐" "$(P t46 -c "select string_agg(route_request_id||':'||origin_type||'/'||destination_type||':'||coalesce(origin_place_hash,'-')||'/'||coalesce(destination_place_hash,'-'),' ' order by 1) from route_requests")" "rr_test000001:festival/user:-/hmac_home rr_test000002:user/festival:hmac_start/-"
P t46 -c "INSERT INTO reports(report_id,reporter_id,target_type,target_id,reason) VALUES ('rpt_test0001','00000000-0000-0000-0000-0000000000a1','chat_room','cr_1','spam'); INSERT INTO rag_documents(document_id,title,category,source_url,collected_at,checksum,app_version) VALUES (gen_random_uuid(),'앱 사용법','app_guide','https://x',now(),'c','1.0'); UPDATE profiles SET birth_year=1999, gender='male' WHERE display_name='오현'; INSERT INTO route_requests(route_request_id,request_id,direction,festival_id,origin_type,destination_type,origin_place_hash,destination_place_hash,travel_mode,route_key,status,is_mock) VALUES ('rr_test000003','req-3','return','fst_test0001','user','user','hmac_o','hmac_d','transit','k3','ready',true)" >/dev/null
P t46 -1 < 009_scenario_v1_down.sql >/dev/null 2>&1; ok "T47a 좌표 없는 축제의 '둘 다 사용자' 경로가 있으면 되돌리기 멈춤" "$?" "3"
ok "T47b 멈춘 뒤 전부 취소(birth_year 칸 그대로)" "$(col t46 profiles birth_year)" "1"
P t46 -c "UPDATE festivals SET latitude=37.5, longitude=126.9 WHERE festival_id='fst_test0001'" >/dev/null
P t46 -1 < 009_scenario_v1_down.sql >/dev/null; ok "T47c 축제 좌표가 있으면 채우고 되돌리기 성공" "$?" "0"
ok "T47d 손실 확인: chat_room 신고·app_guide 문서 삭제, 출생연도 칸 삭제, 경로 행 3개 유지" "$(P t46 -c "select (select count(*) from reports where target_type='chat_room')||'/'||(select count(*) from rag_documents)||'/'||(select count(*) from information_schema.columns where table_name='profiles' and column_name='birth_year')||'/'||(select count(*) from route_requests)")" "0/0/0/3"
ok "T47e '둘 다 사용자' 경로는 장소 해시 하나(도착)만 남음" "$(P t46 -c "select user_place_hash from route_requests where route_request_id='rr_test000003'")" "hmac_d"
P t46 -1 < 009_scenario_v1.sql >/dev/null; ok "T48 되돌린 뒤 다시 적용 성공" "$?" "0"
