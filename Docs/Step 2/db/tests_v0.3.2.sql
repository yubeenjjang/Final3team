-- 놀다가 DB 시험 v0.3.2 — 다시 실행할 수 있는 시험 SQL (강사 11/19 DB 피드백 1·2)
-- 실행 순서: 001(001_schema_v0.3.1.sql) → 002 → 003 → 004 → 005 → 006 → 007 → 이 파일 (run_tests.sh가 순서대로 실행)
-- 실행: psql -v ON_ERROR_STOP=1 -f tests_v0.3.2.sql  (슈퍼유저로 접속, 시험 안에서 SET LOCAL ROLE로 역할을 바꿈)
-- 출력: 시험마다 'PASS Tn …' NOTICE. 하나라도 기대와 다르면 'FAIL'로 멈춤(종료 코드 3)
\set QUIET on
SET client_min_messages = notice;

-- ===== 시험 도우미 (시험 DB에만, 운영 DDL에는 없음) =====
CREATE SCHEMA t;
GRANT USAGE ON SCHEMA t TO noldaga_app, noldaga_service;
-- 오류가 나야 하는 SQL: 오류 메시지가 pat(정규식)에 맞아야 PASS
CREATE FUNCTION t.expect_error(name text, q text, pat text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  EXECUTE q;
  RAISE EXCEPTION 'FAIL %: 거부돼야 하는데 성공했습니다', name;
EXCEPTION WHEN OTHERS THEN
  IF SQLERRM LIKE 'FAIL %' THEN RAISE; END IF;
  IF SQLERRM !~ pat THEN RAISE EXCEPTION 'FAIL %: 예상과 다른 오류 — %', name, SQLERRM; END IF;
  RAISE NOTICE 'PASS % — 거부됨: %', name, SQLERRM;
END $$;
-- 결과 행 수가 n이어야 PASS
CREATE FUNCTION t.expect_count(name text, q text, n bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE c bigint;
BEGIN
  EXECUTE 'SELECT count(*) FROM (' || q || ') s' INTO c;
  IF c <> n THEN RAISE EXCEPTION 'FAIL %: % 행이어야 하는데 % 행', name, n, c; END IF;
  RAISE NOTICE 'PASS % — % 행', name, c;
END $$;
-- 바뀐 행 수가 n이어야 PASS (RLS로 안 보이는 행은 0행으로 바뀜)
CREATE FUNCTION t.expect_affected(name text, q text, n bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE c bigint;
BEGIN
  EXECUTE q; GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> n THEN RAISE EXCEPTION 'FAIL %: % 행이 바뀌어야 하는데 % 행', name, n, c; END IF;
  RAISE NOTICE 'PASS % — % 행 바뀜', name, c;
END $$;
-- 값이 같아야 PASS
CREATE FUNCTION t.expect_value(name text, q text, want text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE v text;
BEGIN
  EXECUTE q INTO v;
  IF v IS DISTINCT FROM want THEN RAISE EXCEPTION 'FAIL %: "%"이어야 하는데 "%"', name, want, v; END IF;
  RAISE NOTICE 'PASS % — 값 "%"', name, coalesce(v, 'NULL');
END $$;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA t TO noldaga_app, noldaga_service;

-- ===== 시험 데이터 (슈퍼유저로 넣음 = 시험 준비, RLS 영향 없음) =====
-- 사용자 A(일반), B(일반), O(운영자)
INSERT INTO users (user_id, email, password_hash) VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@test.local', 'x'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@test.local', 'x'),
  ('cccccccc-0000-0000-0000-000000000003', 'o@test.local', 'x');
INSERT INTO profiles (user_id, role, display_name) VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'user', 'A'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'user', 'B'),
  ('cccccccc-0000-0000-0000-000000000003', 'operator', 'O');
INSERT INTO data_sources (source_id, name, scope, is_realtime) VALUES ('tourapi', 'TourAPI', 'national', false);
INSERT INTO festivals (festival_id, title, region_code, latitude, longitude, published_at) VALUES
  ('fst_000001', '게시된 축제', 'SEOUL', 37.5759, 126.9768, now()),
  ('fst_000002', '비공개 축제', 'SEOUL', 37.5759, 126.9768, NULL);
INSERT INTO favorites (user_id, festival_id) VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'fst_000001'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'fst_000001');
INSERT INTO incident_logs (incident_id, failure_domain, detected_at, detection_rule, injected_test, before_metrics)
  VALUES ('inc_000001', 'internal_route', now(), 'p95_ms > 3000 for 30s', true, '{}');
INSERT INTO incident_events (incident_id, from_status, to_status, actor) VALUES ('inc_000001', NULL, 'open', 'detector');
INSERT INTO route_requests (route_request_id, request_id, festival_id, festival_lat, festival_lng, user_place_hash,
  travel_mode, route_key, status, is_mock)
  VALUES ('rr_000001', 'req-uuid-000001', 'fst_000001', 37.5759, 126.9768, 'h1', 'transit', 'k1', 'ready', true),
         ('rr_000002', 'req-uuid-000002', 'fst_000001', 37.5759, 126.9768, 'h2', 'transit', 'k2', 'ready', false),
         ('rr_000003', 'req-uuid-000003', 'fst_000001', 37.5759, 126.9768, 'h3', 'transit', 'k3', 'ready', false),
         ('rr_000004', 'req-uuid-000004', 'fst_000001', 37.5759, 126.9768, 'h4', 'transit', 'k4', 'ready', false);
-- TMAP 결과(경로 내용에 표식 문자열 TMAP_ROUTE_MARKER — 백업 시험 T25에서 찾음)
INSERT INTO route_results (route_request_id, provider, provider_tier, candidates, route_hash, source_type, queried_at, validation_status, is_mock)
  VALUES ('rr_000002', 'tmap', 'primary', '[{"summary":"TMAP_ROUTE_MARKER"}]', 'rh2', 'fresh', now(), 'verified_basic', false);

-- ===== 기본 30개 테이블 시험 (11/19 결과 재현: T1~T20) =====
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_count('T1 사용자 A가 favorites 조회 → 본인 것만', 'SELECT * FROM favorites', 1);
SELECT t.expect_error('T2 사용자 A가 B 이름으로 관심 저장', $q$INSERT INTO favorites VALUES ('bbbbbbbb-0000-0000-0000-000000000002','fst_000002')$q$, 'row-level security');
SELECT t.expect_count('T3 일반 사용자가 incident_logs 조회 → 0행', 'SELECT * FROM incident_logs', 0);
COMMIT;

BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'cccccccc-0000-0000-0000-000000000003';
SELECT t.expect_count('T4 운영자가 incident_logs 조회 → 1행', 'SELECT * FROM incident_logs', 1);
SELECT t.expect_error('T5 운영자(API 역할)가 incident_logs 직접 추가', $q$INSERT INTO incident_logs (incident_id, failure_domain, detected_at, detection_rule, injected_test, before_metrics) VALUES ('inc_000009','agent',now(),'x',true,'{}')$q$, 'permission denied');
COMMIT;

SELECT t.expect_error('T6 incident_events 수정', $q$UPDATE incident_events SET note = 'x'$q$, '추가만 할 수 있습니다');
SELECT t.expect_error('T7 사건 ID INC-003 형식', $q$INSERT INTO incident_logs (incident_id, failure_domain, detected_at, detection_rule, injected_test, before_metrics) VALUES ('INC-003','agent',now(),'x',true,'{}')$q$, 'incident_logs_incident_id_check');
SELECT t.expect_error('T8 캐시로 제공했는데 validity_check 없음', $q$INSERT INTO route_results (route_request_id, provider, provider_tier, candidates, route_hash, source_type, queried_at, validation_status, is_mock) VALUES ('rr_000001','mock_adapter','mock','[]','rh1','cache',now(),'verified_basic',true)$q$, 'route_results_check');
SELECT t.expect_error('T9 select 결정에 stop_condition 없음', $q$INSERT INTO recovery_plans (plan_id, incident_id, idempotency_key, decided_by, decision, action, reasons, evidence_refs, policy_verdict) VALUES ('rp_000009','inc_000001','ik-9','rule_policy','select','singleflight_enable','["x"]','{diag_000001}','allowed')$q$, 'recovery_plans_check2');
SELECT t.expect_count('T10 created_at 없는 테이블 → 0개',
  $q$SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind = 'r'
       AND NOT EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attname = 'created_at')$q$, 0);
