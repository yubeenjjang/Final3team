# SPEC — 계약 기반 모의 API 서버

- 기준: `Docs/Step 2/API_설계문서.md` v0.3.3. **이 SPEC에 필요한 계약을 옮겨 두었으니 구현할 때 API 설계문서 전체를 읽지 않는다.** 문서와 이 SPEC이 다르면 이 SPEC을 따르고, 다른 곳을 `Doc/IMP-PLAN.md`의 '메모'에 적는다.
- 모든 요구에는 **확인 방법**이 있다. 확인 방법은 `backend/tests/api/`의 pytest 시험으로 만든다(시험 이름에 요구 번호를 넣는다. 예: `test_R4_region_filter`).
- 실행 환경: Python 3.14(안 되면 3.13), `uv`. 명령은 `backend/` 폴더에서 실행한다.
  - 서버: `uv run --with-requirements api/requirements.txt uvicorn api.main:app --reload --port 8000` → `http://localhost:8000/docs`
  - 시험: `uv run --with-requirements api/requirements.txt pytest tests/api -q`
- import는 `backend/`를 기준으로 `from api.… import …`.

## 0. 공통

### R1. 앱·실행
- `api/main.py`의 `app`(FastAPI). 제목 `놀다가 API (mock)`, 버전 `0.1.0-mock`.
- 라우터는 모두 `/api/v1` 아래. `main.py`가 아래 라우터를 **모두** 등록한다(나중 단계 라우터도 1단계에서 빈 `APIRouter`로 만들어 등록해 둔다 → 2·3단계는 `main.py`를 고치지 않는다).
  - `api/routers/health.py`, `api/routers/festivals/catalog.py`, `api/routers/routes/routes.py`, `api/routers/assistant/chatbot.py`, `api/routers/accounts/auth.py`
- CORS 허용 출처: `http://localhost:3000`, `http://localhost:5173`. 헤더 `X-Request-ID`·`X-Route-Access-Token`·`X-Run-Access-Token`·`X-Mock-Scenario`·`Authorization`를 허용하고, 응답 헤더 `X-Request-ID`를 노출한다.
- 가상 상태(메모리 저장소)는 `api/mocks/store.py`의 `reset_store()`로 초기화할 수 있다. 시험은 매번 초기화한다(`tests/api/conftest.py` fixture).
- **확인:** `/openapi.json` 200 · `/api/v1/health` 200 · 시험이 서로 순서에 영향받지 않음(같은 시험을 두 번 돌려도 통과).

### R2. 공통 오류 형식
- 모든 오류 응답 본문: `{"error": {"code": str, "message": str(한국어), "request_id": str, "retryable": bool}}`
- 형식 오류(Pydantic·경로/쿼리 검증)는 **422 `VALIDATION_ERROR`** 로 바꾼다(FastAPI 기본 `detail` 모양을 쓰지 않음). `message`에 어느 칸이 틀렸는지 넣는다.
- 오류는 `api/errors.py`의 `ApiError(status, code, message, retryable=False)`를 raise해서 만든다.
- 없는 주소 404도 같은 모양(`code: "NOT_FOUND"`).
- **확인:** 잘못된 쿼리로 A02 호출 → 422 + `error.code=="VALIDATION_ERROR"` + `detail` 키 없음 · 없는 주소 → 404 같은 모양.

### R3. `X-Request-ID`
- 요청에 `X-Request-ID`(1~64자)가 있으면 그대로, 없거나 형식이 틀리면 서버가 `req_` + 26자(영숫자)로 만든다. 응답 헤더 `X-Request-ID`와 오류 본문 `error.request_id`에 같은 값을 넣는다.
- **확인:** 보낸 값이 그대로 돌아옴 · 안 보내면 `^req_[0-9A-Za-z]{26}$` · 오류 본문의 `request_id`와 헤더가 같음.

### R4. 모든 응답에 `is_mock: true`
- 성공 응답 본문 최상위에 `is_mock: true`(목록·상세·상태·작업·인증·health 모두). 응답 헤더에도 `X-Mock: true`.
- **확인:** 각 단계 시험에서 성공 응답마다 `is_mock is True`.

