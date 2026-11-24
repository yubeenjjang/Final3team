# Codex 작업 지시서 — STEP4 DB 저장

1. API 설계서 2·5·9·17-3·19절, DB 설계서 4·6-1·8절과 001~010을 대조한다. `origin/yubeen`의 `backend/shared/db/session.py`를 읽고 SPEC P16~P19의 임시 서비스 세션을 구현한다.
2. 011 사전 검사·적용·되돌리기·시험 SQL을 추가한다. 적용과 되돌리기는 각각 `psql -X -v ON_ERROR_STOP=1 -1 -f`로 실행한다. 기존 시험 뒤 `run_tests.sh` 6단계에서 010과 T011a~d를 검증한다.
3. `ROUTE_PROVIDER=real ROUTE_STORE=db FESTIVAL_DATA=db`에서 A02·A03과 같은 축제를 사용해 A04·A05를 연결한다. DB 모드는 서비스 접속 정보와 공통 `ROUTE_KEY_SECRET`을 요구한다. `ROUTE_STORE` 기본값은 `memory`다.
4. 저장소 루트에서 `_COMMON.md`의 공통 명령으로 전체를 실행한다. DB 시험은 001~011을 적용한 일회용 DB를 `TEST_DB_URL`로, 축제 조회용 `noldaga_app` 연결을 `TEST_DB_APP_URL`로 넘겨 같은 명령에 `-m db`를 추가한다. 011 적용·되돌리기 시험에는 DB 소유자 권한 또는 일회용 DB의 `TEST_DB_MIGRATION_URL`을 사용한다.
5. 정리 작업은 실행 주체 합의 후 시간마다 `RouteStore.purge_expired(datetime.now(timezone.utc))`를 호출한다. 운영 로그에는 정리 행 수와 실행 시각만 남긴다. 서비스 계정 접속 정보·기존 행·정리 주체의 확인 항목은 SPEC에 기록한다.