SELECT t.expect_count('T11 외래키 수 → 기본 43 + 002의 2 + 004의 3 + 005의 10 + 006의 2 + 007의 19 + 008의 1 = 80',
  $q$SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = 'public' AND c.contype = 'f'$q$, 80);

BEGIN; SET LOCAL ROLE noldaga_app;
SELECT t.expect_error('T12 API 역할이 users(비밀번호 해시) 조회', 'SELECT password_hash FROM users', 'permission denied');
COMMIT;

BEGIN; SET LOCAL ROLE noldaga_service;
SELECT t.expect_affected('T13 서비스 역할이 사건 기록(RLS 우회)', $q$INSERT INTO incident_logs (incident_id, failure_domain, detected_at, detection_rule, injected_test, before_metrics) VALUES ('inc_000002','internal_route',now(),'p95',true,'{}')$q$, 1);
COMMIT;

INSERT INTO recovery_plans (plan_id, incident_id, idempotency_key, decided_by, decision, action, reasons, evidence_refs, stop_condition, policy_verdict)
  VALUES ('rp_000001', 'inc_000001', 'ik-1', 'rule_policy', 'select', 'singleflight_enable', '["dup 0.9"]', '{diag_000001}', '{"max_minutes":5}', 'allowed');
INSERT INTO recovery_attempts (attempt_id, plan_id, incident_id, action, action_enabled_at) VALUES ('ra_000001', 'rp_000001', 'inc_000001', 'singleflight_enable', now());
SELECT t.expect_affected('T14a 복구 시도 결과 채우기(pending일 때 1회)', $q$UPDATE recovery_attempts SET validation_result = 'improved', validated_at = now() WHERE attempt_id = 'ra_000001'$q$, 1);
SELECT t.expect_error('T14b 판정이 끝난 시도 다시 수정', $q$UPDATE recovery_attempts SET validation_result = 'worse' WHERE attempt_id = 'ra_000001'$q$, '판정이 끝난 시도는 바꿀 수 없습니다');
SELECT t.expect_error('T15a 사건 detection_rule 수정', $q$UPDATE incident_logs SET detection_rule = 'y' WHERE incident_id = 'inc_000001'$q$, 'status·closed_at만');
SELECT t.expect_error('T15b 사건 삭제', $q$DELETE FROM incident_logs WHERE incident_id = 'inc_000001'$q$, '삭제할 수 없습니다');

BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_error('T16 사용자가 자기 role을 admin으로', $q$UPDATE profiles SET role = 'admin'$q$, 'permission denied');
SELECT t.expect_count('T17 비공개 축제는 안 보임 → 게시된 1건만', 'SELECT * FROM festivals', 1);
COMMIT;