### R5. 외부 호출 없음
- `httpx`·`requests`·`urllib`로 외부 주소를 부르는 코드가 없다. API 키·환경변수를 읽지 않는다.
- **확인:** 시험 `test_R5_no_external_calls` — `api/` 아래 `.py`에서 `http://`·`https://` 문자열이 들어간 줄은 허용 목록(이미지 주소 `https://tong.visitkorea.or.kr/`, `localhost`)만 있음.

## 1. 축제 (1단계)

### R6. 가상 축제 데이터 (`api/mocks/festivals.py`)
아래 6건을 그대로 쓴다(값은 모양을 보이기 위한 가상 값). `source="tourapi"`, `last_synced_at="2026-11-22T09:00:00+09:00"`, `image_credit`은 이미지가 있으면 `"한국관광공사"`, 없으면 `null`.

| festival_id | name | region_code | venue_name | lat, lng | start_date ~ end_date | event_status | 이미지 |
|---|---|---|---|---|---|---|---|
| `fst_000001` | 광화문 겨울빛 축제 | SEOUL | 광화문광장 | 37.5759, 126.9768 | 2026-11-20 ~ 2026-12-31 | ongoing | 있음, Type3 |
| `fst_000002` | 한강 겨울 야시장 | SEOUL | 여의도 한강공원 | 37.5284, 126.9327 | 2026-12-05 ~ 2026-12-07 | upcoming | 있음, Type1 |
| `fst_000003` | 부산 빛 축제 | BUSAN | 광복로 일대 | 35.1003, 129.0337 | 2026-11-15 ~ 2026-11-30 | ongoing | 있음, Type3 |
| `fst_000004` | 해운대 모래 축제 | BUSAN | 해운대해수욕장 | 35.1587, 129.1604 | 2026-06-01 ~ 2026-06-03 | ended | 있음, Type3 |
| `fst_000005` | 평창 송어 축제 | GANGWON | 오대천 일원 | 37.5640, 128.3846 | 2026-12-26 ~ 2027-01-25 | upcoming | 없음 |
| `fst_000006` | 장소 미정 축제 | GYEONGGI | null | null, null | null ~ null | needs_review | 없음 |

- 이미지 주소: `image_url = "https://tong.visitkorea.or.kr/cms/resource/mock/<id>_1.jpg"`, `thumbnail_url = "…/<id>_2.jpg"`. `image_copyright = {type, credit:"한국관광공사", modify_allowed: type=="Type1"}`, 이미지가 없으면 세 칸 모두 `null`.
- 상세 전용 칸: `address`(venue가 있으면 "<venue_name> 일대", 없으면 null), `overview`("<name> 소개(모의)"), `fee_text`("무료" 또는 null — 1·3번만 "무료"), `homepage_url`(null), `source_ref`("<id 숫자>").

### R7. A02 `GET /api/v1/festivals`
| 쿼리 | 규칙 |
|---|---|
| `region` | 0-1절 지역 코드(`ALL`·`SEOUL`·`BUSAN`·`DAEGU`·`INCHEON`·`GWANGJU`·`DAEJEON`·`ULSAN`·`SEJONG`·`GYEONGGI`·`GANGWON`·`CHUNGBUK`·`CHUNGNAM`·`JEONBUK`·`JEONNAM`·`GYEONGBUK`·`GYEONGNAM`·`JEJU`), 기본 `ALL`. 그 밖의 값 422 |
| `date_from`·`date_to` | `YYYY-MM-DD`. 축제 기간이 이 기간과 **겹치면** 포함. 날짜 없는 축제는 기간 필터가 있으면 제외. `date_from > date_to`면 422, 기간 366일 초과 422 |
| `q` | 1~50자, `name` 또는 `venue_name`에 포함(대소문자 무시) |
| `status` | `upcoming`·`ongoing`·`ended`·`cancelled` |
| `sort` | `start_date`(기본, 날짜 없는 것은 맨 뒤)·`-start_date`·`name` |
| `page`·`page_size` | 1 이상 / 1~100, 기본 1 / 20 |

