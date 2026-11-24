# STEP6 TMAP 결과 정리 운영 절차

권오현이 정리 명령을 제공한다. 신유빈이 W64·W65에서 시간당 실행, 로그 수집, 실패 감시를 구성한다. API 컨테이너와 같은 `.env.example`의 DB 설정으로 013까지 적용한 DB에 연결한다. `DB_MIGRATION_DSN`은 관리자 실행 환경에만 둔다.

먼저 `--dry-run`으로 정리 대상을 확인한다. 성공 시 표준 출력에 대상 행 수만 출력한다. 시간당 정리 작업에는 인자 없이 실행하는 명령을 지정한다.

| 실행 위치 | 대상 건수 확인 | 정리 실행 |
|---|---|---|
| `backend/` | `python -m api.jobs.purge_route_results --dry-run` | `python -m api.jobs.purge_route_results` |
| 저장소 루트 | `PYTHONPATH=backend python -m api.jobs.purge_route_results --dry-run` | `PYTHONPATH=backend python -m api.jobs.purge_route_results` |

정리 명령은 `service_db_session()`의 트랜잭션에서 advisory lock을 잡는다. `queried_at` 기준으로 기본 23시간 이상 된 미정리 TMAP 행 본문을 비우고 `route_results.purged_at`을 기록한다. 013 트리거는 같은 트랜잭션에서 `route_requests.result_purged_at`에 같은 시각을 기록한다. 행과 메타데이터는 보존하며, 재실행 시 이미 정리한 행은 건너뛴다. 시간당 실행이 정상적으로 이어지면 23시간에 정리 대상이 된 본문은 다음 회차까지 최대 24시간 보관된다. `ROUTE_PURGE_AFTER_HOURS`는 기본값 23이며 1~23 사이의 정수만 허용한다. 유효 토큰으로 정리된 결과를 A05에서 조회하면 `ROUTE_RESULT_EXPIRED`(`retryable=false`)를 반환한다.

| 종료 코드 | 상태와 대응 |
|---|---|
| `0` | 정상 완료. 정리 실행은 `status=ok`, `processed`, `duration_ms`를 한 줄에 남긴다. 0건도 정상이다. |
| `1` | 실행 실패. 경보를 보내고 DB 연결·권한·013까지의 적용 상태를 점검한다. |
| `2` | 인자 또는 정리 기준 설정 오류. 경보를 보내고 등록된 명령, 인자, `ROUTE_PURGE_AFTER_HOURS`를 확인한다. |
| `3` | 잠금 사용 중. 경보를 보내고 중복 예약이나 앞선 실행의 지연을 확인한다. |

정기 작업에서 65분 동안 `status=ok`가 없으면 누락 경보를 보낸다. 실행 실패·잠금 로그에는 상태, 처리 건수 필드, 소요 시간만 남긴다.

저장소 루트에서 `uv run --offline --with-requirements backend/api/requirements.txt python -m pytest backend/tests -q`로 시험한다. 001~013을 적용한 일회용 PostgreSQL의 `TEST_DB_URL`을 설정하면 `db` 표시 시험에서 23시간 경계, 정리 직후 유효 토큰의 A05 만료 응답, 삭제 시각 일치, 카카오 제외, 건수 조회, 재실행, 별도 연결의 잠금 충돌을 검증한다. DB 없이 실행하는 시험도 23시간 경계의 대상 건수, 범위 밖 설정 거부, 정리된 결과의 A05 만료 응답을 확인한다.

11/27 제출 기준 커밋: 신유빈 고정 예정(`main` 병합 후)