SELECT t.expect_error('T18a 카카오 결과에 경로 내용 저장', $q$INSERT INTO route_results (route_request_id, provider, provider_tier, candidates, route_hash, source_type, queried_at, validation_status, is_mock) VALUES ('rr_000003','kakao','secondary','[{"x":1}]','rh3','fresh',now(),'verified_basic',false)$q$, 'route_results_check');
SELECT t.expect_error('T18b 카카오 결과를 캐시 등록', $q$INSERT INTO route_cache_entries (cache_key, festival_id, route_hash, provider, valid_until) VALUES ('ck1','fst_000001','rh','kakao',now())$q$, 'route_cache_entries_provider_check');
SELECT t.expect_affected('T18c 카카오 결과를 내용 없이 출처·시각만 저장', $q$INSERT INTO route_results (route_request_id, provider, provider_tier, candidates, route_hash, source_type, queried_at, validation_status, is_mock) VALUES ('rr_000003','kakao','secondary',NULL,'rh3','fresh',now(),'verified_basic',false)$q$, 1);
SELECT t.expect_error('T19 TMAP 결과에 경로 내용 없이 저장', $q$INSERT INTO route_results (route_request_id, provider, provider_tier, candidates, route_hash, source_type, queried_at, validation_status, is_mock) VALUES ('rr_000004','tmap','primary',NULL,'rh4','fresh',now(),'verified_basic',false)$q$, 'route_results_check');
SELECT t.expect_error('T20a TMAP 경로 내용을 purged_at 없이 지움', $q$UPDATE route_results SET candidates = NULL WHERE route_request_id = 'rr_000002'$q$, 'route_results_check');

-- ===== 새 시험: DB 연결을 재사용해도 사용자 권한이 섞이지 않는지 (강사 DB 피드백 2) =====
-- 이 파일 전체가 **한 개의 DB 연결**에서 실행됩니다 = 연결 풀이 같은 연결을 다음 요청에 다시 주는 상황.
-- 규칙: API 서버는 요청마다 트랜잭션을 열고 그 안에서 SET LOCAL app.user_id(= set_config(…, true))만 씀. 커밋·롤백하면 사라짐.
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_value('T21a 요청 1(사용자 A) 안에서 사용자 ID', $q$SELECT app_current_user()::text$q$, 'aaaaaaaa-0000-0000-0000-000000000001');
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app;
SELECT t.expect_value('T21b 같은 연결의 다음 요청(사용자 정보 없음) → A가 남지 않음', $q$SELECT app_current_user()::text$q$, NULL);
SELECT t.expect_count('T21c 사용자 정보 없는 요청의 favorites → 0행', 'SELECT * FROM favorites', 0);
SELECT t.expect_count('T21d 사용자 정보 없는 요청의 profiles → 0행', 'SELECT * FROM profiles', 0);
SELECT t.expect_error('T21e 사용자 정보 없는 요청의 관심 저장 → 거부', $q$INSERT INTO favorites VALUES ('aaaaaaaa-0000-0000-0000-000000000001','fst_000002')$q$, 'row-level security');
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SELECT set_config('app.user_id', 'bbbbbbbb-0000-0000-0000-000000000002', true);
SELECT t.expect_count('T21f 같은 연결의 다음 요청(사용자 B, set_config(…, true)) → B 것만', $q$SELECT * FROM favorites WHERE user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$q$, 1);
SELECT t.expect_count('T21g 사용자 B 요청에서 A의 favorites → 0행', $q$SELECT * FROM favorites WHERE user_id = 'aaaaaaaa-0000-0000-0000-000000000001'$q$, 0);
COMMIT;
-- 오류로 롤백된 요청 뒤에도 남지 않는지
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
\set ON_ERROR_STOP 0
SELECT 1/0;   -- 요청 처리 중 오류 → 트랜잭션 실패(일부러 냄, 출력의 ERROR 한 줄은 정상)
\set ON_ERROR_STOP 1
ROLLBACK;
BEGIN; SET LOCAL ROLE noldaga_app;
SELECT t.expect_value('T21h 롤백된 요청 다음에도 사용자 ID가 남지 않음', $q$SELECT app_current_user()::text$q$, NULL);
COMMIT;
-- 금지 패턴의 근거: LOCAL 없이 SET 하면 연결에 남아 다음 요청으로 새어 나감 → 코드에서 쓰지 않음(문서 3절 규칙)
SET app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
BEGIN; SET LOCAL ROLE noldaga_app;
SELECT t.expect_count('T22 [금지 패턴 확인] LOCAL 없는 SET은 다음 요청에 남음 → A의 관심이 보임', 'SELECT * FROM favorites', 1);
COMMIT;
RESET app.user_id;
-- 다른 사람 데이터 수정·삭제
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_affected('T23a 사용자 A가 B의 표시 이름 수정 → 0행', $q$UPDATE profiles SET display_name = 'hack' WHERE user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$q$, 0);
SELECT t.expect_affected('T23b 사용자 A가 B의 관심 삭제 → 0행', $q$DELETE FROM favorites WHERE user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$q$, 0);
SELECT t.expect_affected('T23c 사용자 A가 자기 표시 이름 수정 → 1행', $q$UPDATE profiles SET display_name = 'A2' WHERE user_id = 'aaaaaaaa-0000-0000-0000-000000000001'$q$, 1);
COMMIT;
SELECT t.expect_value('T23d B의 표시 이름은 그대로', $q$SELECT display_name FROM profiles WHERE user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$q$, 'B');

-- ===== 새 시험: 챗봇 작업 assistant_runs (002) =====
INSERT INTO assistant_runs (run_id, request_id, conversation_id, user_id, message)
  VALUES ('run_000001', 'aq-uuid-000001', 'cv_000001', 'aaaaaaaa-0000-0000-0000-000000000001', '이번 주말 서울 축제 알려줘');
INSERT INTO assistant_runs (run_id, request_id, conversation_id, run_token_hash, message)
  VALUES ('run_000002', 'aq-uuid-000002', 'cv_000002', 'tokhash', '광화문에서 서울역 가는 길');