- 응답 200: `{items:[목록 칸], total, page, page_size, is_mock}`. 목록 칸 = `festival_id, name, region_code, venue_name, lat, lng, start_date, end_date, event_status, thumbnail_url, image_credit, source, last_synced_at`.
- **확인:** 필터 없음 → total 6 · `region=SEOUL` → 2 · `region=BUSAN&status=ongoing` → `fst_000003`만 · `date_from=2026-12-01&date_to=2026-12-10` → `fst_000001`,`fst_000002` · `q=야시장` → `fst_000002` · `page_size=2&page=3` → items 2개, total 6 · 기본 정렬에서 `fst_000006`이 마지막 · `region=MARS` 422 · `date_from=2026-12-10&date_to=2026-12-01` 422 · `page_size=101` 422.

### R8. A03 `GET /api/v1/festivals/{festival_id}`
- `festival_id`는 `^fst_[0-9A-Za-z]{6,26}$`. 형식이 틀리면 422, 없으면 **404 `FESTIVAL_NOT_FOUND`**.
- 응답 200: 목록 칸 + `address, overview, fee_text, homepage_url, image_url, image_copyright, source_ref, is_mock`.
- **확인:** `fst_000001` → `image_copyright.type=="Type3"`, `modify_allowed is False`, `image_credit=="한국관광공사"` · `fst_000002` → `modify_allowed is True` · `fst_000005` → `image_url is None` 이고 `image_copyright is None` · `fst_999999` → 404 `FESTIVAL_NOT_FOUND` · `abc` → 422.

### R9. A01 `GET /api/v1/health`
- 200 `{status:"ok", db:"mock", redis:"mock", version:"0.1.0-mock", is_mock:true}`.
- **확인:** 위 값 그대로.

## 2. 귀갓길·가는 길 (2단계)

### R10. 입력 모델 (`api/schemas/routes.py`)
```python
class Place(BaseModel):            # query 또는 lat+lng 중 하나만 (둘 다/둘 다 없음 → 422)
    query: str | None  # 1~100자
    lat: float | None  # 33.0~39.0
    lng: float | None  # 124.0~132.0
class FestivalEndpoint(BaseModel): type: Literal["festival"]
class PlaceEndpoint(Place):        type: Literal["place"] = "place"   # type 생략하면 place
Endpoint = FestivalEndpoint | PlaceEndpoint
class UserConstraints(BaseModel):  with_child: bool=False; wheelchair: bool=False; max_walk_m: int|None (0~5000)
# 공통: request_id(8~64자), festival_id(^fst_…), travel_mode(transit|walk|car|taxi, 기본 transit),
#       route_preference(fastest|less_crowded|accessible|min_walk|fewest_transfers, 기본 fastest),
#       user_constraints, departure(Literal["now"], 기본 now)
class ReturnRouteRequest: origin: Endpoint = {"type":"festival"}; destination: Endpoint
class VisitRouteRequest:  origin: Endpoint;                     destination: Endpoint = {"type":"festival"}
# 두 모델 모두: origin·destination이 둘 다 festival이면 422 VALIDATION_ERROR
```
- **확인:** 귀가에 `destination` 없음 → 422 · `destination: {query:"서울역", lat:37.5, lng:126.9}` → 422 · 귀가에 `origin:{type:"festival"}, destination:{type:"festival"}` → 422 · 가는 길에 `destination` 생략 + `origin:{query:"서울역"}` → 접수됨 · `travel_mode:"bike"` → 422.

### R11. A04 `POST /api/v1/routes/return` — 서버 판단 순서
1. 축제가 없으면 **404 `FESTIVAL_NOT_FOUND`**
2. 출발이나 도착이 축제 장소인데 축제 좌표가 없으면(`fst_000006`) **400 `FESTIVAL_LOCATION_UNKNOWN`**. 출발·도착이 모두 사용자 장소면 좌표가 없어도 접수
3. `query`에 `없는곳`이 들어 있으면 **400 `ROUTE_INVALID`**("목적지를 찾을 수 없어요")
4. 멱등: 같은 `request_id`로 **본문이 같으면** 처음 만든 요청을 그대로 돌려줌(새로 만들지 않음), **본문이 다르면 409 `IDEMPOTENCY_CONFLICT`**
5. 시나리오(`X-Mock-Scenario` 헤더, 없으면 `async_ready`)

