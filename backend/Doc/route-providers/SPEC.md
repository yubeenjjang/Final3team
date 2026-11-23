# SPEC — 귀가 경로 실제 조회 (TMAP 1차 · 카카오 2차)

- 기준: API 설계문서 v0.3.3(2-2 A04·A05, 5절, 9절, 10-2, 10-3). **이 SPEC에 필요한 것을 옮겼으니 설계서 전체를 읽지 않는다.** 다른 점은 `IMP-PLAN.md` '메모'에.
- 요구 번호 `P1`~. 시험 이름에 번호(`test_P4_tmap_reverses_coordinates`).
- 시험: `uv run --offline --with-requirements api/requirements.txt pytest tests/routes tests/ingestion tests/api -q`
- 고정 파일: `tests/routes/fixtures/`(Claude가 `Docs/Step 2/evidence/responses/합성예시_*`에서 복사, **합성 데이터 — 실제 경로 아님**). Codex는 고치지 않는다.

## 0. 원본 모양 (합성 고정 파일로 확인)
| 공급원 | 호출 | 성공 모양 |
|---|---|---|
| TMAP 대중교통 | `POST https://apis.openapi.sk.com/transit/routes`, 헤더 `appKey`, `Accept`·`Content-Type: application/json`, 본문 `{startX(경도), startY(위도), endX, endY, count:3, lang:0, format:"json", searchDttm?:"YYYYMMDDHHMM"}` | `metaData.plan.itineraries[]`: `totalTime`(초)·`totalWalkDistance`(m)·`transferCount`·`fare.regular.totalFare`·`legs[]`(`mode` WALK/BUS/SUBWAY·`sectionTime`(초)·`distance`·`route`·`routeId`·`service`(1/0)·`Lane[]`(대체 노선, 각 `service`, 합성 고정 파일에서 미확인)·`passStopList.stations[]{stationName, stationID, lat, lon}`·`passShape.linestring`·도보는 `steps[].linestring`) |
| 카카오 대중교통 | `GET https://dapi.kakao.com/v2/routing/publictraffic?start_x=경도&start_y=위도&end_x&end_y`, 헤더 `Authorization: KakaoAK <키>` | 본문 `status`("OK" 등), `routes[]{properties{type, totalDistance, totalTime(초), transfers, fare{value}}, steps[]{properties{type, distance, time, stops[{name}], vehicles[{name,type}]}, path{points[[경도,위도],…]}}}` |
| 카카오 장소 검색 | `GET https://dapi.kakao.com/v2/local/search/keyword.json?query=…&size=1`, 같은 헤더 | `documents[0]{place_name, x(경도), y(위도), address_name}` |
- **좌표 순서:** TMAP `linestring` = `"경도,위도 경도,위도 …"`, 카카오 `points` = `[경도, 위도]`. **내부 형식은 `[위도, 경도]`**(지금 모의와 같음).

## 1. 공통 (1단계) — `api/providers/route_base.py`
### P1. 내부 형식
- `RouteQuery`: `origin:(lat,lng)`, `destination:(lat,lng)`, `depart_at: datetime|None`.
- `ProviderResult`: `provider`("tmap"|"kakao"), `provider_tier`("primary"|"secondary"), `queried_at`(KST ISO), `candidates: list[dict]`(아래), `notices: list[str]`.
- 후보 dict = **지금 모의 후보와 같은 칸**: `candidate_id`("c1"…), `summary`(예: "버스 1회"·"지하철 1회 환승"), `duration_min`(올림), `distance_m`, `walk_m`, `transfers`, `fare_krw`, `legs[{mode:"walk"|"bus"|"subway", duration_min, path:[[lat,lng],…], line?:노선 이름, stops?:[{name, id?, lat?, lng?}]}]`, `service_running`, `score:None`, `area_evidence:{crowd_areas:[], traffic_incidents:[]}`, `mode_evidence:{bus_crowding:{status, reason}}`.
- `ProviderError(kind, provider, detail)` — `kind` ∈ `config`(키 오류) · `no_result` · `service_ended`(TMAP 후보 전부 운행 종료) · `too_close` · `bad_request` · `region` · `temporary` · `timeout` · `quota`. `detail`에 **키 없음**.
- **확인:** 후보 dict 칸 이름이 `api/services/mock_routes.py`의 `_candidate()` 칸과 같다(시험에서 키 집합 비교).