SELECT t.expect_error('T24a 같은 request_id로 작업 두 번 등록', $q$INSERT INTO assistant_runs (run_id, request_id, conversation_id, run_token_hash, message) VALUES ('run_000003','aq-uuid-000001','cv_000003','t','x')$q$, 'assistant_runs_request_id_key');
SELECT t.expect_affected('T24b 워커 1이 작업 선점(queued → running)', $q$UPDATE assistant_runs SET run_status = 'running', attempt = attempt + 1, started_at = now() WHERE run_id = 'run_000001' AND run_status IN ('queued','retrying')$q$, 1);
SELECT t.expect_affected('T24c 워커 2가 같은 작업 선점 → 0행(중복 실행 방지)', $q$UPDATE assistant_runs SET run_status = 'running', attempt = attempt + 1, started_at = now() WHERE run_id = 'run_000001' AND run_status IN ('queued','retrying')$q$, 0);
SELECT t.expect_error('T24d 답변 없이 succeeded', $q$UPDATE assistant_runs SET run_status = 'succeeded' WHERE run_id = 'run_000001'$q$, 'assistant_runs_check');
SELECT t.expect_error('T24e 오류 코드 없이 failed', $q$UPDATE assistant_runs SET run_status = 'failed' WHERE run_id = 'run_000001'$q$, 'assistant_runs_check');
UPDATE assistant_runs SET started_at = now() - interval '71 seconds' WHERE run_id = 'run_000001';
SELECT t.expect_affected('T24f 70초 넘게 running인 작업 정리 → failed', $q$UPDATE assistant_runs SET run_status = 'failed', error_code = 'AI_AGENT_FAILED', ended_at = now() WHERE run_status = 'running' AND started_at < now() - interval '70 seconds'$q$, 1);
SELECT t.expect_error('T24g 보존 정리 때 질문을 남긴 채 purged_at만 기록', $q$UPDATE assistant_runs SET purged_at = now() WHERE run_id = 'run_000002'$q$, 'assistant_runs_check');
SELECT t.expect_affected('T24h 보존 정리(질문·답변 NULL + purged_at)', $q$UPDATE assistant_runs SET message = NULL, answer = NULL, purged_at = now() WHERE run_id = 'run_000002'$q$, 1);
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_count('T24i 사용자 A는 자기 작업만 봄', 'SELECT * FROM assistant_runs', 1);
SELECT t.expect_error('T24j API 역할이 작업 상태를 직접 바꿈', $q$UPDATE assistant_runs SET run_status = 'queued'$q$, 'permission denied');
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T24k 사용자 B는 A의 작업·비로그인 작업을 못 봄', 'SELECT * FROM assistant_runs', 0);
COMMIT;

-- ===== 새 시험: 축제 대표 이미지 (003) =====
SELECT t.expect_error('T26a 이미지 주소가 있는데 저작권 유형 없음', $q$UPDATE festivals SET image_url = 'https://tong.visitkorea.or.kr/x.png' WHERE festival_id = 'fst_000001'$q$, 'festivals_image_copyright_needed');
SELECT t.expect_error('T26b 모르는 저작권 유형', $q$UPDATE festivals SET image_url = 'https://tong.visitkorea.or.kr/x.png', image_copyright_type = 'Type9' WHERE festival_id = 'fst_000001'$q$, 'festivals_image_copyright_type_check');
SELECT t.expect_affected('T26c 원본·썸네일·저작권 유형 함께 저장', $q$UPDATE festivals SET image_url = 'https://tong.visitkorea.or.kr/x_image2_1.png', thumbnail_url = 'https://tong.visitkorea.or.kr/x_image3_1.png', image_copyright_type = 'Type3' WHERE festival_id = 'fst_000001'$q$, 1);

-- ===== 새 시험: 지금 핫한 축제·개인정보 (004) =====
INSERT INTO data_sources (source_id, name, scope, is_realtime) VALUES ('trend_test', '크롤링 시험 사이트', 'national', false);
SELECT t.expect_affected('T27a 크롤링 결과 저장(연결됨)', $q$INSERT INTO festival_trends (source_id, crawled_at, raw_title, source_rank, festival_id, match_status, match_rule) VALUES ('trend_test', now(), '게시된 축제', 1, 'fst_000001', 'matched', 'name_norm+period')$q$, 1);
SELECT t.expect_affected('T27b 크롤링 결과 저장(연결 안 됨)', $q$INSERT INTO festival_trends (source_id, crawled_at, raw_title, mention_count, match_status) VALUES ('trend_test', now(), '모르는 축제', 120, 'unmatched')$q$, 1);
SELECT t.expect_error('T27c matched인데 축제 ID 없음', $q$INSERT INTO festival_trends (source_id, crawled_at, raw_title, source_rank, match_status) VALUES ('trend_test', now(), 'x', 2, 'matched')$q$, 'festival_trends_check');
SELECT t.expect_error('T27d 순위도 언급 수도 없음', $q$INSERT INTO festival_trends (source_id, crawled_at, raw_title, festival_id, match_status) VALUES ('trend_test', now(), 'y', 'fst_000001', 'matched')$q$, 'festival_trends_check');
BEGIN; SET LOCAL ROLE noldaga_app;
SELECT t.expect_count('T27e 공개 API 역할은 연결된 것만 봄', 'SELECT * FROM festival_trends', 1);
SELECT t.expect_error('T27f 공개 API 역할이 크롤링 결과 추가', $q$INSERT INTO festival_trends (source_id, crawled_at, raw_title, source_rank, match_status) VALUES ('trend_test', now(), 'z', 1, 'unmatched')$q$, 'permission denied');
COMMIT;
SELECT t.expect_count('T28a 목적지 원문 라벨 칸이 DB에 없음(Redis 24시간만)', $q$SELECT 1 FROM information_schema.columns WHERE table_name = 'route_requests' AND column_name = 'user_place_label'$q$, 0);
SELECT t.expect_affected('T28b 사건 연결 행의 장소 해시만 지우기', $q$UPDATE route_requests SET user_place_hash = NULL WHERE route_request_id = 'rr_000001'$q$, 1);