| `X-Mock-Scenario` | A04 응답 | 그 뒤 A05 |
|---|---|---|
| `async_ready`(기본) | **202** 접수 | 첫 조회 `processing`, 두 번째부터 `ready` |
| `sync_ready` | **200** `ready` 전체 본문(토큰 없이 바로 결과) | 조회하면 `ready` |
| `async_unavailable` | 202 | 첫 조회 `processing`, 두 번째부터 `unavailable` + `error{ROUTE_UPSTREAM_ERROR, retryable:true}` + `notices` |
| `async_timeout` | 202 | 첫 조회 `processing`, 두 번째부터 `timed_out` + `error{ROUTE_TIMEOUT, retryable:true}` |
| `overloaded` | **503 `ROUTE_OVERLOADED`**(retryable:true) — 요청 기록은 `rejected` | — |
| 그 밖의 값 | 422 | — |

- **202 본문:** `{route_request_id: "rr_"+16자, route_status:"queued", status_url:"/api/v1/routes/return/<id>", route_access_token:"rrt_"+24자, retry_after_s:2, is_mock:true}`
- **200(ready) 본문:** `route_request_id, route_status:"ready", direction:"return", festival_id, origin, destination, travel_mode, route_preference, route_candidates[1개], provider:"mock_adapter", provider_tier:"mock", queried_at(ISO+09:00), verification_status:"control_unverified", completed_valid_route:true, constraint_status, coverage, score_version:null, notices:["공식 교통통제 반영 여부를 확인하지 못했어요."], is_mock:true`
  - `origin`: 축제 장소면 `{type:"festival", name:"<venue_name>", lat, lng}`, 사용자 장소면 `{type:"place", label:<query 또는 "lat,lng">}`. `destination`도 같은 규칙
  - 후보 1개: `{candidate_id:"c1", summary:"지하철 1회 환승(모의)", duration_min:38, distance_m:9200, walk_m:650, transfers:1, fare_krw:1550, legs:[{mode:"walk",duration_min:6,path:[[lat,lng],[lat,lng]]},{mode:"subway",line:"(모의)",duration_min:24,path:[…]},{mode:"walk",duration_min:8,path:[…]}], service_running:true, score:null, area_evidence:{crowd_areas:[], traffic_incidents:[]}, mode_evidence:{bus_crowding:{status:"unverified", reason:"모의 응답"}}}` — `path`는 **`[위도, 경도]` 순서**
  - `constraint_status`: 요청한 조건마다 `"not_verifiable"`(예: `with_child:true` → `{"with_child":"not_verifiable"}`), 항상 `"control":"unverified"`
  - `coverage`: `{scope:"national", region_code:<축제 지역>, supported:true}`
- **확인:** 기본 → 202, `route_access_token` 시작이 `rrt_` · `sync_ready` → 200, `completed_valid_route is True`, 모든 `path` 원소 첫 값이 33~39(위도) · `fst_999999` → 404 · `fst_000006` + 축제 출발 → 400 `FESTIVAL_LOCATION_UNKNOWN` · `fst_000006` + 출발·도착 둘 다 `place` → 202 · `query:"없는곳"` → 400 `ROUTE_INVALID` · 같은 `request_id`·같은 본문 두 번 → 같은 `route_request_id` · 같은 `request_id`·다른 본문 → 409 · `overloaded` → 503 `ROUTE_OVERLOADED`, `retryable is True` · 알 수 없는 시나리오 → 422.

