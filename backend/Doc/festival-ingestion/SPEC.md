# SPEC — 축제 실제 수집(TourAPI) → DB 저장 → A02·A03 실제 조회

- 기준: DB 스키마 설계서 v0.3.3(5절 `festivals`·`festival_sources`·`ingestion_jobs`·`festival_change_history`·`data_sources`), API 설계문서 v0.3.3(0-1 지역 코드, 2-4 A02·A03, 10절 TourAPI). **이 SPEC에 필요한 것을 옮겨 두었으니 구현 때 설계서 전체를 읽지 않는다.** 다른 점은 `IMP-PLAN.md` '메모'에 적는다.
- 요구 번호는 `I1`~. 시험 이름에 번호를 넣는다(예: `test_I4_region_merged_gwangju`).
- 명령은 `backend/`에서. 시험: `uv run --offline --with-requirements api/requirements.txt pytest tests/ingestion tests/api -q`.
- import 기준 `backend/` (`from api.providers.tourapi import …`).

## 0. 실제 데이터에서 확인한 것 (11/23 Claude 실호출, 2026-01-01 이후 시작 870건)
| 항목 | 결과 | 반영 |
|---|---|---|
| 지역 | `areacode`는 거의 비어 있음(860/870). **`lDongRegnCd`**로 판단. 값: 11·26·27·28·30·31·**36110**(세종)·41·43·44·47·48·50·**51**(강원특별자치도)·**52**(전북특별자치도)·**12**(전남광주통합특별시) | I4 |
| `12` 전남광주통합특별시 | 광주 구(동구·서구·남구·북구·광산구, `lDongSignguCd` 200~399)와 전남 시·군이 섞임 | I4 (임시 규칙, 팀 확인 필요) |
| 좌표 | 모두 있음. **1건 한국 밖**(lat 19.69, lng 117.99) | I5 |
| 날짜 | 모두 `YYYYMMDD`, 끝 < 시작 0건 | I5 |
| 이미지 | 없음 6건, 있으면 `cpyrhtDivCd=Type3`(864건) | I5 |
| 소개 | `detailCommon2.overview`(HTML `<br>` 섞임) | I6 |
| 장소·입장료·시간·주최 | `detailIntro2.eventplace`·`usetimefestival`·`playtime`·`sponsor1`, 홈페이지는 `eventhomepage` 또는 `detailCommon2.homepage`(HTML `<a href>`일 수 있음) | I6 |
| 오류 | 틀린 키 → **HTTP 403** + 본문 `OpenAPI_ServiceResponse.cmmMsgHeader.errMsg = SERVICE_KEY_IS_NOT_REGISTERED_ERROR`(11/23 확인). 정상 응답이라도 본문 `header.resultCode != "0000"`이면 오류 | I2 |

## 1. TourAPI 클라이언트 (1단계) — `api/providers/tourapi.py`
### I1. 설정
- 키: 환경변수 **`DATA_GO_KR_SERVICE_KEY`**(없으면 `TourApiError("NO_KEY")`). 이미 `%`가 들어 있으면(인코딩된 키) 그대로, 아니면 URL 인코딩해서 `serviceKey`에 붙인다.
- 기본 주소 `https://apis.data.go.kr/B551011/KorService2/`. 공통 쿼리 `MobileOS=ETC`, `MobileApp=noldaga`, `_type=json`.
- `httpx2.Client`를 생성자에서 받을 수 있게 한다(시험은 `httpx2.MockTransport`). 요청 1회 제한 **10초**, 연결 오류·시간 초과·5xx는 **1번만** 다시 시도.
- **키가 로그·예외 메시지·repr에 나오지 않는다**(URL을 남길 때 `serviceKey=***`).
- **확인:** 키 없음 → `NO_KEY` · MockTransport로 받은 요청 URL에 키가 있고, 예외 메시지·`repr(client)`에는 키 문자열이 없음 · 5xx 한 번 뒤 성공 → 결과 정상 · 5xx 두 번 → `TourApiError("HTTP_ERROR")`.