-- ===== 새 시험: 맞춤 추천 (005) =====
SELECT t.expect_error('T29a 모르는 취향 값', $q$INSERT INTO user_festival_preferences (user_id, scenarios) VALUES ('aaaaaaaa-0000-0000-0000-000000000001', '{camping}')$q$, 'user_festival_preferences_scenarios_check');
SELECT t.expect_error('T29b 아무것도 안 고르고 완료', $q$INSERT INTO user_festival_preferences (user_id, onboarding_status) VALUES ('aaaaaaaa-0000-0000-0000-000000000001', 'completed')$q$, 'user_festival_preferences_check');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_affected('T29c 본인 취향 저장', $q$INSERT INTO user_festival_preferences (user_id, scenarios, onboarding_status) VALUES ('aaaaaaaa-0000-0000-0000-000000000001', '{family_relaxed,pet}', 'completed')$q$, 1);
SELECT t.expect_error('T29d 남의 취향 저장', $q$INSERT INTO user_festival_preferences (user_id, onboarding_status) VALUES ('bbbbbbbb-0000-0000-0000-000000000002', 'skipped')$q$, 'row-level security');
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T29e 사용자 B는 A의 취향을 못 봄', 'SELECT * FROM user_festival_preferences', 0);
COMMIT;
SELECT t.expect_error('T30a 근거 없이 태그 검증 완료', $q$INSERT INTO festival_tags (festival_id, tag, status, rule_id, source_checksum, verified_by, model, prompt_version, decided_at) VALUES ('fst_000001','photo_spot','verified','kw_photo_v1','c1','llm','m','p1',now())$q$, 'festival_tags_check');
SELECT t.expect_error('T30b LLM 검증인데 모델·프롬프트 버전 없음', $q$INSERT INTO festival_tags (festival_id, tag, status, rule_id, evidence_field, evidence_quote, source_checksum, verified_by, decided_at) VALUES ('fst_000001','photo_spot','verified','kw_photo_v1','overview','야간 포토존 운영','c1','llm',now())$q$, 'festival_tags_check');
SELECT t.expect_error('T30c 반려견 가능을 예측 데이터로 검증', $q$INSERT INTO festival_tags (festival_id, tag, status, rule_id, evidence_field, evidence_quote, source_checksum, verified_by, model, prompt_version, decided_at) VALUES ('fst_000001','pet_allowed','verified','kw_pet_v1','visit_forecast','x','c1','llm','m','p1',now())$q$, 'festival_tags_check');
SELECT t.expect_affected('T30d 근거 문장과 함께 검증된 태그', $q$INSERT INTO festival_tags (festival_id, tag, status, rule_id, evidence_field, evidence_quote, source_checksum, verified_by, model, prompt_version, decided_at) VALUES ('fst_000001','photo_spot','verified','kw_photo_v1','overview','야간 포토존 운영','c1','llm','m','p1',now())$q$, 1);
SELECT t.expect_affected('T30e 근거 부족 후보(insufficient)', $q$INSERT INTO festival_tags (festival_id, tag, status, rule_id, source_checksum) VALUES ('fst_000001','relaxed','insufficient','kw_relaxed_v1','c1')$q$, 1);
BEGIN; SET LOCAL ROLE noldaga_app;
SELECT t.expect_count('T30f 공개 API 역할은 검증된 태그만 봄', 'SELECT * FROM festival_tags', 1);
SELECT t.expect_error('T30g 공개 API 역할이 태그를 직접 추가', $q$INSERT INTO festival_tags (festival_id, tag, rule_id, source_checksum) VALUES ('fst_000001','solo_friendly','x','c1')$q$, 'permission denied');
COMMIT;
SELECT t.expect_error('T31 일간 지표 음수', $q$INSERT INTO festival_engagement_daily (festival_id, day, detail_views) VALUES ('fst_000001', current_date, -1)$q$, 'festival_engagement_daily_detail_views_check');

-- ===== 새 시험: 친구 (005) =====
UPDATE profiles SET friend_code = 'AAAA1111' WHERE user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_error('T32a 친구 코드 형식', $q$UPDATE profiles SET friend_code = 'abc' WHERE user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$q$, 'profiles_friend_code_check');
SELECT t.expect_error('T32b 같은 친구 코드 두 번', $q$UPDATE profiles SET friend_code = 'AAAA1111' WHERE user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$q$, 'profiles_friend_code_key');
INSERT INTO friend_requests (request_id, from_user, to_user) VALUES ('frq_000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000002');
SELECT t.expect_error('T32c 자기 자신에게 친구 신청', $q$INSERT INTO friend_requests (request_id, from_user, to_user) VALUES ('frq_000002','aaaaaaaa-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001')$q$, 'friend_requests_check');
SELECT t.expect_error('T32d 반대 방향으로 대기 중 신청 또 만들기', $q$INSERT INTO friend_requests (request_id, from_user, to_user) VALUES ('frq_000003','bbbbbbbb-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000001')$q$, 'uq_friend_requests_pending');
SELECT t.expect_error('T32e 응답 시각 없이 수락', $q$UPDATE friend_requests SET status = 'accepted' WHERE request_id = 'frq_000001'$q$, 'friend_requests_check1');
UPDATE friend_requests SET status = 'accepted', responded_at = now() WHERE request_id = 'frq_000001';
SELECT t.expect_error('T32f 친구 관계 순서 거꾸로', $q$INSERT INTO friendships (user_a, user_b) VALUES ('bbbbbbbb-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000001')$q$, 'friendships_check');
INSERT INTO friendships (user_a, user_b, request_id) VALUES ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000002', 'frq_000001');
INSERT INTO user_blocks (blocker, blocked) VALUES ('bbbbbbbb-0000-0000-0000-000000000002', 'cccccccc-0000-0000-0000-000000000003');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_count('T33a 당사자 A는 친구 관계를 봄', 'SELECT * FROM friendships', 1);
SELECT t.expect_error('T33b 공개 API 역할이 친구 관계를 직접 만듦', $q$INSERT INTO friendships (user_a, user_b) VALUES ('aaaaaaaa-0000-0000-0000-000000000001','cccccccc-0000-0000-0000-000000000003')$q$, 'permission denied');
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'cccccccc-0000-0000-0000-000000000003';
SELECT t.expect_count('T33c 제3자(운영자 O)는 A·B 친구 관계·신청을 못 봄', 'SELECT * FROM friendships UNION ALL SELECT from_user, to_user, request_id, created_at FROM friend_requests', 0);
SELECT t.expect_count('T33d 차단당한 사람(O)은 차단 사실을 못 봄', 'SELECT * FROM user_blocks', 0);
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T33e 차단한 사람(B)은 자기 차단 목록을 봄', 'SELECT * FROM user_blocks', 1);
COMMIT;