### R12. A05 `GET /api/v1/routes/return/{route_request_id}`
- 경로 `^rr_[0-9A-Za-z]{6,26}$`(아니면 422). 헤더 `X-Route-Access-Token` 필수: 없으면 **401 `UNAUTHORIZED`**, 다른 요청의 토큰이면 **403 `FORBIDDEN`**, 없는 ID **404 `ROUTE_REQUEST_NOT_FOUND`**(형식은 맞을 때). `sync_ready`로 만든 요청은 202를 받은 적이 없으므로 이 요청에 대한 토큰을 A04 200 본문에 `route_access_token`으로도 함께 넣는다.
- 조회는 항상 **200**(처리가 실패해도 조회는 성공). 본문: `route_request_id, route_status, completed_valid_route, updated_at, is_mock` + 상태별로
  - `queued`·`processing`: `retry_after_s: 2`
  - `ready`: R11 200 본문과 같은 칸
  - `unavailable`·`timed_out`: `error{code, message, retryable}`, `notices`
- `completed_valid_route`는 `ready`일 때만 true.
- **확인:** 기본 시나리오에서 조회 1회차 `processing`·`completed_valid_route is False`·`retry_after_s==2`, 2회차 `ready`·true, 3회차도 `ready` · 토큰 없음 401 · 다른 요청 토큰 403 · `rr_zzzzzzzz` 404 · `async_unavailable` 2회차 `error.code=="ROUTE_UPSTREAM_ERROR"` · `async_timeout` 2회차 `route_status=="timed_out"`.

### R13. A25 가는 길 `POST /api/v1/routes/visit` + `GET /api/v1/routes/visit/{id}`
- R11·R12와 같은 규칙, `direction:"visit"`, 기본 `origin` 없음(필수)·기본 `destination` = 축제 장소, `status_url`은 `/api/v1/routes/visit/<id>`.
- 귀가 ID를 가는 길 주소로 조회하면(또는 반대) 404 `ROUTE_REQUEST_NOT_FOUND`.
- **확인:** `origin:{query:"서울역"}`만 보내면 202 · 조회 2회차 `ready`·`direction=="visit"`·`destination.type=="festival"` · 귀가 ID를 visit 주소로 조회 → 404.

## 3. 챗봇 작업·인증 (3단계)

### R14. A06 `POST /api/v1/assistant/query` (결과 조회는 `GET /api/v1/assistant/runs/{run_id}`)
- 본문: `request_id`(8~64자), `message`(1~500자), `conversation_id`(선택, `^cv_[0-9A-Za-z]{6,26}$`), `context{festival_id?, route_request_id?}`(형식만 검사), `reference_date`(선택, `YYYY-MM-DD`).
- `conversation_id`를 보냈는데 저장소에 없으면 **403 `FORBIDDEN`**(남의 대화로 취급). 없으면 새로 `cv_`+16자를 만든다.
- 멱등은 R11-4와 같음(같은 본문 → 같은 `run_id`, 다른 본문 → 409).
- **202** `{run_id:"run_"+16자, conversation_id, run_status:"queued", status_url:"/api/v1/assistant/runs/<id>", events_url:"…/events", run_access_token:"rat_"+24자, retry_after_s:1, is_mock:true}`
- **확인:** `POST /api/v1/assistant/query` 202·모든 칸 있음 · 옛 주소 `POST /api/v1/assistant/runs`는 405 또는 404 · `message:""` 422 · 없는 `conversation_id` 403 · 같은 `request_id`·같은 본문 → 같은 `run_id` · 다른 본문 409.

### R15. A06-1 `GET /api/v1/assistant/runs/{run_id}`
- 헤더 `X-Run-Access-Token` 필수: 없으면 401 `UNAUTHORIZED`, 다른 작업 토큰 403 `FORBIDDEN`, 없는 ID 404 `RUN_NOT_FOUND`. 항상 200.
- 조회 1회차 `running`, 2회차부터 최종 상태. 최종 상태는 질문(`message`)으로 정한다.