### I2. 함수
| 함수 | 부르는 것 | 돌려주는 것 |
|---|---|---|
| `search_festivals(start: date, end: date|None=None, page_size=100) -> list[dict]` | `searchFestival2` `eventStartDate`(·`eventEndDate`), `arrange=A`, **`totalCount`까지 모든 페이지** | 원본 `item` 목록 |
| `get_common(content_id) -> dict` | `detailCommon2` `contentId` | 원본 1건 |
| `get_intro(content_id) -> dict` | `detailIntro2` `contentId`, `contentTypeId=15` | 원본 1건 |
- 본문 `response.header.resultCode != "0000"` 또는 JSON이 아님(XML 오류 본문 포함) → `TourApiError(code="RESULT_ERROR", detail=<resultMsg 또는 원문 앞 200자, 키 제거>)`.
- HTTP 4xx는 다시 시도하지 않는다. 본문에 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`·`SERVICE_KEY`가 있으면 `TourApiError("KEY_ERROR")`, 그 밖 4xx는 `HTTP_ERROR`.
- `items`가 `""`(빈 결과)이면 빈 목록. `item`이 dict 하나면 목록으로 감싼다.
- 호출 횟수를 `client.calls`(기능별 dict)로 센다(한도 관리용).
- **확인:** 3페이지 고정 응답(총 250건, page_size 100) → 250건·`calls["searchFestival2"]==3` · 빈 `items` → [] · `resultCode="30"` → `RESULT_ERROR` · XML 본문 → `RESULT_ERROR` · `fixtures/error_key.txt`를 403으로 → `KEY_ERROR`, 다시 시도 0회.

## 2. 정규화·검사 (1단계) — `api/ingestion/festivals/normalize.py`
### I3. 출력 모양 `FestivalRecord`(dataclass 또는 pydantic)
`source_item_id`(contentid), `title`, `start_date`, `end_date`, `venue_name`, `address`, `latitude`, `longitude`, `region_code`, `category`, `summary`, `admission_fee_text`, `image_url`, `thumbnail_url`, `image_copyright_type`, `official_url`, `organizer`, `event_status`, `source_updated_at`, `review_status`, `publishable: bool`, `issues: list[str]`, `raw_checksum`.

### I4. 지역 코드 (`lDongRegnCd` → API 0-1 코드)
| 값 | 코드 | 값 | 코드 | 값 | 코드 |
|---|---|---|---|---|---|
| 11 | SEOUL | 26 | BUSAN | 27 | DAEGU |
| 28 | INCHEON | 29 | GWANGJU | 30 | DAEJEON |
| 31 | ULSAN | 36110 · 36 | SEJONG | 41 | GYEONGGI |
| 42 · 51 | GANGWON | 43 | CHUNGBUK | 44 | CHUNGNAM |
| 45 · 52 | JEONBUK | 46 | JEONNAM | 47 | GYEONGBUK |
| 48 | GYEONGNAM | 50 | JEJU | **12** | `lDongSignguCd` 200~399 → **GWANGJU**, 그 밖 → **JEONNAM** |
- 모르는 값이면 `areacode`(1 서울, 2 인천, 3 대전, 4 대구, 5 광주, 6 부산, 7 울산, 8 세종, 31 경기, 32 강원, 33 충북, 34 충남, 35 경북, 36 경남, 37 전북, 38 전남, 39 제주)로 한 번 더 보고, 그래도 모르면 `region_code=None` + issue `region_unknown`.
- **확인:** 11→SEOUL · 36110→SEJONG · 51→GANGWON · 52→JEONBUK · 12+210→GWANGJU · 12+130→JEONNAM · 99+areacode 6→BUSAN · 99+빈 areacode→issue.

### I5. 값 규칙
- 날짜 `YYYYMMDD` → `date`. 형식이 틀리면 None + issue `date_invalid`. 끝 < 시작이면 둘 다 None + `date_invalid`.
- 좌표: `mapy`=위도, `mapx`=경도(**순서 주의**). 위도 33~39, 경도 124~132 밖이면 둘 다 None + issue `coords_out_of_range`. 소수 6자리 반올림.
- 이미지: `firstimage`→`image_url`, `firstimage2`→`thumbnail_url`(빈 문자열은 None). `image_url`이 있으면 `image_copyright_type=cpyrhtDivCd`(Type1/Type3만, 그 밖이면 이미지 세 칸 None + issue `image_copyright_unknown`). 이미지 없으면 세 칸 None(issue 아님).
- `event_status`(KST 오늘 기준 `today` 인자로 받음): 날짜 없음 → `needs_review` · 오늘 < 시작 → `upcoming` · 오늘 > 끝 → `ended` · 그 밖 `ongoing`.
- `source_updated_at` = `modifiedtime`(`YYYYMMDDHHMMSS`, KST).
- `category = "festival"`.
- `raw_checksum` = 목록·상세 원본 3개를 키 정렬 JSON으로 합친 sha256(16진수).
- **확인:** 각 규칙 1개씩 + 실제 고정 파일의 한국 밖 좌표 1건 → None·issue.

### I6. 상세 칸
- `summary` = `overview`에서 HTML 태그 제거·`<br>`→줄바꿈·연속 빈 줄 1개로, 앞뒤 공백 제거, 최대 2,000자.
- `venue_name` = `eventplace`(비면 None), `address` = `addr1` + (`addr2`가 있으면 " " + addr2).
- `admission_fee_text` = `usetimefestival` 정리(태그 제거, 비면 None). **원문을 바꾸지 않는다**(요약·가공 금지).
- `official_url` = `eventhomepage` → 없으면 `homepage`. HTML이면 첫 `href` 값, `http(s)://`로 시작하지 않으면 None.
- `organizer` = `sponsor1`(비면 None).
- 상세를 못 받았으면(오류) 해당 칸 None + issue `detail_missing`(축제는 남김).
- **확인:** `<br>` 섞인 소개 정리 · `<a href="https://x">` → `https://x` · 빈 입장료 → None.

