# STEP7 귀가 경로 후속

P23은 방향, 축제, 해석된 출발·도착, 이동 제약과 출발 기준, 통제 버전, 공급원을 정규화한 JSON에 HMAC을 적용합니다. TMAP 캐시·병합은 `v2:` 키로 조회하고 카카오 전환은 요청별 동기 응답으로 처리합니다. 기존 요청의 A05와 멱등 재전송은 기존 식별자와 해시로 확인합니다.

P24는 SQLAlchemy 연결 풀 대기 초과에 503 `SERVICE_BUSY`, `retryable=true`, `Retry-After: 1`을 반환합니다. DB-14의 30초 풀 대기는 시험에서 예외 주입으로 재현합니다.

P25는 SK 회신 없이 적용하는 확정 기준 2-2입니다. TMAP 후보·근거와 후보 해시를 함께 비웁니다. 이미 정리된 행의 잔여 값을 비울 때 최초 삭제 시각을 보존합니다. 요청 행과 기존 로그·지표는 자체 측정 시각·상태·공급원을 사용합니다.

| 검증 | 시험 |
|---|---|
| 같은 조건에서 같은 키, 조건·시각·통제·공급원이 다르면 다른 키, 원문 좌표 부재, 멱등 본문 충돌 | `test_p9_real_routes.py` P10·P23 |
| A04·A05 풀 초과 응답, 추적 ID와 재시도 헤더 | `test_p16_route_store.py` P24 |
| 기준 시각, 기존 삭제 시각 보존, 파생 값 제거, 카카오 제외, 재실행 | `test_purge_route_results.py` P25 및 `test_p18_route_store_db.py` |

저장소 루트에서 `uv run --offline --with-requirements backend/api/requirements.txt python -m pytest backend/tests -q`를 실행합니다. PostgreSQL 시험은 013까지 적용한 일회용 DB 설정이 필요합니다. 정리 명령과 시간당 운영 절차는 [STEP6](STEP6.md)을 따릅니다.