| `message`에 들어 있는 말 | 최종 상태 |
|---|---|
| `실패` | `failed`, `error{code:"AI_AGENT_FAILED", message:"답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요.", retryable:true}`, `used_tools:[{tool:"request_return_route", ok:false, error_code:"TOOL_TIMEOUT"}]` |
| `귀가`·`돌아가`·`가는 길` | `succeeded`, `answer:"경로를 찾았어요. 귀가 화면에서 확인하세요."`, **A04를 `sync_ready`와 같은 결과로 실제로 하나 만들어** `route_request_id`·`route_access_token`을 넣음(그 토큰으로 A05 조회가 `ready`), `evidence:[{type:"route", ref:<route_request_id>, provider:"mock_adapter", queried_at}]`, `used_tools:[{get_festival ok}, {request_return_route ok}]` — 축제는 `context.festival_id`, 없으면 `fst_000001` |
| 그 밖 | `succeeded`, `answer:"이번 주 서울에서 열리는 축제는 광화문 겨울빛 축제예요.(모의)"`, `used_tools:[{tool:"search_festivals", ok:true, error_code:null}]`, `evidence:[{type:"festival", ref:"fst_000001", provider:"tourapi", queried_at}]` |

- 본문 칸: `run_id, conversation_id, run_status, run_kind:"chat", answer, used_tools, evidence, result:null, route_request_id, route_access_token, error, queued_at, started_at, ended_at, is_mock`. **`answer`에는 경로 구간·정류장 내용을 넣지 않는다.**
- **확인:** 1회차 `running`·`answer is None` · 일반 질문 2회차 `succeeded` · "실패" 2회차 `failed`·`error.code=="AI_AGENT_FAILED"` · "귀가" 2회차의 `route_request_id`·`route_access_token`으로 A05 → 200 `ready` · 토큰 없음 401 · 다른 토큰 403 · `run_zzzzzzzz` 404.

### R16. A32~A35 가짜 인증 (`/api/v1/auth/*`, 메모리 저장)
| API | 요청 | 성공 | 실패 |
|---|---|---|---|
| A32 `POST /signup` | `{email, password, display_name, birth_year, gender}` 모두 필수. 이메일 형식·254자 이하(소문자로 바꿔 비교), 비밀번호 8~64자·영문과 숫자 모두 포함, 닉네임 앞뒤 공백 제거 후 2~12자, 출생연도 1900~올해, 성별 `male`·`female` | **201** `{user_id(UUID), display_name, is_mock}` | 422 / 409 `EMAIL_ALREADY_EXISTS` / 409 `NICKNAME_TAKEN`(대소문자 무시) |
| A33 `POST /login` | `{email, password}` | 200 `{access_token:"mock_at_"+32자, token_type:"bearer", expires_in:1800, refresh_token:"mock_rt_"+32자, refresh_expires_at, user{user_id, display_name, role:"user"}, is_mock}` | 401 `INVALID_CREDENTIALS`(이메일 없음·비밀번호 틀림 구분 안 함) |
| A34 `POST /refresh` | `{refresh_token}` | 200 A33과 같은 모양, **새 refresh_token**(옛 것은 폐기) | 401 `REFRESH_INVALID`(모름) / 401 `REFRESH_REUSED`(폐기된 것을 다시 씀 → 그 사용자 refresh 전부 폐기) |
| A35 `POST /logout` | 헤더 `Authorization: Bearer <access>` + `{refresh_token}` | **204** | 401 `UNAUTHORIZED`(토큰 없음·모름·이미 로그아웃한 access) |

- 비밀번호는 메모리에도 원문으로 두지 않고 `hashlib.pbkdf2_hmac('sha256', …)` + 임의 salt로 둔다. 로그·응답에 비밀번호·토큰 원문을 찍지 않는다.
- **확인:** 가입 201 · 같은 이메일(대문자 섞어) 409 `EMAIL_ALREADY_EXISTS` · 닉네임 `Abc`/`abc` 409 `NICKNAME_TAKEN` · 닉네임 1자 422 · `birth_year:2100` 422 · 비밀번호 숫자만 422 · 로그인 200 · 틀린 비밀번호 401 · refresh → 새 토큰 · 옛 refresh 다시 → 401 `REFRESH_REUSED` 그리고 새 토큰도 401 · logout 204 · 같은 access로 다시 logout 401.

## 5. 축제 주변 정보·관심 축제 (5단계)