### I7. 공개 판정
- `publishable = True` 이고 `review_status="approved"`: 제목 있음 · 날짜 있음 · 좌표 있음 · `region_code` 있음.
- 그 밖: `publishable=False`, `review_status="pending"`(지도·목록에 안 나옴, 관리자 검토 대기). 이유는 `issues`에.
- **확인:** 정상 → approved · 좌표 밖 → pending + `coords_out_of_range` · 날짜 없음 → pending + `needs_review` 상태.

## 3. 수집 실행기 (1단계) — `api/ingestion/festivals/collect.py`
### I8. 명령
`uv run --with-requirements api/requirements.txt python -m api.ingestion.festivals.collect --since 2026-01-01 [--until YYYY-MM-DD] [--limit N] --out <폴더> [--no-detail]`
- 순서: 목록 전체 → (상세 2종, `--no-detail`이면 생략) → 정규화·검사 → `<out>/festivals.jsonl`(1줄 1건, `FestivalRecord`) + `<out>/report.json`.
- `report.json`: `{started_at, ended_at, since, until, scanned, publishable, pending, issues:{코드: 건수}, calls:{기능: 횟수}, errors:[{content_id, stage, code}]}`. **키·원본 전체는 넣지 않는다.**
- 상세 호출 하나가 실패해도 전체는 계속(issue `detail_missing`). 목록 호출이 실패하면 종료 코드 1.
- 한도 보호: 상세 호출이 **기능별 900회**에 닿으면 남은 축제는 `--no-detail`처럼 처리하고 보고서에 `detail_skipped_quota` 건수.
- **확인:** MockTransport + 고정 파일로 실행 → jsonl 줄 수 = 고정 목록 수 · report 숫자 일치 · 상세 1건 실패 → 계속 진행·errors 1건 · 출력 파일 어디에도 키 문자열 없음.

## 4. DB 저장 (2단계) — `api/ingestion/festivals/store.py`, `api/ingestion/db.py`
### I9. 연결 (`api/ingestion/db.py`, 유빈 님 `shared/db/session.py` 전까지 임시)
- SQLAlchemy 2 + psycopg 3(D1 결정). 엔진 생성은 **이 파일 한 곳**. 수집은 서버 내부 작업이므로 **`noldaga_service`** 계정.
- 환경변수: `DB_HOST`(기본 `127.0.0.1`), `DB_PORT`(5432), `DB_NAME`(`noldaga`), `DB_SERVICE_PASSWORD`(D1에서 정한 이름). 사용자 이름은 `noldaga_service` 고정.
- **확인:** 환경변수로 URL이 만들어지고 비밀번호가 `repr(engine.url)`에 나오지 않음.