## 2. TMAP 어댑터 (1단계) — `api/providers/tmap.py`
### P2. 호출
- 키: 환경변수 `TMAP_APP_KEY`(없으면 `ProviderError("config")`). `httpx2.Client` 주입 가능, 제한 **5초**, **재시도 없음**(전환은 서비스가 함 — 한도 보호).
- **확인:** MockTransport로 요청 본문 `startX`=출발 경도·`startY`=출발 위도·`count`=3, 헤더 `appKey` 있음 · 예외·`repr`에 키 없음.
### P3. 오류 판정(10-3) — HTTP → 본문 순서
| 응답 | kind |
|---|---|
| 403 + `error.code=INVALID_API_KEY` / 401·403 | `config` |
| 200 + `result.status` 11 | `too_close` |
| 200 + `result.status` 12·13·14 | `no_result` |
| 400 + `result.status` 21·22·24 | `bad_request` |
| 400 + `result.status` 23 | `region` |
| 429 | `quota` |
| 500·502·503 + 31·32, 그 밖 5xx | `temporary` |
| 시간 초과·연결 오류 | `timeout` / `temporary` |
| 200인데 `itineraries` 없음·JSON 아님 | `no_result` / `temporary` |
- **확인:** 고정 파일 `tmap_error_key.json`(403) → `config` · 각 행 1개씩(dict로 만든 응답).
### P4. 변환
- `itineraries` 최대 3개 → 후보. `duration_min = ceil(totalTime/60)`, `walk_m = totalWalkDistance`, `transfers = transferCount`, `fare_krw = fare.regular.totalFare`, `distance_m = totalDistance`.
- 구간: `mode` 소문자. 경로선 = `passShape.linestring`(없으면 `steps[].linestring` 이어 붙임) → **`[위도, 경도]`로 뒤집기**, 소수 6자리. `line = route`, `stops = passStopList.stations[]`(`{name, id, lat, lng}` 숫자로).
- **막차 `service_running`:** 6절 P13 적용.
- `summary`: 대중교통 구간 종류·환승 수로 "지하철 1회 환승"·"버스 1회"처럼.
- `mode_evidence.bus_crowding = {status:"unverified", reason:"버스 혼잡 연결 전"}`.
- **확인:** `tmap_seoul.json` → 후보 1개, 모든 `path` 첫 값 33~39(위도)·둘째 124~132 · 구간 종류 walk/bus/walk. 막차 시험은 P15.

## 3. 카카오 어댑터 (1단계) — `api/providers/kakao.py`
### P5. 호출·오류
- 키: `KAKAO_REST_API_KEY`. 제한 **3초**(동기 응답 안에서만 쓰므로), 재시도 없음.
| 응답 | kind |
|---|---|
| 401 / 403 | `config` |
| 400 + `code=-10` | `quota` |
| 429 | `quota` |
| 200 + `status` `NO_RESULTS`·`STARTNODES_NULL`·`ENDNODES_NULL`·`EQUAL_POINTS` | `no_result` |
| 200 + `status` `INVALID_REQUEST` | `bad_request` |
| 5xx·연결 오류 / 시간 초과 | `temporary` / `timeout` |
- **확인:** `kakao_error_key.json`(401) → `config` · 각 행.
### P6. 변환
- `routes` 앞에서 **최대 3개**. `duration_min = ceil(properties.totalTime/60)`, `distance_m = totalDistance`, `transfers`, `fare_krw = fare.value`, `walk_m = None`(첫·끝 도보 없음).
- 구간: `properties.type` → `BUS`→bus·`SUBWAY`→subway·`WALK`→walk, `duration_min = ceil(time/60)`, `path = points`를 `[위도, 경도]`로, `line = vehicles[0].name`, `stops = [{name}]`(ID·좌표 없음).
- `service_running = None`(P14) + `notices`에 "2차 공급원(카카오맵) 결과예요. 이 결과는 저장하지 않아 다시 보려면 새로 조회해야 해요." · "첫·끝 도보 정보가 없어요" · "막차 확인 불가".
- `mode_evidence.bus_crowding = {status:"unsupported", reason:"2차 공급원은 버스 혼잡 근거를 주지 않아요"}`.
- 도보 보완 API는 **이번에 부르지 않는다**(호출 아끼기, 나중).
- **확인:** `kakao_transit_seoul.json` → 후보 1개·좌표 순서·notice 3개.
### P7. 장소 검색 `search_place(query) -> (lat, lng, label)`
- 결과 0건 → `ProviderError("no_result")`. **결과를 저장·캐시하지 않는다**(라벨은 사용자가 입력한 글자 그대로 씀).
- **확인:** dict 응답 1건 → (위도, 경도) 순서 · 0건 → `no_result`.