-- ===== 새 시험: AI 방문 코스·공지 이력 (006) =====
SELECT t.expect_error('T34a 챗봇 작업에 코스 결과 저장', $q$UPDATE assistant_runs SET result = '{"stops":[]}' WHERE run_id = 'run_000001'$q$, 'assistant_runs_result_kind');
SELECT t.expect_affected('T34b 방문 코스 작업 등록', $q$INSERT INTO assistant_runs (run_id, request_id, conversation_id, user_id, run_kind, message) VALUES ('run_000010','vc-uuid-000010','cv_000010','aaaaaaaa-0000-0000-0000-000000000001','visit_course','가족 2시간 코스')$q$, 1);
SELECT t.expect_affected('T34c 방문 코스 결과 저장(장소 ID·검증 여부)', $q$UPDATE assistant_runs SET result = '{"stops":[{"order":1,"type":"festival","ref_id":"fst_000001","verified":true}]}', run_status = 'succeeded', answer = '코스를 만들었어요' WHERE run_id = 'run_000010'$q$, 1);
SELECT t.expect_error('T34d 보존 정리 때 결과를 남김', $q$UPDATE assistant_runs SET message = NULL, answer = NULL, purged_at = now() WHERE run_id = 'run_000010'$q$, 'assistant_runs_result_purge');
INSERT INTO data_sources (source_id, name, scope, is_realtime) VALUES ('admin_manual', '운영자 등록', 'national', false);
INSERT INTO official_notices (notice_id, festival_id, type, title, source_id) VALUES ('ntc_000001', 'fst_000001', 'traffic_control', '세종대로 통제', 'admin_manual');
SELECT t.expect_affected('T35a 관리자 공지 등록 이력', $q$INSERT INTO notice_events (notice_id, action, actor, after_value) VALUES ('ntc_000001','create','cccccccc-0000-0000-0000-000000000003','{"title":"세종대로 통제"}')$q$, 1);
SELECT t.expect_error('T35b 이유 없이 반려', $q$INSERT INTO notice_events (notice_id, action, actor) VALUES ('ntc_000001','reject','cccccccc-0000-0000-0000-000000000003')$q$, 'notice_events_check');
SELECT t.expect_error('T35c 공지 이력 수정', $q$UPDATE notice_events SET reason = 'x'$q$, '추가만 할 수 있습니다');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'cccccccc-0000-0000-0000-000000000003';
SELECT t.expect_error('T35d API 역할이 공지 이력을 직접 기록', $q$INSERT INTO notice_events (notice_id, action, actor) VALUES ('ntc_000001','approve','cccccccc-0000-0000-0000-000000000003')$q$, 'permission denied');
SELECT t.expect_count('T35e 미승인 공지는 공개 조회에 안 보임', 'SELECT * FROM official_notices', 0);
COMMIT;