### I10. 업서트 (한 수집 = 트랜잭션 하나는 아님: 축제 1건마다 저장점(savepoint), 1건 실패가 전체를 막지 않음)
1. 시작: `data_sources`에 `tourapi` 행이 없으면 넣음 → `ingestion_jobs`(`job_id="ij_"+ULID`, status `running`).
2. 축제마다 `festival_sources`(`source_id='tourapi'`, `source_item_id=contentid`)로 찾기:
   - 없으면: `festivals` 새 행(`festival_id="fst_"+ULID`), `festival_sources` 새 행 → inserted
   - 있고 `raw_checksum` 같으면: `last_synced_at`·`fetched_at`·`last_job_id`만 갱신 → 변경 없음
   - 있고 체크섬 다르면: 바뀐 칸만 UPDATE + 칸마다 `festival_change_history`(`actor='ingestion'`, before/after JSONB) → updated
   - 공개 판정: `approved`면 `published_at`이 비어 있을 때만 지금 시각, `pending`이면 `published_at=NULL`. **관리자가 `hidden`으로 바꾼 축제는 수집이 다시 공개하지 않는다.**
3. 끝: `ingestion_jobs` 건수(scanned·inserted·updated·rejected)·`ended_at`·status(`success` / 오류 있으면 `partial` / 목록 실패면 `failed`)·`error`(JSONB, 키 없음).
- **확인(DB 시험, `pytest -m db`, 환경변수 없으면 건너뜀 — Claude가 로컬 도커로 실행):** 첫 저장 → inserted N · 같은 입력 재실행 → inserted 0·updated 0·축제 수 그대로 · 제목 바꾼 입력 → updated 1·history 1행 · `hidden` 축제는 재수집 뒤에도 `hidden` · `ingestion_jobs` 2행 · `festival_id` 재실행 뒤 같음.

### I11. 바뀐 축제만 상세 다시 받기
- `collect --db`: 목록을 받은 뒤 DB의 `festival_sources`와 비교해, **목록 `modifiedtime`이 저장된 `source_updated_at`보다 새롭거나 새 축제일 때만** 상세 2종을 부른다. 나머지는 저장된 상세 칸을 그대로 쓴다.
- **확인:** 두 번째 실행에서 바뀐 1건만 상세 호출(`calls["detailCommon2"]==1`).

## 5. A02·A03 실제 조회 (3단계) — `api/routers/festivals/catalog.py` + `api/services/festival_store.py`
### I12. 데이터 출처 고르기
- 환경변수 **`FESTIVAL_DATA=mock|db`**(기본 `mock`). `db`면 DB에서, `mock`이면 지금 모의 그대로. **주소·쿼리 규칙·응답 칸은 R7·R8과 같다.**
- `db`일 때: 사용자 요청이므로 **`noldaga_app`** 계정(`DB_USER_PASSWORD`), 요청마다 트랜잭션, 비회원은 `app.user_id`를 설정하지 않음(D1). 공개 축제만(`review_status='approved' AND published_at IS NOT NULL`).
- 응답 칸 대응: `name←title`, `lat/lng←latitude/longitude`, `overview←summary`, `fee_text←admission_fee_text`, `homepage_url←official_url`, `source="tourapi"`, `source_ref←festival_sources.source_item_id`, `image_credit`·`image_copyright`는 R6 규칙(이미지 있으면 "한국관광공사"). `is_mock: false`, 헤더 `X-Mock` 없음.
- `event_status`는 **조회 시점 KST 오늘로 다시 계산**(저장 값이 어제 기준일 수 있음).
- **확인:** `FESTIVAL_DATA=mock` → 기존 시험 전부 그대로 통과 · DB 시험(`-m db`): 시험용 축제 3건 저장 후 A02 total 3·`region` 필터·`q` 검색·`pending` 축제 안 보임·A03 `is_mock is False`·없는 ID 404.

## 6. 시험 고정 파일 (1단계) — `tests/ingestion/fixtures/`
- Claude가 11/23 실제 응답에서 골라 **키 없이** 넣어 둔다: `search_page1.json`(5건: 3379778 서울·2536122 부산·292950 `12` 광주 남구·3486674 `12` 전남 강진군·2865122 한국 밖 좌표), `common_<id>.json`·`intro_<id>.json`(5건), `error_key.txt`(틀린 키 403 응답 본문), `empty.json`.
- Codex는 이 파일을 **고치지 않는다**. 더 필요한 모양은 시험 안에서 dict로 만든다.