## 4. 한도 계산기 (1단계) — `api/providers/quota.py`
### P8.
- 공급원별 **KST 날짜 기준** 하루 건수. 한도: `ROUTE_TMAP_DAILY_LIMIT`(기본 **10**), `ROUTE_KAKAO_DAILY_LIMIT`(기본 **1000**), `ROUTE_KAKAO_LOCAL_DAILY_LIMIT`(기본 1000 — 넉넉해도 시연 보호).
- `try_acquire(provider) -> bool`: 남았으면 1 올리고 True, 아니면 False(**부르기 전에** 셈 — 오류 응답도 1건으로 셈, 9절). 80% 넘으면 경고 로그 1번.
- 저장: 파일 `ROUTE_QUOTA_FILE`(기본 `./.route_quota.json`), 파일 잠금(`fcntl`)으로 여러 요청이 동시에 와도 정확. 날짜가 바뀌면 0부터. (나중에 Redis `quota:{provider}`로 바꿀 수 있게 클래스 하나.)
- `status() -> {provider: {used, limit}}`.
- **확인:** 한도 2로 3번 → True, True, False · 날짜 바뀜(시각 주입) → 다시 True · 스레드 20개 동시 → 정확히 한도만 True.

## 5. 실제 경로 서비스 (2단계) — `api/services/real_routes.py`
### P9. 켜기
- `ROUTE_PROVIDER=mock|real`(기본 `mock` — 지금 동작 그대로). `real`이면 A04·A25 접수와 A05 조회가 이 서비스를 쓴다. **응답 칸·상태 흐름·토큰 규칙·오류 형식은 지금(R11~R13·R23~R25)과 같다.** `is_mock: false`, `X-Mock` 없음(main.py 미들웨어에 경로 주소 추가).
- `X-Mock-Scenario` 헤더는 `real`에서 무시(시험용 기능이라).
### P10. 처리 순서
1. 축제 찾기(`find_festival`) → 출발·도착 좌표. 사용자 장소는 `query`면 장소 검색(P7), `lat·lng`면 그대로. 실패: 장소 검색 `no_result` → 400 `ROUTE_INVALID`.
2. `route_key` = **HMAC-SHA256**(키 `ROUTE_KEY_SECRET`, 없으면 서버 시작 때 임의 생성) of `방향|출발(소수 4자리)|도착(4자리)|travel_mode|route_preference|출발 시각 5분 구간` — 원문 좌표를 키에 남기지 않음(강사 DB 피드백 2).
3. **캐시(TMAP 결과만, 60초, 메모리):** 같은 `route_key`가 있으면 공급원을 부르지 않고 그 결과로 `ready`.
4. **요청 병합:** 같은 `route_key`가 처리 중이면 새로 부르지 않고 그 결과를 기다린다(메모리, 12초 뒤 풀림).
5. 1차 TMAP: `quota.try_acquire("tmap")`가 False면 건너뜀. 호출 → 성공이면 `ready`(provider tmap, primary), 캐시 저장.
6. 1차 실패(`temporary`·`timeout`·`quota`·`config`·`no_result`(12~14)·`region`) 또는 건너뜀 → **접수 뒤 3초 안이면** 2차 카카오 1회(`try_acquire("kakao")`). `too_close`·`bad_request`·`service_ended`는 2차로 안 넘김.
7. 결과 판정: 성공 → `ready`(`completed_valid_route=True`). 실패 → `unavailable` + 오류 코드: `too_close`·`no_result`·`service_ended` → `ROUTE_NO_RESULT`(`retryable=false`, `too_close` 문구 "걸어서 갈 수 있는 거리예요", `service_ended` 문구 "지금은 대중교통으로 갈 수 없어요") · `bad_request` → `ROUTE_INVALID` · 두 공급원 모두 `quota`/건너뜀 → `ROUTE_QUOTA_EXCEEDED` · `timeout` → `timed_out`+`ROUTE_TIMEOUT` · 그 밖 → `ROUTE_UPSTREAM_ERROR`(retryable true).
### P11. 동기·비동기
- A04는 처리를 시작하고 **최대 3초** 기다린다. 3초 안에 끝나면 **200 + 전체 본문**(지금 `sync_ready`와 같은 모양). 넘으면 **202 접수**(지금과 같은 본문), 처리는 계속(프로세스 안 백그라운드 작업). 전체 **10초** 넘으면 `timed_out`.
- **카카오 결과는 200(동기) 응답에서만 준다.** 202 뒤에 1차가 실패해서 2차가 필요해지면 카카오를 부르지 않고 `unavailable` + `ROUTE_SECONDARY_SYNC_ONLY`(retryable true).
- A04 200으로 준 카카오 결과를 A05로 다시 조회하면 `unavailable` + `ROUTE_SECONDARY_SYNC_ONLY`(R23과 같음). 결과 본문은 **메모리에도 남기지 않는다**(상태·오류만).
- TMAP 결과는 A05 조회용으로 메모리에 보관하되 **`valid_until`(60초) 뒤에는 `ROUTE_RESULT_EXPIRED`**(retryable true)로 답하고 본문을 지운다.
### P12. 확인(일반 시험, 공급원은 가짜 객체 주입 — 네트워크 없음)
- TMAP 성공 → 200 `ready`, `provider=="tmap"`, `is_mock is False`, `X-Mock` 없음
- TMAP `temporary` → 카카오 성공 → 200, `provider_tier=="secondary"`, A05 재조회 → `ROUTE_SECONDARY_SYNC_ONLY`
- TMAP 4초 걸림(가짜 지연) → 202 → A05 2회차 `ready`(TMAP)
- TMAP 4초 뒤 실패 → 202 → A05 `unavailable` + `ROUTE_SECONDARY_SYNC_ONLY`, **카카오 호출 0회**
- TMAP 한도 0 → 카카오로 · 둘 다 한도 0 → `ROUTE_QUOTA_EXCEEDED`, 공급원 호출 0회
- `too_close` → `ROUTE_NO_RESULT`, 카카오 호출 0회
- 같은 요청 2번(다른 `request_id`) 60초 안 → TMAP 호출 1회 · 동시에 5개 → TMAP 호출 1회
- TMAP 결과 61초 뒤 A05 → `ROUTE_RESULT_EXPIRED`(시각 주입)
- `route_key`에 좌표 문자열이 들어 있지 않음
- `ROUTE_PROVIDER` 없음 → 기존 시험 전부 그대로