-- ===== 새 시험: 동행·채팅·알림·신고 (007) =====
-- 준비: A가 동행 글(정원 1)을 올림 → 작성자만 있는 동행방
INSERT INTO chat_rooms (room_id, room_type, name, owner_id) VALUES ('crm_000001', 'companion', '동행방', 'aaaaaaaa-0000-0000-0000-000000000001');
INSERT INTO chat_members (room_id, user_id, role, status, joined_at) VALUES ('crm_000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'owner', 'joined', now() - interval '1 hour');
INSERT INTO companion_posts (post_id, festival_id, author_id, room_id, meet_at, capacity) VALUES ('cpo_000001', 'fst_000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'crm_000001', now() + interval '1 day', 1);
INSERT INTO meeting_places (post_id, name, updated_by) VALUES ('cpo_000001', '광화문 해치마당', 'aaaaaaaa-0000-0000-0000-000000000001');
INSERT INTO chat_messages (room_id, seq, sender_id, msg_type, body, client_message_id, created_at) VALUES ('crm_000001', 1, 'aaaaaaaa-0000-0000-0000-000000000001', 'text', '승인 전 메시지', 'cm-a-0001', now() - interval '30 minutes');
INSERT INTO companion_applications (application_id, post_id, applicant_id, message) VALUES ('cap_000001', 'cpo_000001', 'bbbbbbbb-0000-0000-0000-000000000002', '같이 가요');
SELECT t.expect_error('T36a 같은 글에 또 신청(대기 중)', $q$INSERT INTO companion_applications (application_id, post_id, applicant_id) VALUES ('cap_000002','cpo_000001','bbbbbbbb-0000-0000-0000-000000000002')$q$, 'uq_companion_applications_active');
SELECT t.expect_error('T36b 결정 시각 없이 승인', $q$UPDATE companion_applications SET status = 'approved' WHERE application_id = 'cap_000001'$q$, 'companion_applications_check');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T37a 승인 전 신청자는 정확한 만남 장소를 못 봄', 'SELECT * FROM meeting_places', 0);
SELECT t.expect_count('T37b 승인 전 신청자는 동행방 메시지를 못 봄', 'SELECT * FROM chat_messages', 0);
SELECT t.expect_count('T37c 신청자는 자기 신청을 봄', 'SELECT * FROM companion_applications', 1);
SELECT t.expect_count('T37d 모집 글 공개 정보는 누구나 봄', 'SELECT * FROM companion_posts', 1);
SELECT t.expect_error('T37e 앱 역할이 신청을 직접 승인', $q$UPDATE companion_applications SET status = 'approved', decided_at = now()$q$, 'permission denied');
COMMIT;
-- 승인(서버 코드가 한 트랜잭션: 신청 승인 + 정원 +1 + 방 멤버 입장 + 시스템 메시지)
UPDATE companion_applications SET status = 'approved', decided_at = now() WHERE application_id = 'cap_000001';
UPDATE companion_posts SET approved_count = approved_count + 1, status = 'full' WHERE post_id = 'cpo_000001';
INSERT INTO chat_members (room_id, user_id, status, joined_at) VALUES ('crm_000001', 'bbbbbbbb-0000-0000-0000-000000000002', 'joined', now());
INSERT INTO chat_messages (room_id, seq, msg_type, body) VALUES ('crm_000001', 2, 'system', 'B님이 들어왔어요');
SELECT t.expect_error('T36c 정원 초과 승인(동시 승인 재현)', $q$UPDATE companion_posts SET approved_count = approved_count + 1 WHERE post_id = 'cpo_000001'$q$, 'companion_posts_check');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T37f 승인된 참여자는 만남 장소를 봄', 'SELECT * FROM meeting_places', 1);
SELECT t.expect_count('T37g 입장한 뒤 메시지만 보임(입장 전 메시지 1개 제외)', 'SELECT * FROM chat_messages', 1);
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'cccccccc-0000-0000-0000-000000000003';
SELECT t.expect_count('T37h 멤버가 아니면 방·멤버·메시지·장소 0행', 'SELECT room_id FROM chat_rooms UNION ALL SELECT room_id FROM chat_members UNION ALL SELECT room_id FROM chat_messages UNION ALL SELECT post_id FROM meeting_places', 0);
COMMIT;
SELECT t.expect_error('T38a 같은 방에 같은 순서 번호', $q$INSERT INTO chat_messages (room_id, seq, sender_id, msg_type, body, client_message_id) VALUES ('crm_000001', 2, 'bbbbbbbb-0000-0000-0000-000000000002', 'text', 'x', 'cm-b-0001')$q$, 'chat_messages_room_id_seq_key');
INSERT INTO chat_messages (room_id, seq, sender_id, msg_type, body, client_message_id) VALUES ('crm_000001', 3, 'bbbbbbbb-0000-0000-0000-000000000002', 'text', '안녕하세요', 'cm-b-0002');
SELECT t.expect_error('T38b 같은 client_message_id 재전송(중복 저장 방지)', $q$INSERT INTO chat_messages (room_id, seq, sender_id, msg_type, body, client_message_id) VALUES ('crm_000001', 4, 'bbbbbbbb-0000-0000-0000-000000000002', 'text', '안녕하세요', 'cm-b-0002')$q$, 'chat_messages_room_id_sender_id_client_message_id_key');
SELECT t.expect_error('T38c 보낸 사람 없는 일반 메시지', $q$INSERT INTO chat_messages (room_id, seq, msg_type, body) VALUES ('crm_000001', 5, 'text', 'x')$q$, 'chat_messages_check');
INSERT INTO chat_rooms (room_id, room_type, direct_key) VALUES ('crm_000002', 'direct', 'aaaaaaaa-0000-0000-0000-000000000001'||'|'||'bbbbbbbb-0000-0000-0000-000000000002');
SELECT t.expect_error('T38d 같은 두 사람의 1:1 방 중복', $q$INSERT INTO chat_rooms (room_id, room_type, direct_key) VALUES ('crm_000003','direct','aaaaaaaa-0000-0000-0000-000000000001|bbbbbbbb-0000-0000-0000-000000000002')$q$, 'chat_rooms_direct_key_key');
SELECT t.expect_error('T38e 이름 없는 친구 단체방', $q$INSERT INTO chat_rooms (room_id, room_type, owner_id) VALUES ('crm_000004','friend_group','aaaaaaaa-0000-0000-0000-000000000001')$q$, 'chat_rooms_check1');
INSERT INTO chat_rooms (room_id, room_type, name, owner_id) VALUES ('crm_000005', 'friend_group', '축제 친구들', 'aaaaaaaa-0000-0000-0000-000000000001');
INSERT INTO chat_members (room_id, user_id, role, status, joined_at) VALUES ('crm_000005', 'aaaaaaaa-0000-0000-0000-000000000001', 'owner', 'joined', now());
INSERT INTO chat_members (room_id, user_id, status, invited_by, invited_at) VALUES ('crm_000005', 'cccccccc-0000-0000-0000-000000000003', 'invited', 'aaaaaaaa-0000-0000-0000-000000000001', now());
INSERT INTO chat_messages (room_id, seq, sender_id, msg_type, body, client_message_id) VALUES ('crm_000005', 1, 'aaaaaaaa-0000-0000-0000-000000000001', 'text', '초대 전 메시지', 'cm-a-0101');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'cccccccc-0000-0000-0000-000000000003';
SELECT t.expect_count('T38f 초대만 받은 사람은 방은 보이지만 메시지는 0행(수락 전 접근 차단)', 'SELECT 1 FROM chat_rooms UNION ALL SELECT 1 FROM chat_messages', 1);
COMMIT;
INSERT INTO notifications (user_id, type, ref_type, ref_id) VALUES ('bbbbbbbb-0000-0000-0000-000000000002', 'companion_approved', 'companion_application', 'cap_000001');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_affected('T39a 본인 알림 읽음 처리', $q$UPDATE notifications SET read_at = now()$q$, 1);
SELECT t.expect_error('T39b 알림 종류를 바꿈(읽음 칸만 허용)', $q$UPDATE notifications SET type = 'friend_accepted'$q$, 'permission denied');
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_count('T39c 남의 알림은 안 보임', 'SELECT * FROM notifications', 0);
COMMIT;
INSERT INTO reports (report_id, reporter_id, target_type, target_id, reason) VALUES ('rpt_000001', 'bbbbbbbb-0000-0000-0000-000000000002', 'chat_message', '3', 'abuse');
SELECT t.expect_error('T40a 처리자 없이 신고 처리 완료', $q$UPDATE reports SET status = 'actioned' WHERE report_id = 'rpt_000001'$q$, 'reports_check');
SELECT t.expect_affected('T40b 관리자 채팅 열람 기록', $q$INSERT INTO chat_admin_access (admin_id, room_id, report_id, reason) VALUES ('cccccccc-0000-0000-0000-000000000003', 'crm_000001', 'rpt_000001', '신고 처리')$q$, 1);
SELECT t.expect_error('T40c 관리자 열람 기록 지우기', $q$DELETE FROM chat_admin_access$q$, '추가만 할 수 있습니다');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T40d 신고자는 자기 신고만 봄', 'SELECT * FROM reports', 1);
COMMIT;
-- 보존: 동행 종료 뒤 3일 지난 메시지 정리(내용만 지우고 순서 번호는 남김)
UPDATE chat_rooms SET status = 'read_only', read_only_at = now() - interval '4 days' WHERE room_id = 'crm_000001';
SELECT t.expect_affected('T41a 종료 3일 지난 동행방 메시지 정리', $q$UPDATE chat_messages m SET body = NULL, deleted_at = now() FROM chat_rooms r WHERE r.room_id = m.room_id AND r.room_type = 'companion' AND r.read_only_at < now() - interval '3 days' AND m.deleted_at IS NULL$q$, 3);
SELECT t.expect_error('T41b 지우지 않았는데 내용 비움', $q$UPDATE chat_messages SET body = NULL WHERE room_id = 'crm_000005'$q$, 'chat_messages_check1');
SELECT t.expect_error('T41c 종료 시각 없이 읽기 전용', $q$UPDATE chat_rooms SET status = 'read_only', read_only_at = NULL WHERE room_id = 'crm_000005'$q$, 'chat_rooms_check2');

-- ===== 008 교차 검토 반영 (T42) =====
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_affected('T42a 본인 닉네임 검색 허용 바꾸기(A78)', $q$UPDATE profiles SET nickname_searchable = true$q$, 1);
COMMIT;
UPDATE festivals SET review_status = 'hidden' WHERE festival_id = 'fst_000001';
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_count('T42b 게시 뒤 숨긴 축제는 공개 목록에서 빠짐', 'SELECT * FROM festivals', 0);
COMMIT;
UPDATE festivals SET review_status = 'pending' WHERE festival_id = 'fst_000001';
SELECT t.expect_count('T42c 채팅 권한 함수 검색 경로에 pg_temp가 맨 뒤', $q$SELECT 1 FROM pg_proc WHERE proname IN ('app_room_joined_at','app_room_visible','app_public_display_name') AND array_to_string(proconfig, ',') LIKE '%public, pg_temp'$q$, 3);
SELECT t.expect_error('T42d 숨김 처리자 없이 동행 글 숨김', $q$UPDATE companion_posts SET hidden_at = now() WHERE post_id = 'cpo_000001'$q$, 'companion_posts_check');
UPDATE companion_posts SET hidden_at = now(), hidden_by = 'cccccccc-0000-0000-0000-000000000003' WHERE post_id = 'cpo_000001';
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T42e 숨긴 동행 글은 다른 사람에게 안 보임(A77)', $q$SELECT 1 FROM companion_posts WHERE post_id = 'cpo_000001'$q$, 0);
COMMIT;
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_count('T42f 숨긴 동행 글도 작성자 본인은 봄', $q$SELECT 1 FROM companion_posts WHERE post_id = 'cpo_000001'$q$, 1);
COMMIT;
UPDATE companion_posts SET hidden_at = NULL, hidden_by = NULL WHERE post_id = 'cpo_000001';
SELECT t.expect_affected('T42g improved 판정 뒤 조치 끈 시각·이유 기록(1회)', $q$UPDATE recovery_attempts SET action_disabled_at = now(), rollback_reason = 'max_minutes' WHERE attempt_id = 'ra_000001'$q$, 1);
SELECT t.expect_error('T42h 끈 시각 다시 바꾸기', $q$UPDATE recovery_attempts SET action_disabled_at = now() WHERE attempt_id = 'ra_000001'$q$, '판정이 끝난 시도는 바꿀 수 없습니다');
SELECT t.expect_error('T42i 실패한 부하 시험인데 실패 원인 없음', $q$INSERT INTO load_simulations (simulation_id, idempotency_key, comparison_arm, scenario, concurrency, duration_s, unique_route_keys, cache_state, code_version, limits_version, status) VALUES ('sim_000099', 'sim-key-000099', 'B0', 'mixed', 10, 30, 5, 'cold', 'v0', 'lim-0.1', 'failed')$q$, 'load_simulations_check');
BEGIN; SET LOCAL ROLE noldaga_app; SET LOCAL app.user_id = 'bbbbbbbb-0000-0000-0000-000000000002';
SELECT t.expect_count('T42j 남의 프로필 행은 직접 안 보임', $q$SELECT 1 FROM profiles WHERE user_id = 'aaaaaaaa-0000-0000-0000-000000000001'$q$, 0);
SELECT t.expect_value('T42k 남의 표시 이름은 공개 함수로만 봄', $q$SELECT app_public_display_name('aaaaaaaa-0000-0000-0000-000000000001')$q$, 'A2');
COMMIT;
BEGIN;
UPDATE users SET email = 'deleted+' || user_id || '@invalid', password_hash = '!', status = 'deleted' WHERE user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
UPDATE profiles SET display_name = NULL, friend_code = NULL, nickname_searchable = false WHERE user_id = 'aaaaaaaa-0000-0000-0000-000000000001';
SELECT t.expect_value('T42l 탈퇴(이메일·해시 덮어쓰기) 뒤 표시 이름은 NULL(A80)', $q$SELECT app_public_display_name('aaaaaaaa-0000-0000-0000-000000000001')$q$, NULL);
ROLLBACK;

-- ===== TMAP 24시간 정리 (T20b) — 백업 시험(T25)이 표식을 찾을 수 있게 맨 끝에 둠 =====
-- (run_tests.sh가 T25를 먼저 돌린 뒤 이 정리를 확인함)
\echo 'ALL SQL TESTS PASSED'
