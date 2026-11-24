# 축제 정보 API 구현 및 실호출 확인

## 오프라인 시험

저장된 공급원 응답과 합성 fixture만 사용합니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt python -m pytest backend/tests -q
```

## Claude 실호출

1. 루트에서 `DATA_GO_KR_SERVICE_KEY`와 `SEOUL_SUBWAY_API_KEY`가 이미 주입된 비밀 환경을 사용합니다. DB 접속에는 기존 `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER_USERNAME`, `DB_USER_PASSWORD`를 사용합니다. A29 스냅샷을 쓰려면 `DB_SERVICE_USERNAME`·`DB_SERVICE_PASSWORD`도 주입합니다. 서울 버스는 공공데이터포털의 서울 정류소 조회·버스도착정보 두 서비스가 승인된 키가 필요합니다.
2. A07은 006까지 적용된 DB에서 승인 공지가 있는 공개 축제를 선택합니다. A26은 `facilities`에서 반경 내 유효 역, 서울 ARS ID, TAGO 노드가 있는 축제를 각각 선택합니다. A29는 해당 축제의 `venue_name`과 공급원 `tAtsNm`이 일치하고 지역 코드가 확인된 연결만 준비합니다. 연결 파일은 `VISIT_FORECAST_MAPPING_FILE`에 지정하고, 다음 구조로 축제별 한 행을 저장합니다.

```json
{
  "fst_EXAMPLE": {
    "attraction": "SEA LIFE 부산아쿠아리움",
    "area_code": "26",
    "district_code": "26350"
  }
}
```

3. 비밀값이 환경에 주입된 셸에서 서버를 실행합니다. 호출 상한 상태 파일을 기존 실호출 작업과 공유해야 하는 경우 `FESTIVAL_INFO_QUOTA_FILE`을 해당 경로로 지정합니다.

```bash
set +x
: "${DATA_GO_KR_SERVICE_KEY:?공공데이터포털 키 필요}"
: "${SEOUL_SUBWAY_API_KEY:?서울 지하철 키 필요}"
export FESTIVAL_DATA=db
export NOTICES_PROVIDER=real WEATHER_PROVIDER=real TRANSIT_PROVIDER=real VISIT_FORECAST_PROVIDER=real
export VISIT_FORECAST_MAPPING_FILE
export VISIT_FORECAST_STORE=db
PYTHONPATH=backend uv run --offline --with-requirements backend/api/requirements.txt \
  python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

4. 다른 셸에서 `NOTICE_FESTIVAL_ID`, `WEATHER_FESTIVAL_ID`, `SEOUL_SUBWAY_FESTIVAL_ID`, `SEOUL_BUS_FESTIVAL_ID`, `TAGO_FESTIVAL_ID`, `VISIT_FESTIVAL_ID`에 확인한 공개 축제 ID를 넣습니다.

```bash
base=http://127.0.0.1:8000/api/v1/festivals
curl -fsS "$base/$NOTICE_FESTIVAL_ID/notices?type=operation&active_only=true"
curl -fsS "$base/$WEATHER_FESTIVAL_ID/weather"
curl -fsS "$base/$SEOUL_SUBWAY_FESTIVAL_ID/transit?mode=subway&limit=1"
curl -fsS "$base/$SEOUL_BUS_FESTIVAL_ID/transit?mode=bus&limit=1"
curl -fsS "$base/$TAGO_FESTIVAL_ID/transit?mode=bus&limit=1"
curl -fsS "$base/$TAGO_FESTIVAL_ID/transit?mode=subway&limit=1"
curl -fsS "$base/$VISIT_FESTIVAL_ID/visit-forecast?days=7"
```

| 호출 | 캐시가 없을 때 예상 공급원 호출 | 확인할 값 |
|---|---|---|
| A07 공지 | 0 | 타입·효력 필터와 미승인 제외 |
| A09 날씨 | 실황 1 + 예보 보통 1~2페이지 | `observed_at`, `forecast.issued_at`, 예보 대상 시각 |
| A26 서울 지하철 | 1 | `eta_s=0`과 공급원 문구 동시 보존 |
| A26 서울 버스 | 정류소 1 + 정류소가 가진 노선 수만큼 노선당 1 | `ARS_ID` 앞자리 0, 정류장 대조, 일치했을 때 혼잡 |
| A26 TAGO | 도착 1, 도시 코드가 미적재된 경우 근접 목록 통상 1회 추가 | `eta_s`, `remaining_stops`, 빈 결과 |
| A26 서울 밖 지하철 | 0 | `unsupported` |
| A29 예측 | 시군구 1,000행당 1페이지 + 지역 수요 1. 11/19 해운대 조건 기준 2회 예상(570행) | 일별 상대 점수, 직전 달 수요, `realtime_snapshots` 두 종류 |

일시 오류 재시도는 공급원 호출별 한 번까지 추가됩니다. A09와 A26은 같은 조건으로 캐시 시간 안에 다시 조회하면 공급원 호출이 추가되지 않습니다. A29는 일일 수집 대상으로 선택한 매핑의 경로를 매일 KST 기준 한 번 호출하고, 같은 날짜의 DB 적재본이 있으면 추가 공급원 요청은 0회입니다.

일일 보호값은 KMA·TAGO 정류소·TAGO 도착이 각각 10,000, 서울 지하철·서울 버스·서울 정류소·관광 집중 예측·관광 수요가 각각 1,000입니다. 테스트나 운영 예산을 줄이려면 `KMA_DAILY_LIMIT`, `TAGO_STOP_DAILY_LIMIT`, `TAGO_ARRIVAL_DAILY_LIMIT`, `SEOUL_SUBWAY_DAILY_LIMIT`, `SEOUL_BUS_DAILY_LIMIT`, `SEOUL_BUS_STATION_DAILY_LIMIT`, `VISIT_FORECAST_DAILY_LIMIT`, `REGION_DEMAND_DAILY_LIMIT`를 설정합니다.