## 6. STEP3 막차 처리 (강사 API 2 · W36 일부)

### P13. TMAP 후보 판정
- 합성 예시 `Docs/Step 2/evidence/responses/합성예시_tmap_{서울,부산}.json` 및 `tests/routes/fixtures/tmap_{seoul,busan}.json`은 `metaData.plan.itineraries[].legs[].service`의 필드 구조를 참고하는 데 쓴다. 대표 노선 0·대체 노선 1이 같은 구간에 나오는 동작은 11/20 실제 호출 기록을 근거로 한다.
- 도보 구간은 막차 판정에서 제외한다. 교통 구간은 대표 노선과 대체 노선의 `service` 중 하나라도 1이면 운행 중, 확인 대상이 모두 0이면 종료다. 정수와 문자열 0·1을 허용한다. 하나라도 종료된 교통 구간이 있는 후보는 제외하고, 남은 후보의 순서와 ID를 유지한다. 일부만 제외되면 `ready`의 `notices`에 "운행이 끝난 구간이 있어요"를 넣는다.
- **확인 필요:** 합성 고정 파일에 대체 노선 목록과 대체 노선명 필드가 없다. 코드의 `Lane`과 API 설계서의 `lane`을 모두 읽는다. 대표 노선이 운행 중이면 대표 이름을 쓰고, 대체 노선이 운행 중이면 문자열 `route`가 확인되는 대체 노선 이름을 쓴다. 대표 노선의 운행이 확인되지 않고 운행 중인 대체 노선의 이름이 없으면 `line`을 생략한다. `service` 누락·알 수 없는 값은 종료로 단정하지 않고, 종료가 확인된 구간이 없으면 후보를 유지하고 `service_running=null`로 표시한다.

### P14. API 응답과 카카오
- TMAP 후보가 전부 운행 종료로 제외되면 기존 공급원 전환 없이 HTTP 200, `route_status=unavailable`, `completed_valid_route=false`, `ROUTE_NO_RESULT`, `retryable=false`, 오류 문구 "지금은 대중교통으로 갈 수 없어요"와 운행 종료 안내를 반환한다. 공급원의 기존 `no_result` 오류는 기존 전환 규칙을 따른다.
- 카카오는 `service_running=null`과 "막차 확인 불가" 안내를 반환한다. 본문은 동기 응답에서만 전달한다. 모의 경로와 기존 모의 시나리오를 유지한다.

### P15. 시험 및 문서
- 실제 공급원 어댑터에 합성 고정 파일과 MockTransport를 주입해 정상·일부 종료·전부 종료·카카오 동기 결과와 A05 재조회를 검증한다. 운행 중 대체 노선, 정보 누락, 기존 전환 규칙도 검증한다.
- 전체 백엔드 시험을 오프라인으로 실행하고 API 설계서 0-A·5·17-3·19절, v0.4 변경 이력 및 API 연동 현황표를 갱신한다.
