-- T25(백업 시험) 뒤에 실행: TMAP 경로 정리
SET client_min_messages = notice;
SELECT t.expect_affected('T20b TMAP 경로 내용을 purged_at과 함께 지움', $q$UPDATE route_results SET candidates = NULL, evidence = '{}', purged_at = now() WHERE route_request_id = 'rr_000002'$q$, 1);
SELECT t.expect_count('T20c 정리 작업 조건: 23시간 지난 TMAP 내용 찾기 쿼리 실행 가능', $q$SELECT 1 FROM route_results WHERE provider = 'tmap' AND candidates IS NOT NULL AND created_at < now() - interval '23 hours'$q$, 0);
\echo 'AFTER-BACKUP TESTS PASSED'