### R18. 외부 데이터 조회 공통 (A07·A09·A10, API 설계문서 6-2-0)
- 경로 `festival_id` 형식 422 → 축제 없음 **404 `FESTIVAL_NOT_FOUND`** → 축제 좌표가 없으면(`fst_000006`) **200 + `status:"unavailable"` + `error{code:"FESTIVAL_LOCATION_UNKNOWN", message, retryable:false}`** → 그 지역에 공급원이 없으면 **200 + `status:"unsupported"`**.
- 응답 공통 칸: `festival_id, status(ok·stale·unavailable·unsupported·unverified), coverage{scope, region_code, supported}, source, observed_at, notices[], is_mock` + API별 `items`/`data`/`areas`.
- 외부 공급원 오류는 HTTP 오류가 아니라 **200 + `status:"unavailable"` + `error{code:"SOURCE_RESULT_ERROR", retryable:true}`**.
- 시나리오 헤더 `X-Mock-Scenario`: 없으면 `ok`, `stale`(값은 주되 `status:"stale"`, `notices`에 "정보가 오래됐어요"), `source_error`(위 공급원 오류). 그 밖의 값 422. (A07·A09·A10 모두 같음, 좌표 없음·지역 미지원이 시나리오보다 먼저)
- **확인:** `fst_999999` 404 · `fst_000006` 200 `unavailable`·`error.code=="FESTIVAL_LOCATION_UNKNOWN"` · `source_error` 200 `unavailable`·`SOURCE_RESULT_ERROR` · `stale` 200 `status=="stale"` · 알 수 없는 시나리오 422.

### R19. A07 공지·통제 `GET /api/v1/festivals/{festival_id}/notices`
- 쿼리 `type`(선택: `operation`·`traffic_control`·`no_stop`·`bus_detour`·`road_closure`, 그 밖 422), `active_only`(bool, 기본 true).
- 가상 공지(`api/mocks/notices.py`), 모두 승인된 것. `fst_000001`만 3건:
  - `ntc_000001` `traffic_control` "세종대로 일부 차로 통제" 효력 2026-11-20T18:00+09:00 ~ 2026-12-31T23:00+09:00, `source:"seoul_topis"`, `control_version:"ctl-0001"`
  - `ntc_000002` `operation` "점등 시간 18:00~23:00 안내" 효력 2026-11-20T00:00+09:00 ~ 2026-12-31T23:59+09:00, `source:"operator"`, `control_version:null`
  - `ntc_000003` `bus_detour` "지난 우회 운행 안내(종료)" 효력 2026-11-01 ~ 2026-11-10(끝남), `source:"operator"`
  - 다른 축제는 0건 → `status:"ok"`, `items:[]`, `notices:["확인할 수 있는 공지 자료가 없어요"]`
- "지금"은 **2026-11-22T12:00:00+09:00로 고정**(`api/mocks/clock.py`의 `MOCK_NOW`)해서 시험이 날짜에 따라 바뀌지 않게 한다.
- `items[]`: `notice_id, type, title, content, effective_from, effective_to, source, source_url, published_at, control_version`. 정렬 `effective_from` 내림차순.
- 공지는 서울 TOPIS(서울만)+운영자 등록(전국) → `coverage.scope:"national"`, 좌표 없어도 됨(공지는 좌표 불필요 — `fst_000006`도 200 `ok` 0건).
- **확인:** `fst_000001` 기본 2건(끝난 `ntc_000003` 제외) · `active_only=false` 3건 · `type=traffic_control` 1건 · `fst_000003` 0건+안내 · `fst_000006` 200 `ok` · `type=parade` 422.

### R20. A09 날씨 `GET /api/v1/festivals/{festival_id}/weather`
- `data`: `{observed_at:"2026-11-22T11:00:00+09:00", temperature_c, precipitation_mm, precipitation_type, grid{nx, ny}, forecast:{status:"unverified"}}`.
- 가상 값: SEOUL → grid 60,127, 4.5℃, 0.0mm, `none` / BUSAN → 97,74, 9.0℃, 0.0mm, `none` / GANGWON → 84,123, -3.0℃, 0.5mm, `snow`. `source:"kma"`, `coverage.scope:"national"`.
- `precipitation_type` 허용값: `none`·`rain`·`rain_snow`·`snow`·`drizzle`·`drizzle_snow`·`snow_flurry`.
- **확인:** `fst_000001` grid 60,127 · `fst_000003` grid 97,74 · `fst_000005` `snow` · `forecast.status=="unverified"` · `fst_000006` `unavailable`.

