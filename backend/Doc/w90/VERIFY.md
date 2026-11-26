# W90 주변 시설 API 구현 기록

- 기준 브랜치: `yubeen`, 2026-11-25
- A26 `/festivals/{id}/transit`는 기존 구현을 확인했다. 서울 지하철·서울 버스·서울 밖 TAGO 조회와 지역 미지원 구분이 `backend/api/services/real_festival_info.py`에 있다.
- A08 `/festivals/{id}/facilities`를 추가했다. 분류·반경·분류별 건수 입력 검증, 축제 좌표 확인, DB 시설의 실제 거리 필터·정렬, 분류별 `ok`·`unverified`·`unsupported`·`unavailable`을 제공한다.
- `FACILITIES_PROVIDER=real`에서 `facilities` DB의 8개 정적 유형을 조회한다. `locker`·`pharmacy`는 설계대로 미지원이다. `food`·`attraction`은 카카오 로컬을 요청 때만 조회하고 결과를 DB·캐시에 저장하지 않는다. 키 부재·공급원 오류는 해당 분류를 `unavailable`로 표시한다.
- 기본 `mock` 모드는 시설 위치를 꾸며 내지 않고 `unverified`로 응답한다. 정적 시설이 DB에 없으면 `unverified`이며 전국 수집 완료로 간주하지 않는다.

## 검증 및 남은 조건

- Python 구문 검사와 `git diff --check` 통과.
- 로컬 Windows Python에 `httpx2`가 없어 pytest 수집 실패. WSL 시스템 Python에는 `pytest`가 없어 실행 불가. API 통합 시험은 의존성이 설치된 Linux/Docker 환경에서 재실행 필요.
- 현재 저장소에서 `facilities` 적재 작업은 발견되지 않았다. 실제 정적 시설을 제공하려면 공급원 원본 좌표·출처를 검증해 적재하고, 서울 정류장 ID와 A26 연결을 실DB에서 확인해야 한다.
- 카카오 장소 중계는 실키 호출·쿼터 동작을 확인하지 못했다. 실제 키와 분리된 시험 환경에서 응답·한도·오류를 확인해야 한다.

따라서 W90은 **API 코드 부분 완료, 실데이터·통합 시험 대기**다.

## 2026-11-26 정적 시설 적재 (권오현, 유빈님 위임)

- 적재 코드: `backend/api/ingestion/facilities/` — `python -m api.ingestion.facilities [source_id ...]`(수집 계정 `noldaga_service`, `SEOUL_OPEN_API_KEY`). 전체 목록을 다 받았을 때만 저장하고, `UNIQUE(source_id, source_item_id)` upsert라 다시 돌려도 행이 늘지 않는다. 원본에서 사라진 시설은 지우지 않는다(설계 '삭제 대신 숨김', 숨김 칸은 아직 없음).
- 공급원(서울 열린데이터광장 OpenAPI, 공공누리 제1유형·출처 표시, 좌표 WGS84 경위도 그대로):

| source_id | 서비스 | 분류 | 원본 → 적재 | 처리 |
|---|---|---|---|---|
| `seoul_bus_stop` | busStopLocationXyInfo | bus_stop | 11,223 → 11,215 | `STOPS_NO`(9자리 정류소 ID) = `source_item_id`, `NODE_ID`(5자리 ARS) = `ref_code`(A26 서울 버스 도착). 한강선착장 8건 제외 |
| `seoul_subway_station` | subwayStationMaster | subway_station | 784 → 657 | 노선별 행을 역 이름으로 묶음(1km 넘게 떨어진 동명 역은 따로), 괄호 부역명 제거, `region_code` 비움(A26이 축제 지역으로 판단) |
| `seoul_bike_station` | bikeStationMaster | bike_zone | 3,438 → 3,361 | 좌표 없는 77건 제외, `RNTLS_ID` = `ref_code` |
| `seoul_public_toilet` | mgisToiletPoi | toilet | 4,547 → 4,547 | |
| `seoul_public_parking` | GetParkInfo | parking | 2,244행(888곳) → 122 | 좌표 있는 공영주차장만(나머지 좌표 0) |
| `seoul_hospital` | TbHospitalInfo | hospital·emergency | 23,120 → 334 + 77 | 종합병원·병원만 hospital(의원·치과·한의원 제외), 응급실 운영(`DUTYERYN=1`) 77곳은 emergency |

- 학원 노트북 DB 적재(11/26, 백업 `~/noldaga-backup/noldaga_before_facilities_20261126_1039.dump`), 두 번째 실행은 새로 0·전부 갱신으로 멱등 확인. 서울빛초롱축제 A08(반경 1500m): taxi_stand만 `unverified`, 나머지 9개 분류 `ok`(화장실 82m, 버스 청계광장 55m, 따릉이 39m, 광화문역 261m, 강북삼성병원 858m 등).
- 시험: `backend/tests/ingestion/test_facilities_load.py`(오프라인 9), `test_facilities_load_db.py`(DB 2 — 재적재 멱등, 실패 시 기존 행 유지, 앱 계정 A08 조회).
- 남은 것: 택시 승강장(서울 OpenAPI 서비스 확인 안 됨), 서울 밖 시설(공공데이터포털 전국 표준데이터는 현재 키에 활용 신청 없음), 공영 외 주차장, 원본에서 사라진 시설 숨김 칸.
