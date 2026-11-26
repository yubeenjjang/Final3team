# bus 구현과 검증

1. A04 동기 응답 헤더와 A05 선택 쿼리를 연결합니다. 일반 폴링 및 지역 근거에 외부 버스 호출이 없는지 확인합니다.
2. 서울 정류장 위치와 노선 정보를 읽고 승차 정류장 좌표·이름·노선·다음 정류장을 함께 대조합니다. 공급원 요청에는 기존 전송 로그 차단과 호출 한도를 적용합니다.
3. `SourceCache` 인터페이스를 사용하는 기존 메모리 구현으로 동시 조회를 합칩니다. DB 경로는 기존 TMAP 메모리 캐시를 사용해 매칭 정보를 읽습니다. 현재 DDL로 처리됩니다.
4. `backend/tests/routes/test_bus_crowding.py`는 저장한 15000314 정상·키 오류 응답과 합성 정류장 위치로 API를 검증합니다. `test_bus_crowding_db.py`는 일회용 `TEST_DB_URL`·`TEST_DB_APP_URL` 설정에서 동시 요청·교차 토큰 차단·RLS·보존 범위를 검증합니다.

모의 버스 경로는 A04의 `X-Mock-Scenario`를 `sync_bus_ready` 또는 `async_bus_ready`로 지정해 확인할 수 있습니다.

```sh
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```