### R21. A10 혼잡 구역 `GET /api/v1/festivals/{festival_id}/crowd` (서울만)
- 서울 밖 → `status:"unsupported"`, `coverage{scope:"seoul_only", region_code, supported:false}`, `areas:[]`, `notices:["이 지역은 아직 지원하지 않아요"]`.
- 서울인데 검증된 구역 연결이 없으면(`fst_000002`) → `unsupported`, `coverage.supported:true`, `notices:["이 축제는 검증된 혼잡 구역 연결이 없어요"]`. **근처 아무 구역이나 붙이지 않는다.**
- `fst_000001` → `ok`, `areas` 1개: `{area_code:"POI009", area_name:"광화문·덕수궁", relation_type:"contains", congest_level:"보통", congest_color:"yellow", congest_message:"사람이 몰려 있을 수 있지만 크게 붐비지는 않아요.(모의)", population_min:48000, population_max:50000, observed_at:"2026-11-22T11:55:00+09:00", forecast:[3개 {time, congest_level, population_min, population_max}]}`. `source:"seoul_citydata"`.
- 색 규칙: `여유`→`green`, `보통`→`yellow`, `약간 붐빔`→`orange`, `붐빔`→`red`. 성별·연령 비율 칸은 응답에 넣지 않는다.
- 좌표 없음 검사가 지역 검사보다 먼저(`fst_000006` → `unavailable`).
- **확인:** `fst_000001` `ok`·`congest_color=="yellow"`·`forecast` 3개 · `fst_000002` `unsupported`·`supported is True` · `fst_000003` `unsupported`·`supported is False` · 응답 어디에도 `MALE`·`rate` 글자가 든 키 없음.

### R22. A11~A13 관심 축제 (로그인 필요, 3단계 가짜 인증 재사용)
- 헤더 `Authorization: Bearer <A33 access_token>` 필수. 없음·모름·로그아웃한 토큰 → **401 `UNAUTHORIZED`**. 사용자는 **토큰으로만** 정한다(경로·본문으로 받지 않음).
- A12 `PUT /api/v1/me/favorites/{festival_id}`: 처음 저장 **201** `{festival_id, saved_at, is_mock}`, 이미 있으면 **200** 같은 본문(같은 `saved_at`). 축제 없음 404 `FESTIVAL_NOT_FOUND`, 형식 422.
- A13 `DELETE /api/v1/me/favorites/{festival_id}`: **204**(없던 것을 지워도 204). 형식 422.
- A11 `GET /api/v1/me/favorites`: `page`·`page_size`(1~100, 기본 20), `sort`(`-saved_at` 기본·`start_date`). 200 `{items[{festival_id, name, region_code, start_date, end_date, event_status, thumbnail_url, saved_at}], total, page, page_size, is_mock}`.
- 저장 시각은 같은 초에 여러 개를 저장해도 순서가 정해지게 순번을 같이 둔다.
- **확인:** 토큰 없이 A11 401 · A12 처음 201 다시 200(같은 `saved_at`) · A11 total 1 · 사용자 B는 A의 관심을 못 봄(total 0) · A13 204 두 번 다 204 · A13 뒤 A11 total 0 · `fst_999999` A12 404 · 로그아웃한 토큰 401.

## 4. 문서

### R17. `backend/api/MOCK_API.md`
- 실행·시험 명령, 주소 목록(A01·A02·A03·A04·A05·A25·A06(`POST /assistant/query`)·A06-1·A07·A09·A10·A11~A13·A32~A35), `X-Mock-Scenario` 값 표, 가상 축제 6건 표, "모든 값은 가상이며 `is_mock:true`" 안내, 화면·에이전트 팀이 쓰는 예시 `curl` 3개(축제 목록, 귀갓길 접수→조회, 챗봇 접수→조회).
- **확인:** 파일이 있고 위 항목 제목이 모두 있음(시험 `test_R17_mock_doc`가 제목 문자열 확인).
