# 03. API 설계 문서

놀다가(NOLDAGA) / 3팀 수다수다 | 문서 버전 **v0.3.1** | 작성 상태: **팀 검토 반영본(11/20 제출 대상)** | 작성 2026-11-17 · 수정 2026-11-19 · 권오현(백엔드) — AI 초안 후 본인 검토

문서명: REST API 및 Function Calling 명세서

## 문서 정보

| 항목 | 내용 |
|---|---|
| **정본(이 문서의 기준 위치)** | GitHub `yubeenjjang/Final3team` → `Docs/Step 2/API_설계문서.md`. **이 경로만 정본**이며 로컬 파일·Discord 첨부는 사본입니다. 대시보드 제출 링크도 이 경로를 씁니다 |
| 짝 문서 | `Docs/Step 2/DB_스키마_설계서.md` (같은 ID 형식·필드↔컬럼 대응은 16절) |
| 기준 문서 | **기획서 최신본(11/19 05:18 신유빈 님 공유, v3.1 다음판 — `받은자료/2026-11-19_신유빈_기획서_최신본_0518.md`)** · 기획서 v3.1(11/19 정예진) · WBS 128개(필수 118, W112~W128 신규), 결정대장 D-009~D-036(팀 회의·멘토 2차 회의·11/19 사용자 결정), 팀 자체 평가 30문항(한다영, 11/18, 이하 BFCL), 17개 시·도 데이터 조사, 강사 2차 의견(11/18)·일일 피드백(11/19), 수업 가이드 「API 설계 문서 작성법」(11/18) |
| 진행 단계 | ☑ 초안 작성(11/19) → ☑ 팀 검토 완료(11/19 신유빈·정예진) → ☐ GitHub 정본 업로드 → ☐ 대시보드 제출(링크·상태 `제출완료`) |
| 범위 | **메인 기능만**: 전국 축제 탐색 + AI 안심 귀가 + 귀가 조회 장애 자동 복구. 서비스 부가 기능(축제 즐기기, D-026)은 아직 정하지 않았고 14절 '확장 지점'에 들어올 자리만 둡니다 |
| 실제 호출 근거 | 서울 실시간 인구(11/16) + **11/19 한태경 님 실호출 10종**(TourAPI·기상청·TAGO·서울 지하철·주차장·TOPIS·문화행사 등, 10절). **길찾기(TMAP·카카오맵)는 아직 미호출**입니다 |

> **이 문서의 모든 API는 설계안입니다.** 구현·외부 공급원 연동·배포가 끝났다는 뜻이 아닙니다. 미확인 항목은 11절, 기획서와 다른 점은 15절, 바뀐 점은 맨 아래 '변경 이력'에 있습니다.

### 검토 기록

| 일자 | 검토자 | 범위 | 결과·수정 내용 |
|---|---|---|---|
| 2026-11-19 | 권오현 (AI 초안 작성) | 전체 | v0.3 작성: 강사 피드백·멘토 회의·D-033~D-036·수업 가이드 반영 |
| 2026-11-19 | AI 교차 검토(Gemini 4 Neon) | 전체 | 25건 지적 → 내부 모순·BFCL 생략 인자·오류 코드 등 반영. 남은 것(1차 필수 API 일부의 상세·필드 표, 도구 6개 JSON Schema)은 v0.4로 '상세 명세 작성 범위' 표에 기록 |
| 2026-11-19 | 신유빈(인프라·R06 검토) | 전체 | 검토 완료. 변경 이력 정리·택시 범위·추적 ID·최신 기획서 대조·신규 기능(v0.4) 표기 요청 → 반영 |
| 2026-11-19 | 정예진(기획) | 기획서와 대조 | 6건(경로 5유형 이름, 택시 범위, created, 대조표, 추적 ID, 카카오 비동기) → 반영 |

### 공통 정보

| 항목 | 내용 |
|---|---|
| 개발 서버 | `http://localhost:8000/api/v1` |
| 배포 서버 | **미정** (배포 환경 결정 후 기입, 12/24 웹 앱 마감 전) |
| 자동 문서 | `<서버 주소>/docs`(Swagger UI), `<서버 주소>/openapi.json` — FastAPI가 생성. 구현 후 이 문서와 대조하고, 다르면 문서 버전을 올립니다 |
| 인증 | `Authorization: Bearer <JWT>` (1절) |
| 오류 형식 | 모든 API 공통 (0절) |
| 시각 | ISO 8601 + `+09:00`(KST) |

---

## 0. 설계 원칙 (모든 API 공통)

| 원칙 | 내용 | 근거 |
|---|---|---|
| 내부 API와 외부 공급원 분리 | 화면·에이전트는 **놀다가 내부 API만** 부릅니다. 외부 API(TourAPI·TMAP·카카오·서울시·TAGO·경찰청 등)는 백엔드 어댑터만 호출합니다. 축제 목록은 수집된 DB에서 제공하고 요청마다 외부 API를 부르지 않습니다 | 기획서 5.12 |
| 접수 ≠ 완료 | `queued`·`accepted`는 경로 제공 성공이 아닙니다. 검증을 통과한 경로가 응답에 담길 때만 `ready` | FR-R14, FR-H24 |
| 모의/실제 구분 | 시험용 경로 어댑터·장애 주입으로 만든 응답은 항상 `is_mock=true`, `test_mode` 표기 | 기획서 3.6, 5.17 |
| 출처·시각 표시 | 외부 데이터가 들어간 응답에는 `provider`(또는 `source`), `queried_at`/`observed_at` 필수 | FR-R08, FR-C06 |
| **지역 지원 범위 표시** | 외부 데이터 응답에는 `coverage`를 넣습니다. 그 지역에 데이터가 없으면 오류가 아니라 `status:"unsupported"`로 돌려주고 화면은 '이 지역은 미지원'으로 표시합니다. 다른 지역 값으로 채우지 않습니다 | D-010·D-016, 데이터 조사 3절 |
| 에이전트는 제안, 코드는 실행 | 복구 조치는 에이전트가 고르고(`select/reject/defer/rollback`) **정책 코드가 allowlist·상한을 검사한 뒤 실행**합니다. 에이전트가 직접 실행하는 도구는 없습니다 | FR-H05, 기획서 6.22 |
| 장애 격리 | 귀가 조회 부하·외부 API 장애·LLM 장애가 축제 검색·상세를 멈추지 않게 엔드포인트와 작업 풀을 분리 | FR-H18, FR-C09, NFR-12 |
| 비밀정보 | 외부 API 키는 서버 환경변수에만 둡니다. 응답·로그·저장소·문서에 노출 금지 | NFR-09 |
| **공급원 어댑터** | 같은 데이터를 주는 공급원(예: 길찾기 1차 TMAP · 2차 카카오맵 · 모의)은 **같은 내부 형식**으로 바꿔 돌려주는 어댑터 뒤에 둡니다. 공급원을 바꿔도 내부 API 응답은 같습니다 | D-029·D-038 |
| **외부 공급원 보호** | 실제 외부 API에는 부하 시험·반복 개발 호출을 하지 않습니다. 개발·부하 시험은 실제 응답 구조를 본뜬 모의 응답만 씁니다(10절 최소 호출 계획) | 강사 일일 피드백 2 |
| **확장 가능** | 지금 문서는 완성본이 아닙니다. 새 서비스 기능은 기존 계약을 바꾸지 않고 API 묶음·도구·테이블을 **추가**하는 방식으로 붙입니다(14절) | D-034 |

**공통 규칙**
- 기본 경로: **`/api/v1`** (수업 가이드 S10. 규격이 깨지게 바뀌면 `/api/v2`를 새로 열고 `v1`은 유지). 경로는 소문자·하이픈, 자원은 복수형 명사. 형식: JSON, UTF-8, 시각은 ISO 8601 + `+09:00`.
- **검증 오류의 경계**: 입력 **형식**(타입·허용값·길이·패턴)은 Pydantic이 검사하고 **422 `VALIDATION_ERROR`**. 형식은 맞지만 서버가 판단해야 하는 것은 따로: 권한·소유권은 **403**, 대상 없음은 **404**, 중복·충돌은 **409**, 해석 불가(목적지를 찾을 수 없음 등)는 **400**. 두 검사를 섞지 않습니다(수업 가이드 S19·S31). FastAPI 기본 422 응답도 공통 오류 형식으로 바꾸는 예외 핸들러를 둡니다.
- **ID 형식(두 문서 공통)**: 모두 `소문자 접두사_` + ULID — `fst_`(축제) · `rr_`(경로 요청) · `inc_`(사건) · `diag_`(진단) · `rp_`(복구 계획) · `ra_`(복구 시도) · `sim_`(부하 시험) · `run_`(에이전트 실행 묶음) · `ar_`(에이전트 1회 실행) · `cv_`(대화 세션, LangGraph `thread_id`) · `rv_`(후기) · `rt_`(Refresh Token). `request_id`(경로 요청 본문의 **멱등 키**)는 UUID. **추적 ID**(`X-Request-ID` 헤더·로그·오류 응답의 `request_id`)는 `req_` + ULID로, 둘은 다른 값입니다. BFCL의 `F01`·`RR02`·`INC-003`은 평가용 가짜 ID입니다(4-7절). **별도 `trace_id`는 도입하지 않습니다** — 추적은 `X-Request-ID`(`req_`) → `run_id` → `agent_run_id` → `route_request_id`·`incident_id`를 이어서 합니다(기획서 최신본과 같음).
- 모든 요청에 `X-Request-ID`(없으면 서버가 생성)를 붙이고, 응답 헤더·로그·에이전트 `run_id`와 연결합니다.
- 목록 API는 `page`(1부터)·`page_size`(기본 20, 최대 100) 사용, 응답에 `total`·`page`·`page_size`.
- 오류 응답 형식(공통):

```json
{ "error": { "code": "ROUTE_TIMEOUT", "message": "경로 조회 시간이 초과됐어요.", "request_id": "req_01JD8Q3K2M", "retryable": true } }
```

- 외부 데이터 응답의 `coverage` 형식(공통):

```json
{ "coverage": { "scope": "seoul_only", "region_code": "BUSAN", "supported": false }, "status": "unsupported", "items": [] }
```

`scope`는 `national`(전국 공통) / `seoul_only`(서울만) / `region_specific`(일부 시·도) 중 하나입니다(13절 표).

### 0-1. 지역 코드

| 코드 | 시·도 | 코드 | 시·도 | 코드 | 시·도 |
|---|---|---|---|---|---|
| `ALL` | 전체(검색 기본값) | `SEOUL` | 서울 | `BUSAN` | 부산 |
| `DAEGU` | 대구 | `INCHEON` | 인천 | `GWANGJU` | 광주 |
| `DAEJEON` | 대전 | `ULSAN` | 울산 | `SEJONG` | 세종 |
| `GYEONGGI` | 경기 | `GANGWON` | 강원 | `CHUNGBUK` | 충북 |
| `CHUNGNAM` | 충남 | `JEONBUK` | 전북 | `JEONNAM` | 전남 |
| `GYEONGBUK` | 경북 | `GYEONGNAM` | 경남 | `JEJU` | 제주 |

- BFCL의 `region="SEOUL"`·`region="ALL"`과 같은 값입니다. TourAPI는 `areaCode`가 아니라 **법정동 시·도 코드 `lDongRegnCd`** 로 지역을 받습니다(11/19 실호출: 서울 11, 부산 26 — 10절).

### 0-2. 서비스 범위 (D-020 멘토님 답변 + D-022 팀 결정, 11/18)

**기준: 전국에 있는 데이터는 전국으로, 지역별로만 있는 데이터는 서울만** 씁니다.

| 구분 | 1차 범위 | 데이터·API |
|---|---|---|
| **전국 공통 데이터** (정적·실시간 모두) | **전국** | 축제 검색·상세(A02·A03, TourAPI·전국문화축제표준데이터), 지도·장소 검색(카카오), 지도 시설 위치(A08), 날씨(A09, 기상청), 버스 도착(A26 버스: **서울 밖은 TAGO, 서울은 서울시 버스도착정보** — 11/19 실호출에서 TAGO 서울 0건), 교통 돌발(A28 경찰청), 길찾기 귀가·가는 길(A04·A05·A25: **1차 TMAP, 2차 카카오맵**, D-038), 방문 집중 예측·지역 수요(A29), 주변 상권(카카오 로컬), 자전거 존(전국 통합 공급원이 확인되면 전국, 아니면 서울만 — D-036) |
| **지역별로만 있는 데이터** | **서울만** | 혼잡 구역(A10, OA-21778 — **지도 표시 + 귀가 근거**), 지하철 실시간 도착(A26 지하철), 공영주차장 빈자리(A27), TOPIS 통제(A07·A28 보강), 서울 문화행사(A02·A03 보강), **버스 차내 혼잡(교통수단 선택 근거, D-033)**, **택시 승강장·자전거 존: 전국 통합 공급원·좌표가 확인되지 않을 때만 서울**(D-036) |
| 부하·장애 시뮬레이션 | 서울 축제 기준 | A20~A22 (멘토님 "실제 시뮬레이션은 서울 기준") |
| 서울 밖 시·도 자체 데이터 (대구 돌발·주차, 대전 축제, 비짓제주 등) | 1차 사용 안 함 | 지역마다 형태가 달라 서울 먼저(멘토님). 나중에 기능별로 확대 |

- 서울만 켜는 데이터는 `data_sources.enabled_region_codes`(04 문서)에 `SEOUL`만 넣어 둡니다. 서울 밖 축제에서 부르면 오류가 아니라 `status:"unsupported"`(`REGION_UNSUPPORTED`)로 답하고, 화면은 '이 지역은 아직 지원하지 않아요'로 표시합니다. 지역을 넓힐 때는 **이 값에 지역을 추가하는 것만으로** 됩니다.
- 그래서 **부산 축제**에서도 축제 정보·지도·날씨·버스 도착·교통 돌발·**귀갓길 안내**는 나오고, 혼잡도·지하철 도착·주차 빈자리만 '미지원'으로 표시됩니다.
- 귀갓길 경로 근거(`evidence`)도 같은 기준입니다: 교통 돌발은 전국, 혼잡 구역·버스 차내 혼잡은 서울만.
- **지역 범위를 정하는 규칙(D-036):** 한 공급원에서 전국을 한 번에 불러올 수 있으면 전국, 지역마다 공급원이 따로면 서울만. 개발은 서울 기준으로 하고, 다른 지역은 표준 입력 형태 + 지역별 전처리로 나중에 붙입니다(D-023).

### 0-3. '확인 불가' 표시 규칙 (강사 일일 피드백 3)

데이터가 없거나 믿을 수 없을 때는 **다른 값으로 채우지 않고** 아래처럼 구분해 표시합니다. 지도에 넣을 수 있다는 것만으로 기능 완료로 보지 않습니다.

| 경우 | 응답 | 화면 문구(초안) |
|---|---|---|
| 서울 한정 데이터를 서울 밖 축제에서 요청 | `status:"unsupported"`, `REGION_UNSUPPORTED` | 이 지역은 아직 지원하지 않아요 |
| 공급원은 있으나 관측 시각이 오래됨(기준: 공급원 갱신 주기의 2배, 임시) | `status:"stale"`, `SOURCE_STALE`, `observed_at` 그대로 | ○분 전 정보라 지금과 다를 수 있어요 |
| 공급원 오류·한도 소진 | `status:"unavailable"`, `SOURCE_HTTP_ERROR` 등 | 지금은 확인할 수 없어요 (공식 안내 링크) |
| 공급원 미확인(아직 실호출·검증 전) | `status:"unverified"` | 준비 중인 정보예요 |
| 모의 데이터 | `is_mock:true` | 시험용 자료 표시 |


---

## 1. 인증 방식

수업 가이드의 네 줄(인증·전달·검증·오류) 기준입니다. **DB는 AWS 위 Docker PostgreSQL, 인증은 FastAPI 자체 JWT**입니다(D-037, Supabase 사용 안 함).

| 항목 | 명세 |
|---|---|
| **인증(발급)** | `POST /api/v1/auth/login`(이메일·비밀번호) → Access JWT(30분, `sub`·`role`·`jti`) + Refresh Token(14일). 갱신은 `POST /api/v1/auth/refresh`(Refresh를 쓸 때마다 새로 발급, 이전 것 폐기), 로그아웃은 `POST /api/v1/auth/logout` (수명은 임시값, 04 문서 4절) |
| **전달** | `Authorization: Bearer <access_token>` |
| **검증** | 서명·만료·발급자 → 로그아웃한 토큰(`revoked:{jti}`) 아닌지 → 역할(`profiles.role`, JWT와 다르면 DB 우선) → 자원 소유권 |
| **오류** | 401 `UNAUTHORIZED`(누구인지 모름: 토큰 누락·만료·폐기) / 403 `FORBIDDEN`(누구인지는 알지만 권한 없음: 역할 부족·타인 자원) |
| **역할** | `anonymous`(비로그인) / `user`(일반 회원) / `operator`(운영자: 사건·지표 조회, 부하 시뮬레이션, 복구 조치 승인) / `admin`(operator 권한 + 축제 데이터 승인·수정) / `service`(백엔드 내부 작업·에이전트 실행용, 외부 노출 없음) |
| **역할 저장 위치** | 역할은 DB `profiles.role`과 서버가 발급한 JWT로만 판단합니다. **요청 본문·대화 내용의 "관리자예요"는 권한으로 인정하지 않습니다** (BFCL NLD-27) |
| **DB 쪽 2차 안전장치** | API 서버는 요청마다 DB에 사용자 ID를 넘기고(`SET LOCAL app.user_id`), DB는 접속 역할·컬럼 권한·RLS로 본인 것만 보이게 막습니다(04 문서 3절) |
| **로그인 없이 쓰는 API** | 축제 목록·상세·공지·시설·지도 표시·날씨·교통·주차·혼잡 조회, 귀가·가는 길 경로 조회·상태 조회, 챗봇 질문 |
| **로그인 필요** | 관심 축제 저장·해제·목록, 후기(Should) |
| **운영자 이상** | `/api/v1/admin/**` 전부 |
| **비로그인 경로 요청 보호** | 상태 조회는 `route_request_id` + 요청 시 발급한 `route_access_token`(짧은 수명, 202 응답에 1회 제공, 로그인 JWT와 다른 토큰)으로 본인만 조회. IP·세션 단위 요청 수 제한 |


---

## 2. 대표 API 상세 명세: `POST /api/v1/routes/return` (AI 안심 귀가 조회)

수업 가이드의 **상세 명세 8칸**(호출 목적·요청 헤더·경로/쿼리·요청 본문·검증/권한·정상 응답·오류 응답·실행 규칙)으로 씁니다.

| # | 칸 | 명세 |
|---|---|---|
| 1 | **호출 목적** | 축제가 끝난 뒤 축제장에서 목적지까지 돌아가는 경로를 요청 (FR-R13 · 1차 시연 필수 · D-009). 호출 주체: 귀가 화면(직접), Route Agent(도구 `request_return_route` 경유) |
| 2 | **요청 헤더** | `Content-Type: application/json`(필수) · `X-Request-ID: req_…`(선택, 없으면 서버 생성) · `Authorization`(선택, 로그인 사용자면) |
| 3 | **경로·쿼리** | 없음 |
| 4 | **요청 본문** | 아래 '요청 필드 명세'와 예시 |
| 5 | **검증·권한** | 형식은 3절 `ReturnRouteRequest`(422). 서버 검사: 축제 존재(404) → 축제 좌표 있음(400 `FESTIVAL_LOCATION_UNKNOWN`) → 목적지 해석(400 `ROUTE_INVALID`) → 같은 `request_id`면 같은 결과, 본문이 다르면 409. 인증 없음(anonymous 허용), 요청 수 제한(429) |
| 6 | **정상 응답** | `200` 제한 시간 안에 끝남(`ready` 또는 `unavailable`) / `202` 아직 처리 중(`queued`·`processing`, 상태 조회 URL·짧은 수명 `access_token` 제공) |
| 7 | **오류 응답** | 아래 '오류 응답 표' |
| 8 | **실행 규칙** | **동기 대기 3초**(넘으면 그때까지의 상태로 202 반환, 처리는 계속) · **전체 처리 제한 10초**(넘으면 `route_status=timed_out` — 202 뒤에는 A05로 확인, 3초 안에 판정되면 504) (모두 임시) · 길찾기 어댑터 1회 호출 5초(임시) · 1차 공급원 실패(시간 초과·429·5xx)면 **2차 공급원으로 1회** · 400/404/409/422는 재시도 없음 · 같은 `request_id`는 처음 만든 `route_request_id`를 돌려줌(멱등) · 9절 |

**처리 순서:** ① 축제 존재·좌표 확인 → ② 목적지 확인(좌표 또는 카카오 장소 검색) → ③ 경로 키(`route_key`) 계산 → ④ 켜져 있는 복구 조치(동일 요청 병합 등) 적용 → ⑤ **길찾기 어댑터 호출: 1차 TMAP 대중교통 → 실패 시 2차 카카오맵 대중교통**(개발·시험은 모의, D-038) → ⑥ 결과 검증(출처·수단·시각·확인 가능한 통제) → ⑦ 경로 근거 붙이기 → ⑧ 추천 기준으로 점수 매겨 정렬 → ⑨ 기록(`route_requests`·`route_results`·지표)

**경로 근거(evidence) — 두 가지로 나눕니다 (D-024·D-033)**

| 근거 | 무엇을 고르는 데 쓰나 | 데이터 | 지역 |
|---|---|---|---|
| `area_evidence` 지역 선택 근거 | **어느 역·지역으로 갈지** (예: 삼각지역이 붐비니 이태원역) | 서울 실시간 인구 혼잡 구역(OA-21778), 교통 돌발(경찰청 전국·TOPIS 서울) | 혼잡 = 서울만, 돌발 = 전국 |
| `mode_evidence` 교통수단 선택 근거 | **무엇을 탈지** (만석 버스 대신 지하철) | 서울 버스 차내 혼잡(서울시 버스 도착정보 15000314의 혼잡 필드). 경로 속 정류장은 **TMAP `stationID`로 `arsId`와 연결**(같은 값인지 실호출로 확인). 2차 카카오맵 응답에는 정류장 ID가 없어 이때는 `unsupported` | 서울만. 서울 밖이면 `unsupported`, 공급원 실호출 전이면 `unverified`(0-3절). **경로 응답의 필수 부분이 아님**(없어도 경로는 제공) |

- **정류장 연결 규칙(11/19 한태경 님 확인):** TMAP `stationID`, 서울 버스 `arsId`(5자리), 카카오맵(정류장 ID 없음)은 ID 체계가 다릅니다. ① TMAP `stationID`와 `arsId`가 대응되면 ID로 연결(실호출로 확인 중) ② 안 되면 **거리(임시 30m 안) + 정류장 이름 + 노선·방향**이 모두 맞을 때만 연결 ③ 길 건너 같은 이름 정류장처럼 하나로 정해지지 않으면 연결하지 않고 `mode_evidence`를 `unverified`로 둡니다(잘못 붙이지 않음).
- 버스 차내 혼잡은 **지역이 붐빈다는 근거로 쓰지 않습니다**(버스 승객은 지나가는 사람). 처음부터 다 보여 주지 않고, 사용자가 경로를 고른 뒤 그 경로의 버스에만 보여 줍니다(D-025).

**추천 기준과 점수 (D-025, 기획서 FR-R01~R05 '고급 5유형'과 같은 이름, 비율 미정, Should)**

| `route_preference` 값 | 뜻 | 점수에 크게 반영하는 것 |
|---|---|---|
| `fastest` (기본) | **최단시간 경로** (FR-R01) | 소요 시간 |
| `less_crowded` | **혼잡 회피 경로** (FR-R02) | 혼잡(지역·차내) — 구간 단위 근거가 있을 때만, 지역 혼잡을 길 혼잡으로 단정하지 않음 |
| `accessible` | **교통약자 배려** (FR-R03) | 계단·승강기·통제 데이터가 확인된 범위만 — **없으면 `not_verifiable`** |
| `min_walk` | **최소 도보 경로** (FR-R04) — 노약자·보행 약자를 위해 **엘리베이터·에스컬레이터 등 보행 부담이 적은 동선과 도보 구간**을 안내. '최단 거리'가 아님 | 도보 거리·계단 회피(시설 데이터 확인 범위) |
| `fewest_transfers` | **최소 환승 경로** (FR-R05) | 환승 횟수 |

v0.3 초안의 `relaxed`(여유로운 길)·`shortest`(최단 거리)는 기획서와 뜻이 달라 **`less_crowded`·`min_walk`로 바꿨습니다**(11/19 정예진 님 피드백). '최단 거리'는 따로 두지 않습니다.

점수 = 시간·거리·비용·혼잡에 기준별 비율을 곱한 합(낮을수록 좋음). **비율은 실제 응답을 넣어 보고 정합니다**(지금은 미정). 점수와 쓴 비율 버전을 응답(`score`, `score_version`)에 남깁니다.

**요청 필드 명세**

| 필드 | 위치 | 타입 | 필수 | 빈값 | 제약 | 설명 |
|---|---|---|---|---|---|---|
| `request_id` | body | string | 예 | 불가 | 8~64자, UUID 권장 | 멱등 키 |
| `festival_id` | body | string | 예 | 불가 | `^fst_[0-9A-Za-z]{6,26}$` | 출발 축제 |
| `destination` | body | object | 예 | 불가 | `query` 또는 `lat`+`lng` 중 **하나만** | 목적지 |
| `destination.query` | body | string | 조건 | 불가 | 1~100자 | 장소명·주소 |
| `destination.lat` / `lng` | body | number | 조건 | 불가 | 위도 33~39, 경도 124~132 | 좌표 |
| `travel_mode` | body | string | 아니요 | — | `transit`·`walk`·`car`·`taxi`, 기본 `transit` | 이동 수단(공급원 지원 범위 확인 후 축소 가능) |
| `route_preference` | body | string | 아니요 | — | 위 5개 값, 기본 `fastest` | 추천 기준 |
| `user_constraints` | body | object | 아니요 | `{}` | `with_child`·`wheelchair`: bool, `max_walk_m`: 0~5000 또는 null | 이동 조건 |
| `departure` | body | string | 아니요 | — | `now`만(예약 출발은 후속) | 출발 시각 |

**정상 응답 필드 명세 (200)** — 202는 아래 '처리 중 응답' 필드만 돌려줍니다

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `route_request_id` | string | 불가 | `rr_` + ULID |
| `route_status` | string | 불가 | `queued`·`processing`·`ready`·`unavailable`·`rejected`·`timed_out` (`ready`만 경로 제공 성공) |
| `direction` | string | 불가 | `return` |
| `origin` / `destination` | object | 불가 | 출발(축제 DB 좌표)·도착(표시 이름, 해석 방법) |
| `route_preference` | string | 불가 | 요청한 추천 기준 |
| `route_candidates[]` | array | 빈 배열 가능 | `ready`일 때만 채움. 각 후보: `candidate_id`, `summary`, `duration_min`, `distance_m`, `walk_m`, `transfers`, `fare_krw`, `legs[]`(구간마다 `mode`·`path`=**`[[위도, 경도], …]`**·`stops[]`), `service_running`(막차 이후면 false), `score`, `area_evidence`, `mode_evidence` — **공급원이 주지 않는 값은 `null`, 만들지 않음** |
| `provider` | string | 불가 | 실제로 답한 공급원 `tmap`·`kakao`·`mock_adapter` |
| `provider_tier` | string | 불가 | `primary`·`secondary`·`mock` |
| `queried_at` | string | 불가 | 공급원 조회 시각 |
| `verification_status` | string | 불가 | `verified_basic`·`constraint_unverified`·`control_unverified`·`failed` |
| `constraint_status` | object | `{}` | 조건별 `verified`·`not_verifiable`·`unverified`(통제 등 공급원 미확인) |
| `coverage` | object | 불가 | 0절 공통 형식 |
| `score_version` | string | null | 점수 비율 버전 |
| `is_mock` | boolean | 불가 | 모의 응답이면 true |
| `notices[]` | array | 빈 배열 | 확인 못 한 것 안내 |
| `festival_id` · `travel_mode` | string | 불가 | 요청 값 그대로 |
| `completed_valid_route` | boolean | 불가 | 검증된 경로가 실제로 담겼으면 true(`ready`일 때만) |

**처리 중 응답 필드 명세 (202)**

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `route_request_id` · `route_status`(`queued`·`processing`) | string | 불가 | |
| `status_url` | string | 불가 | A05 주소 |
| `route_access_token` | string | 불가 | 짧은 수명(10분) 조회 토큰. A05의 `X-Route-Access-Token` 헤더로 보냄 |
| `retry_after_s` | int | 불가 | 다음 조회까지 기다릴 초 |
| `is_mock` | boolean | 불가 | |

**요청 예시**

```json
{
  "request_id": "6f1c2a0e-7b1d-4a5e-9a51-2b3f0c9d1e20",
  "festival_id": "fst_000123",
  "destination": { "query": "서울역" },
  "travel_mode": "transit",
  "route_preference": "less_crowded",
  "user_constraints": { "with_child": true, "wheelchair": false, "max_walk_m": null },
  "departure": "now"
}
```

**정상 응답 예시 (200, ready)** — 수치·구간은 모양을 보이기 위한 **가상 값**입니다(실호출 전, `is_mock: true`). 점수 비율이 미정이라 `score`는 `null`입니다.

```json
{
  "route_request_id": "rr_01JD8Q3K2M",
  "route_status": "ready",
  "direction": "return",
  "festival_id": "fst_000123",
  "origin": { "name": "축제장 정문(축제 DB 좌표)", "lat": 37.0, "lng": 127.0 },
  "destination": { "label": "서울역", "resolved_by": "kakao_place_search" },
  "travel_mode": "transit",
  "route_preference": "less_crowded",
  "route_candidates": [
    {
      "candidate_id": "c1", "summary": "지하철 1회 환승",
      "duration_min": 38, "distance_m": 9200, "walk_m": 650, "transfers": 1, "fare_krw": 1550,
      "legs": [ { "mode": "walk", "duration_min": 6 }, { "mode": "subway", "line": "(가상)", "duration_min": 24 }, { "mode": "walk", "duration_min": 8 } ],
      "score": null,
      "area_evidence": {
        "crowd_areas": [ { "area_code": "POI009", "congest_level": "보통", "observed_at": "…" } ],
        "traffic_incidents": []
      },
      "mode_evidence": {
        "bus_crowding": { "status": "unverified", "reason": "서울 버스 혼잡 공급원 실호출 전" }
      }
    }
  ],
  "provider": "mock_adapter",
  "provider_tier": "mock",
  "queried_at": "2026-11-19T21:40:05+09:00",
  "verification_status": "control_unverified",
  "completed_valid_route": true,
  "constraint_status": { "with_child": "not_verifiable", "control": "unverified" },
  "coverage": { "scope": "national", "region_code": "SEOUL", "supported": true },
  "score_version": null,
  "is_mock": true,
  "notices": ["공식 교통통제 반영 여부를 확인하지 못했어요."]
}
```

**처리 중 응답 예시 (202)**

```json
{
  "route_request_id": "rr_01JD8Q3K2M",
  "route_status": "queued",
  "status_url": "/api/v1/routes/return/rr_01JD8Q3K2M",
  "route_access_token": "rrt_…(짧은 수명)",
  "retry_after_s": 2,
  "is_mock": false
}
```

**오류 응답 표**

| HTTP | 코드 | 발생 조건 | 재시도 |
|---|---|---|---|
| 400 | `ROUTE_INVALID` | 목적지를 찾을 수 없음, 공급원이 지원하지 않는 수단 | 아니요(입력 수정) |
| 404 | `FESTIVAL_NOT_FOUND` | 없는 `festival_id` | 아니요 |
| 409 | `IDEMPOTENCY_CONFLICT` | 같은 `request_id`에 다른 본문 | 아니요 |
| 422 | `VALIDATION_ERROR` | 형식 오류(필드 명세 위반) | 아니요 |
| 400 | `FESTIVAL_LOCATION_UNKNOWN` | 축제 좌표가 없어 출발점을 못 정함(서버 판단) | 아니요 |
| 429 | `RATE_LIMITED` | 요청 수 제한 초과 | `Retry-After` 뒤 |
| 502 | `ROUTE_UPSTREAM_ERROR` | 1차·2차 공급원 모두 오류 | 예(1회) |
| 503 | `ROUTE_QUOTA_EXCEEDED` | 공급원 일일 한도 소진 → '확인 불가 + 공식 안내' | 아니요(당일) |
| 503 | `ROUTE_OVERLOADED` | 과부하 보호로 거절(`route_status=rejected`, **경로 제공 성공 아님**) | 예(잠시 뒤) |
| 503 | `ROUTE_PROVIDER_UNVERIFIED` | 공급원 미연동·미검증(지금 상태) | 아니요 |
| 504 | `ROUTE_TIMEOUT` | 제한 시간 초과(`route_status=timed_out`) | 예(같은 `request_id`로 1회) |

**규칙**
- `user_constraints`(아이 동반·휠체어 등)를 검증할 데이터가 없으면 `constraint_status`에 `not_verifiable`로 표시하고, "확실히 이용 가능"이라고 답하지 않습니다 (FR-R10, BFCL NLD-13·21).
- 혼잡 자료가 지역 단위뿐이면 "가장 덜 붐비는 경로"라고 판정하지 않습니다. `area_evidence`로 구역 혼잡만 보여 줍니다 (BFCL NLD-22).
- 목적지 원문은 저장하지 않고 해시·짧은 보존 라벨만 남깁니다(04 문서 7절).
- 어떤 공급원이 답했는지(`provider`·`provider_tier`)를 항상 남깁니다. 2차 공급원으로 답했다고 해서 자동 복구로 세지 않습니다(복구 판정은 7절).

### 2-2. 상태 조회: `GET /api/v1/routes/return/{route_request_id}` (A05)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 202로 접수된 귀가 요청의 처리 상태·결과 확인 (FR-R14). 화면 폴링, Route Agent(`get_route_request_status`) |
| 2 | 요청 헤더 | `X-Request-ID`(선택) · `X-Route-Access-Token: rrt_…`(필수, 요청 때 받은 짧은 수명 토큰) |
| 3 | 경로·쿼리 | `route_request_id`: string, 필수, `^rr_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 형식 오류 422 · 토큰 없음·만료 401 · 다른 요청의 토큰 403 · 없는 ID 404 |
| 6 | 정상 응답 | **200** — 요청 처리가 실패했어도 '조회'는 성공이므로 200. 실패는 `route_status`·`error`로 알림(수업 가이드 S29). 경로는 `ready`일 때만 `route_candidates`에 담음 |
| 7 | 오류 응답 | 401 `UNAUTHORIZED` / 403 `FORBIDDEN` / 404 `ROUTE_REQUEST_NOT_FOUND` / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회만 함(멱등). 폴링 간격 2초·최대 5회(임시), 그 뒤엔 '확인 불가' 안내 |

**상태별 응답 예시 (모두 200)**

```json
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "queued", "completed_valid_route": false, "retry_after_s": 2 }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "processing", "completed_valid_route": false, "retry_after_s": 2 }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "ready", "completed_valid_route": true, "route_candidates": [ "…2절과 같은 모양…" ], "provider": "tmap", "queried_at": "…" }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false, "error": { "code": "ROUTE_UPSTREAM_ERROR", "message": "길찾기 공급원 오류예요.", "retryable": true }, "notices": ["지금은 경로를 확인할 수 없어요. 공식 안내를 확인해 주세요."] }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "timed_out", "completed_valid_route": false, "error": { "code": "ROUTE_TIMEOUT", "message": "경로 조회 시간이 초과됐어요.", "retryable": true } }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "rejected", "completed_valid_route": false, "error": { "code": "ROUTE_OVERLOADED", "message": "요청이 많아 잠시 뒤 다시 시도해 주세요.", "retryable": true } }
```

- `completed_valid_route`는 **검증된 경로가 실제로 담겼을 때만 true**입니다. 대기열 접수(`queued`)는 성공이 아닙니다 (BFCL NLD-15·17).

### 2-3. 축제 검색: `GET /api/v1/festivals` (A02) — 필드 명세

| 필드 | 위치 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|---|
| `region` | query | string | 아니요 | `ALL` | 0-1절 지역 코드 | 시·도 |
| `date_from` / `date_to` | query | string(date) | 아니요 | null | `YYYY-MM-DD`, `date_from ≤ date_to`, 최대 366일 | 기간(겹치는 축제) |
| `q` | query | string | 아니요 | null | 1~50자 | 이름·장소 키워드 |
| `status` | query | string | 아니요 | null | `upcoming`·`ongoing`·`ended`·`cancelled` | 진행 상태 |
| `bbox` | query | string | 아니요 | null | `minLng,minLat,maxLng,maxLat` | 지도 화면 범위 |
| `sort` | query | string | 아니요 | `start_date` | `start_date`·`-start_date`·`name`·`distance`(`bbox` 있을 때만). `-`는 내림차순 | 정렬 |
| `page` / `page_size` | query | int | 아니요 | 1 / 20 | page ≥ 1, page_size 1~100 | 페이지 |

응답(200): `{ "items": [ { "festival_id", "name", "region_code", "venue_name", "lat", "lng", "start_date", "end_date", "event_status", "thumbnail_url", "source", "last_synced_at" } ], "total": 37, "page": 1, "page_size": 20 }` — 요청마다 외부 API를 부르지 않고 수집된 DB에서 답합니다. 오류: 422 `VALIDATION_ERROR`.

### 2-4. 축제 상세: `GET /api/v1/festivals/{festival_id}` (A03) — 필드 명세

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `festival_id` | string | 불가 | `fst_…` |
| `name` · `region_code` | string | 불가 | 이름·지역 |
| `venue_name` · `address` | string | null 가능 | 장소·주소(원본에 없을 수 있음, 실호출 전) |
| `lat` / `lng` | number | null 가능 | 좌표가 없으면 귀가 요청 시 400 `FESTIVAL_LOCATION_UNKNOWN` |
| `start_date` / `end_date` | string | null 가능(미확정 일정) | 기간 |
| `event_status` | string | 불가 | `upcoming`·`ongoing`·`ended`·`cancelled`·`needs_review` |
| `overview` · `fee_text` · `homepage_url` · `image_url` | string | null 가능 | 소개·입장료·홈페이지·이미지(공급원에 있을 때만, D-015·D-031). **TourAPI 실호출 전이라 어느 원본 필드에서 오는지 미확인** |
| `source` / `source_ref` / `last_synced_at` | string | 불가 | 출처·원본 ID·마지막 수집 시각 |

오류: 404 `FESTIVAL_NOT_FOUND`, 422 `VALIDATION_ERROR`(ID 형식).

### 2-5. 축제 가는 길: `POST /api/v1/routes/visit` (D-015)

귀가 API와 **같은 처리·검증·기록**을 쓰고 출발과 도착만 바꿉니다. `route_requests.direction='visit'`으로 기록합니다.

| 항목 | 귀가 (`/api/v1/routes/return`) | 가는 길 (`/api/v1/routes/visit`) |
|---|---|---|
| 출발 | 축제장 (축제 DB 좌표) | 사용자가 입력한 장소 `origin: {query \| lat,lng}` |
| 도착 | 사용자가 입력한 목적지 `destination` | 축제장 |
| 상태 조회 | `GET /api/v1/routes/return/{id}` | `GET /api/v1/routes/visit/{id}` |
| 1차 시연 | **필수(대표)** | 최종 |
| 부하 시험 대상 | 예 | 아니요 (대표 시연은 귀가만) |

---

## 3. Pydantic 검증 규칙

```python
from typing import Literal
from pydantic import BaseModel, Field, model_validator

TravelMode = Literal["transit", "walk", "car", "taxi"]          # 공급원 지원 범위 확인 후 축소 가능
RoutePreference = Literal["fastest", "less_crowded", "accessible", "min_walk", "fewest_transfers"]   # 기획서 FR-R01~R05
RouteStatus = Literal["queued", "processing", "ready", "unavailable", "rejected", "timed_out"]   # DB의 created는 내부 전용(응답에 안 나옴)
FinalMode = Literal["normal_recovered", "valid_cache", "alternate_source", "degraded", "unresolved"]
RegionCode = Literal["ALL", "SEOUL", "BUSAN", "DAEGU", "INCHEON", "GWANGJU", "DAEJEON", "ULSAN", "SEJONG",
                     "GYEONGGI", "GANGWON", "CHUNGBUK", "CHUNGNAM", "JEONBUK", "JEONNAM",
                     "GYEONGBUK", "GYEONGNAM", "JEJU"]
# locker·pharmacy는 보류(D-021): 값은 BFCL 도구와 맞추려고 남기고, 호출되면 status="unsupported"로 응답
FacilityCategory = Literal["toilet", "parking", "locker", "hospital", "emergency", "pharmacy",
                           "subway_station", "bus_stop", "bike_zone", "taxi_stand", "food", "attraction"]
FESTIVAL_ID = r"^fst_[0-9A-Za-z]{6,26}$"

class Place(BaseModel):                                          # 목적지(귀가) 또는 출발지(가는 길)
    query: str | None = Field(default=None, min_length=1, max_length=100)   # 장소명·주소
    lat: float | None = Field(default=None, ge=33.0, le=39.0)              # 대한민국 범위
    lng: float | None = Field(default=None, ge=124.0, le=132.0)

    @model_validator(mode="after")
    def one_of(self):
        has_query = self.query is not None
        has_point = self.lat is not None and self.lng is not None
        if has_query == has_point:            # 둘 다 있거나 둘 다 없으면 오류
            raise ValueError("query 또는 lat/lng 중 하나만")
        return self

class UserConstraints(BaseModel):
    with_child: bool = False
    wheelchair: bool = False
    max_walk_m: int | None = Field(default=None, ge=0, le=5000)

class ReturnRouteRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)       # 멱등 키(UUID 권장)
    festival_id: str = Field(pattern=FESTIVAL_ID)
    destination: Place
    travel_mode: TravelMode = "transit"
    route_preference: RoutePreference = "fastest"
    user_constraints: UserConstraints = UserConstraints()
    departure: Literal["now"] = "now"                          # 예약 출발은 후속(Should)

class VisitRouteRequest(BaseModel):                             # 축제 가는 길 (D-015)
    request_id: str = Field(min_length=8, max_length=64)
    festival_id: str = Field(pattern=FESTIVAL_ID)
    origin: Place
    travel_mode: TravelMode = "transit"
    route_preference: RoutePreference = "fastest"
    user_constraints: UserConstraints = UserConstraints()
    departure: Literal["now"] = "now"

class FestivalSearchQuery(BaseModel):
    region: RegionCode = "ALL"
    date_from: str | None = None                               # YYYY-MM-DD
    date_to: str | None = None
    q: str | None = Field(default=None, min_length=1, max_length=50)
    status: Literal["upcoming", "ongoing", "ended", "cancelled"] | None = None
    bbox: str | None = None                                    # 지도 범위 "minLng,minLat,maxLng,maxLat"
    sort: Literal["start_date", "-start_date", "name", "distance"] = "start_date"   # distance는 bbox 있을 때만
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    # 검증: date_from <= date_to, 조회 기간 최대 366일

class FacilityQuery(BaseModel):                                 # 지도 표시 (D-014)
    categories: list[FacilityCategory] = Field(min_length=1, max_length=12)
    radius_m: int = Field(default=1000, ge=100, le=3000)

class RouteLoadSimulationRequest(BaseModel):                    # 운영자 전용
    scenario: Literal["duplicate_keys", "unique_keys", "mixed"]
    comparison_arm: Literal["B0", "B1", "A1"]
    concurrency: int = Field(ge=1, le=200)                     # 상한 숫자는 첫 기준 시험 후 확정
    offered_rps: float | None = Field(default=None, gt=0, le=100)
    duration_s: int = Field(ge=5, le=300)
    unique_route_keys: int = Field(ge=1, le=1000)
    cache_state: Literal["cold", "warm"] = "cold"
    repeat_group: str | None = Field(default=None, max_length=40)   # 같은 조건 반복 묶음
    run_index: int = Field(default=1, ge=1, le=20)                  # 반복 몇 번째인지
    fault: dict | None = None                                    # {"type": "internal_delay", "delay_ms": 1~5000}
    upstream: Literal["mock_adapter"] = "mock_adapter"         # 외부 공급원 부하 금지: 실제 공급원 선택지 없음
    seed: int | None = None
```

- `RouteLoadSimulationRequest.upstream`에는 일부러 **시험용 어댑터만** 둡니다. 외부 길찾기 API에 부하를 거는 요청은 스키마 단계에서 막힙니다. **길찾기 무료 한도(TMAP 하루 10건, 카카오맵 하루 1,000건 — 11/19 한태경 조사)** 때문에도 부하 시험은 모의 응답으로만 합니다 (D-012, 회의록 ⚠8).
- `cache_state`·`repeat_group`·`run_index`는 강사 2차 의견("요청량·중복 비율·캐시 준비 상태·실행 횟수를 남겨야 같은 조건으로 다시 확인할 수 있어요")에 따라 넣었습니다.
- 숫자 상한(동시 요청 200, 지속 300초 등)은 **임시값**이며 첫 기준 성능 시험 후 확정합니다.
- **BFCL의 `F01`·`RR02`·`INC-003`은 평가용 가짜 ID**입니다. 실제 API는 0절 ID 형식(`fst_…`·`rr_…`·`inc_…`)만 받습니다. 평가 실행기는 모의 응답을 쓰므로 실제 API 검증을 거치지 않습니다(4-7절).
- 이 절의 모델에 걸리는 것은 모두 **422**입니다. 목적지를 실제로 찾을 수 있는지, 권한이 있는지는 여기서 판단하지 않고 서버 로직이 400·403으로 답합니다(0절 공통 규칙).

---

## 4. Tool 정의 (에이전트가 부르는 함수)

에이전트 도구는 모두 **내부 API를 감싼 얇은 함수**입니다. 아래 13개는 **BFCL 30문항(한다영, 11/18)의 정답 기준 이름**과 같습니다. 평가가 시작되면 이름·인자를 바꾸지 않습니다.

### 4-1. 도구 목록 (BFCL 기준 13개)

| Tool 이름 | 호출 주체 | 감싸는 API | 권한 | 1차 |
|---|---|---|---|---|
| `search_festivals` | Supervisor·Festival | `GET /api/v1/festivals` | 공개 | 필수 |
| `get_festival` | Festival·Route | `GET /api/v1/festivals/{id}` | 공개 | 필수 |
| `request_return_route` | Route | `POST /api/v1/routes/return` | 공개 | **필수(대표)** |
| `get_route_request_status` | Route·Supervisor | `GET /api/v1/routes/return/{id}` | 본인 요청 | **필수** |
| `get_official_notices` | Festival·Route | `GET /api/v1/festivals/{id}/notices` | 공개 | 최종 |
| `get_facilities` | Festival | `GET /api/v1/festivals/{id}/facilities` | 공개 | 최종 |
| `get_crowd` | Festival·Route | `GET /api/v1/festivals/{id}/crowd` | 공개 | 보조(서울만) |
| `save_favorite` | Supervisor | `PUT /api/v1/me/favorites/{festival_id}` | user (사용자 세션 토큰으로만) | 최종 |
| `get_incident` | Diagnosis·Recovery | `GET /api/v1/admin/incidents/{id}` | service(운영자 요청 맥락) | **필수** |
| `get_route_metrics` | Diagnosis | `GET /api/v1/admin/route-metrics` | service | **필수** |
| `predict_route_delay_risk` | Diagnosis | `GET /api/v1/admin/route-metrics/risk` | service | 후속(FR-H19) — BFCL에서 호출하지 않음 |
| `list_allowed_actions` | Recovery | `GET /api/v1/admin/incidents/{id}/allowed-actions` | service | **필수** |
| `propose_recovery_action` | Recovery | `POST /api/v1/admin/incidents/{id}/recovery-plans` | service | **필수** |

### 4-2. v0.2 추가 후보 도구 (BFCL 30문항 밖)

11/18 회의에서 정한 데이터를 에이전트가 쓰려면 아래 도구가 필요합니다. **BFCL 30문항에는 넣지 않았습니다**(평가 기준을 바꾸지 않기 위해). 평가 문항을 늘릴 때 함께 넣습니다.

| Tool 이름 | 호출 주체 | 감싸는 API | 쓰는 곳 |
|---|---|---|---|
| `request_visit_route` | Route | `POST /api/v1/routes/visit` | 축제 가는 길 (D-015) |
| `get_weather` | Festival·Route | `GET /api/v1/festivals/{id}/weather` | 날씨 안내 (D-012) |
| `get_transit_arrivals` | Route | `GET /api/v1/festivals/{id}/transit` | 주변 지하철·버스 도착 (D-010) |
| `get_parking_status` | Festival | `GET /api/v1/festivals/{id}/parking` | 공영주차장 빈자리 (D-010) |
| `get_traffic_incidents` | Route | `GET /api/v1/festivals/{id}/traffic-incidents` | 교통 돌발 (D-012) |

**도구로 만들지 않는 것 (에이전트가 절대 부를 수 없음)**
- 장애·부하 주입(`POST /api/v1/admin/simulations/*`): 운영자가 관리자 화면에서만 실행합니다. 챗봇 대화로 요청해도 도구가 없으므로 호출이 일어나지 않습니다 (BFCL NLD-27의 `run_simulation` 금지).
- 복구 정책 끄기·allowlist 수정·권한 변경: 코드 설정이며 API·도구가 없습니다 (BFCL NLD-30).
- 조치의 **실제 실행**: `propose_recovery_action`은 제안을 기록할 뿐입니다. 실행은 정책 코드(`policy_gate`)가 합니다.

### 4-3. 대표 Tool 명세: `request_return_route`

| 항목 | 명세 |
|---|---|
| **Tool 개요** | 선택한 축제장에서 목적지까지 귀가 경로를 요청 |
| **호출 주체** | Route Agent |
| **입력** | `{"festival_id":"fst_000123","destination":{"query":"서울역"},"travel_mode":"transit","route_preference":"fastest","user_constraints":{"with_child":true}}` (멱등 키 `request_id`는 도구 래퍼가 새 UUID로 자동 생성하고, 같은 도구 호출을 재시도할 때만 같은 값을 다시 씀) |
| **출력** | 4-5절 공통 형식: `{"ok":true,"data":{"route_request_id":"rr_…","route_status":"ready","completed_valid_route":true,"route_candidates":[…],"provider":"…","queried_at":"…","verification_status":"…","is_mock":false},"request_id":"req_…"}` / 실패 `{"ok":false,"error":{"code":"ROUTE_TIMEOUT","message":"…","retryable":true},"request_id":"req_…"}` |
| **실패** | `FESTIVAL_NOT_FOUND` / `FESTIVAL_LOCATION_UNKNOWN` / `ROUTE_INVALID` / `ROUTE_TIMEOUT` / `ROUTE_OVERLOADED` / `ROUTE_PROVIDER_UNVERIFIED` |
| **호출 전 조건** | `festival_id`와 목적지가 **모두 확정**돼야 호출. 목적지를 모르면 호출하지 않고 사용자에게 묻습니다 (BFCL NLD-19·20) |
| **재시도** | 도구 래퍼가 `ROUTE_TIMEOUT`에 한해 1회, 같은 `request_id`로만 재시도(새 요청 생성 금지) |

### 4-4. 대표 Tool 명세: `propose_recovery_action`

| 항목 | 명세 |
|---|---|
| **Tool 개요** | Recovery Agent가 진단을 보고 허용된 조치 하나를 선택·기각·보류·원복한 결정을 기록 |
| **호출 주체** | Recovery Agent |
| **입력** | `{"incident_id":"inc_01JD8Q3K2X","decision":"select","action":"singleflight_enable","reasons":["unique_route_keys=12/120, duplicate_ratio=0.9"],"rejected_actions":[{"action":"bounded_queue_adjust","reason":"중복 작업이 주원인"}],"stop_condition":{"max_minutes":5,"rollback_if":"valid_completed_rate가 오르지 않거나 rejections 증가"},"evidence_refs":["diag_01JD8Q3K2Y"]}` |
| **출력** | 4-5절 공통 형식: `{"ok":true,"data":{"plan_id":"rp_…","policy_verdict":"allowed","execution":"scheduled_by_policy_gate"},"request_id":"req_…"}` / 거절 `{"ok":false,"error":{"code":"ACTION_NOT_ALLOWED","message":"…","retryable":false},"request_id":"req_…"}` |
| **실패** | `ACTION_NOT_ALLOWED`(allowlist 밖) / `EVIDENCE_REQUIRED`(근거 ID 없음) / `INCIDENT_CLOSED` / `POLICY_LIMIT_EXCEEDED` |
| **decision 값** | `select`(선택) / `reject`(기각만 기록) / `defer`(근거 부족으로 보류 — 조치 없음, 안전 정책 유지) / `rollback`(이전에 켠 조치 원복 제안) |

---

### 4-5. 도구 공통 출력 형식과 실패 뒤 처리 (수업 가이드 S24·S25)

모든 도구는 성공·실패를 **같은 모양**으로 돌려줍니다. 에이전트는 `ok`와 `retryable`만 보고 다음 행동을 정합니다. LLM이 만든 인자도 사용자 입력처럼 다뤄 도구 안에서 3절 검증을 한 번 더 합니다.

```json
{ "ok": true,  "data": { "…내부 API 응답 본문…" }, "request_id": "req_…", "is_mock": false }
{ "ok": false, "error": { "code": "ROUTE_TIMEOUT", "message": "경로 조회 시간이 초과됐어요.", "retryable": true }, "request_id": "req_…" }
```

| 실패 코드 | `retryable` | 실패 뒤 처리 |
|---|---|---|
| `ROUTE_TIMEOUT`·`TOOL_TIMEOUT` | true | 먼저 `get_route_request_status`로 실제 처리됐는지 확인 → 아니면 **같은 `request_id`로 1회만** 재시도 |
| `ROUTE_UPSTREAM_ERROR`·`RATE_LIMITED` | true | `Retry-After` 뒤 1회. 그래도 실패면 '확인 불가 + 공식 안내'로 답함 |
| `ROUTE_QUOTA_EXCEEDED`·`ROUTE_PROVIDER_UNVERIFIED` | false | 재시도 없이 '확인 불가'로 답함 |
| `VALIDATION_ERROR`·`ROUTE_INVALID` | false | 재시도 없이 **사용자에게 다시 물음**(목적지 등) |
| `FESTIVAL_NOT_FOUND`·`INCIDENT_NOT_FOUND` | false | 재시도 없이 검색 단계로 되돌아감 |
| `FORBIDDEN`·`ACTION_NOT_ALLOWED` | false | 멈추고 이유를 안내. 다른 방법으로 우회하지 않음 |
| `EVIDENCE_REQUIRED` | false | Diagnosis 단계로 되돌려 근거를 다시 모음 |
| `REGION_UNSUPPORTED` | false | 실패가 아님 — '이 지역은 미지원'으로 그대로 안내 |

**도구 실행 전 서버가 확인하는 4가지(S26):** ① 이 에이전트에 허용된 도구인가(에이전트별 허용 목록) ② 요청한 사용자의 권한(사용자가 못 하는 일은 에이전트도 못 함) ③ 대상이 그 사용자가 볼 수 있는 자원인가(`save_favorite`는 세션 사용자 본인만) ④ 복구 조치는 allowlist·근거 ID·상한을 정책 코드(`policy_gate`)가 검사.

**API의 `X-Request-ID`와 도구 출력의 추적 ID(`request_id`, `req_…`)는 같은 값**으로 이어, 로그에서 요청 하나를 끝까지 추적합니다. 경로 요청의 멱등 키(UUID)와는 다른 값입니다.

### 4-6. 도구 description과 JSON Schema (1차 필수 도구)

`description`은 LLM이 **언제 이 도구를 쓸지** 판단하는 근거라 구체적으로 씁니다.

| 도구 | description (LLM에게 주는 설명) |
|---|---|
| `search_festivals` | 지역·기간·키워드로 축제 목록을 찾는다. 상대 날짜("이번 주말")는 대화의 기준 날짜로 바꿔서 넣는다. 축제를 정하기 전에 쓴다. |
| `get_festival` | 축제 하나의 장소·좌표·일정·출처를 확인한다. 귀가 출발점을 확인하거나 사용자가 고른 축제를 자세히 볼 때 쓴다. |
| `request_return_route` | 축제장에서 목적지까지 귀가 경로를 요청한다. **축제와 목적지가 모두 정해졌을 때만** 쓴다. 목적지를 모르면 쓰지 말고 사용자에게 묻는다. |
| `get_route_request_status` | 이미 요청한 귀가 경로의 처리 상태를 확인한다. `queued`는 성공이 아니다. |
| `get_incident` | (운영자 맥락) 사건 하나의 감지 근거·상태·지표 요약을 본다. 진단의 첫 단계에서 쓴다. |
| `get_route_metrics` | (운영자 맥락) 귀가 조회 지표(요청량·p95·대기열·거절·중복률·내부/외부 지연)를 본다. 원인을 구분할 때 쓴다. |
| `list_allowed_actions` | (운영자 맥락) 이 사건에서 지금 허용된 복구 조치와 상한을 본다. 복구 결정 전에 반드시 쓴다. |
| `propose_recovery_action` | (운영자 맥락) 허용된 조치 중 하나를 선택·기각·보류·원복한 결정을 근거와 함께 기록한다. **실행은 하지 않는다**(정책 코드가 실행). |

**JSON Schema — `request_return_route`**

```json
{
  "name": "request_return_route",
  "description": "축제장에서 목적지까지 귀가 경로를 요청한다. 축제와 목적지가 모두 정해졌을 때만 쓴다.",
  "parameters": {
    "type": "object",
    "properties": {
      "festival_id": { "type": "string", "description": "출발 축제 ID" },
      "destination": {
        "type": "object",
        "properties": {
          "query": { "type": "string", "minLength": 1, "maxLength": 100 },
          "lat": { "type": "number", "minimum": 33, "maximum": 39 },
          "lng": { "type": "number", "minimum": 124, "maximum": 132 }
        }
      },
      "travel_mode": { "type": "string", "enum": ["transit", "walk", "car", "taxi"], "default": "transit" },
      "route_preference": { "type": "string", "enum": ["fastest", "less_crowded", "accessible", "min_walk", "fewest_transfers"], "default": "fastest" },
      "user_constraints": {
        "type": "object",
        "properties": {
          "with_child": { "type": "boolean" },
          "wheelchair": { "type": "boolean" },
          "max_walk_m": { "type": ["integer", "null"], "minimum": 0, "maximum": 5000 }
        }
      }
    },
    "required": ["festival_id", "destination"]
  }
}
```

**JSON Schema — `propose_recovery_action`**

```json
{
  "name": "propose_recovery_action",
  "description": "허용된 복구 조치 하나를 선택·기각·보류·원복한 결정을 근거와 함께 기록한다. 실행은 하지 않는다.",
  "parameters": {
    "type": "object",
    "properties": {
      "incident_id": { "type": "string" },
      "decision": { "type": "string", "enum": ["select", "reject", "defer", "rollback"] },
      "action": { "type": "string", "description": "list_allowed_actions 결과 안의 값만" },
      "reasons": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
      "rejected_actions": { "type": "array", "items": { "type": "object", "properties": { "action": { "type": "string" }, "reason": { "type": "string" } } } },
      "stop_condition": { "type": "object" },
      "evidence_refs": { "type": "array", "items": { "type": "string" }, "minItems": 1 }
    },
    "required": ["incident_id", "decision", "reasons", "evidence_refs"]
  }
}
```

나머지 도구의 입력 스키마는 8절 표, JSON Schema는 구현할 때 FastAPI·Pydantic 모델에서 생성해 이 문서와 대조합니다(v0.4).

### 4-7. BFCL 30문항과의 대조 (강사 일일 피드백 5)

**대조 기준:** BFCL 문서 = `놀다가_BFCL_30문항.md`(한다영, 2026-11-18 11:16 팀 문서함, **API 설계 v0.1 기준**) ↔ 이 문서 v0.3. **합의 버전: 아직 없음** — 아래 '다름'을 한태경·한다영 님과 맞춘 뒤 "BFCL vX ↔ API v0.3"으로 이 칸에 기록합니다.

| 항목 | BFCL | API v0.3 | 판정 | 조치 |
|---|---|---|---|---|
| 도구 이름 13개 | 13개 | 4-1과 같음 | ✅ 같음 | — |
| 정답 호출 인자 (`festival_id`·`destination`·`travel_mode`·`user_constraints`·`incident_id`·`decision`·`action`·`reasons`·`evidence_refs`, `search_festivals`의 `region`·`date_from`·`date_to`) | 사용 | 같은 이름·타입 | ✅ 같음 | — |
| `propose_recovery_action` 생략 인자 | NLD-10 `rollback`에 `action` 없음, NLD-23 `select`에 `stop_condition` 없음 | 둘 다 생략 가능, 서버가 기본값을 채움(7-4) | ✅ 맞춤(v0.3에서 API를 완화) | BFCL 정답 그대로 |
| `reasons` 타입 | 정답에 문자열(자유 서술) | `array<string>` | ⚠ 다름 | 도구 래퍼가 문자열 1개를 배열로 감쌈 → BFCL 정답 유지 |
| 가상 응답의 기타 필드 | `get_festival.venue`, NLD-13 `accessibility_verified`, NLD-06 `service_status`, `get_incident` 최상위 `evidence_refs`(`diag-23`) | `venue_name`, `constraint_status`, (A02에 없음), `diagnosis.evidence_refs`(`diag_…`) | ⚠ 다름 | 가상 응답 필드명을 v0.3에 맞추는 것을 태경·다영 님과 합의(실행 전이면) |
| `get_facilities` | 도구는 `category` 1개 | A08은 `categories[]`, `radius_m` 기본 1000 | 래퍼가 변환 | 도구는 BFCL대로 1개, 래퍼가 `[category]`로 보냄 |
| `route_preference` | 없음 | 새 선택 인자(기본 `fastest`) | ➕ 추가만 | 기존 정답 그대로 통과. 문항 추가는 선택 |
| `get_facilities.category` 허용값 | `toilet·parking·locker·hospital·pharmacy` | 12종(물품보관함·약국은 보류 → `unsupported`) | ⚠ 일부 다름 | BFCL 값은 모두 API에 포함 → 정답 유지 가능 |
| `get_route_metrics`·`search_festivals` 인자 표 | 도구 표에 인자 칸이 비어 있음 | 8절에 정의 | ⚠ BFCL 문서 보완 필요 | 태경·다영 님께 8절 기준으로 채움 요청 |
| 가상 응답 필드명 | `routes[]`·`route_id`·`source`·`status` | `route_candidates[]`·`candidate_id`·`provider`·`route_status` | ⚠ **다름** | 실행 전이면 BFCL 가상 응답을 v0.3 이름으로 수정, 이미 실행했으면 그 결과는 'v0.1 기준'으로 표시하고 그대로 둠 |
| 평가용 ID | `F01`·`RR02`·`INC-003` | `fst_…`·`rr_…`·`inc_…` | ⚠ 형식 다름 | 가상 응답 안에서만 쓰는 가짜 ID로 명시(실제 API 검증 안 거침) |
| NLD-12 과거 구간 혼잡 DB | 기능 없음 → '현재 경로 확인 불가'가 정답 | 기능 없음 | ✅ 같음 | **새 기능으로 넣지 않음**(확인 불가로 답하는 것이 정답) |
| NLD-03 `predict_route_delay_risk` | 후속 구현, 이번 채점 제외 | 후속(A17) | ✅ 같음 | — |
| 길찾기 공급원 | `MOCK_ROUTE` | 1차 TMAP·2차 카카오맵·모의 | — | 평가에는 영향 없음(모의 응답) |

**평가 결과를 적을 때 구분할 것 (BFCL-PREPARE 기준):**

| 구분 | 분모 | 실행 여부 표시 |
|---|---|---|
| BFCL 원본 공통 30문항 | 30 | 강사님 실행분만 '실행', 나머지 '미실행' |
| 팀 자체 30문항(놀다가) — 1단계 판단 평가 | 17(호출 판단만) | 문항별 실행/미실행 |
| 팀 자체 30문항 — 2단계 가상 연동 | 13(가상 응답 주입) | 주입 못 하면 '미실행' |
| 실제 서비스 연동 시험 | 별도 | 구현 후. 판단 평가 결과를 실제 복구 성공으로 쓰지 않음 |

---

## 5. Tool 호출 흐름

**정상 귀가 요청 (BFCL NLD-04·11·16·18 형태)**

```
사용자 → POST /api/v1/assistant/query (run_id 발급)
  → Supervisor: 의도 = 귀가, 필요한 값 확인(festival_id, 목적지)
      ├─ 축제가 정해지지 않았으면 search_festivals → (첫 결과 선택 등)
      ├─ 장소를 모르면 get_festival
  → Route: request_return_route
      ├─ ready → 코드 검증(출처·시각·조건) + 경로 근거(혼잡 구역·교통 돌발) → Supervisor가 답변 통합
      └─ queued/processing → get_route_request_status(폴링 상한 있음) → ready/unavailable
  → 답변: 경로 + provider + queried_at + 확인 못 한 조건 + 미지원 데이터 표시
```

**길찾기 공급원 전환 (어댑터 안, 코드가 처리 — D-038)**

```
Route Query Service → 1차 TMAP 대중교통 어댑터 (제한 5초, 출발·도착 도보와 정류장 ID 포함)
  ├─ 성공 → 검증 → ready (provider=tmap, provider_tier=primary)
  └─ 시간 초과·429·5xx·한도 소진 → 2차 카카오맵 대중교통 어댑터 1회 (+ 도보 API로 첫·끝 도보 보완)
        ├─ 성공 → 검증 → ready (provider=kakao, provider_tier=secondary, 버스 혼잡 근거 unsupported)
        └─ 실패 → unavailable '확인 불가 + 공식 안내' (만든 경로·오래된 경로로 채우지 않음)
개발·시험(APP_ENV≠prod): 두 어댑터 대신 같은 형식의 모의 어댑터(mock_adapter). 개발 초기 실물 확인은 무료 한도가 큰 카카오맵으로
```

- 요청 1건 안에서 2차로 넘어가는 것은 **어댑터의 기본 동작**이고, 그것만으로 '자동 복구'로 세지 않습니다. 1차 공급원 오류가 기준 이상 계속되면 감지 코드가 `failure_domain=route_upstream` 사건을 만들고, 그때부터는 아래 장애 흐름(진단 → 조치 선택 → 같은 부하 재확인)을 따릅니다.
- **좌표 순서:** TMAP 경로선(`passShape.linestring`, `steps[].linestring`)은 **`"경도,위도 경도,위도"`** 순서이고 카카오맵 지도는 `LatLng(위도, 경도)`입니다. 어댑터가 **내부 형식 `[위도, 경도]`로 바꿔서** 돌려주므로 화면은 순서를 신경 쓰지 않습니다(좌표계는 둘 다 WGS84라 변환은 필요 없음). TMAP으로 받은 경로는 카카오 길찾기 화면(`landingURL`)을 쓸 수 없어서 **경로선·정류장 마커·안내 문구를 화면이 직접 그립니다**.
- **막차:** TMAP 응답의 `service`(1 운행 중 / 0 운행 종료)를 `service_running`으로 옮기고, 0이면 `notices`에 '운행이 끝난 구간이 있어요'를 넣습니다.
- **TMAP 약관 — 받은 데이터는 저장 후 24시간 넘게 쓸 수 없음:** 캐시(`valid_until`, 지금 60초)는 문제없고, DB에 남긴 경로 내용은 **24시간 안에 지웁니다**(04 문서 7절). 원본 JSON 근거 파일도 24시간 안에 필드만 확인하고 지우며, 강사님 제출용 근거는 **키·좌표를 바꾼 합성 예시와 메타데이터**로 남깁니다.
- **카카오맵 결과는 A04의 동기 응답(3초 안)에서만 전달합니다.** 카카오 개발자 답변상 임시 캐싱도 허용되지 않아, 이미 202로 접수한 요청의 결과를 나중에 A05로 돌려줄 수 없습니다. 그래서 202 이후 1차(TMAP)가 실패하면 A05는 `route_status=unavailable`, 오류 `ROUTE_SECONDARY_SYNC_ONLY`('다시 조회해 주세요')로 답하고 사용자가 새로 요청하면 2차를 동기로 부릅니다. **이 문제가 풀리기 전에는 2차 공급원을 쓴 비동기 복구를 '복구 완료'로 세지 않습니다**(11/19 정예진 님 피드백).
- **카카오맵 응답은 저장·캐시하지 않습니다**(개발자 포럼 답변 기준 '응답 저장 제한', 요청 때 호출해 전달하고 폐기하는 중계는 가능). 2차로 답한 경로는 DB에 경로 내용 없이 출처·시각만 남깁니다(04 문서 6-1). TMAP의 저장 조건은 약관 확인 필요(11절).
- TMAP 1차를 고른 이유(D-038): 정류장 ID·좌표(버스 혼잡 연결), 출발·도착 도보 포함, 출발 시각 지정(`searchDttm`), 초과 단가 0.88원/건. 카카오맵은 하루 1,000건 무료라 2차·개발 초기 검증에 씁니다.


**귀가 조회 장애 (BFCL NLD-03·10·23~26 형태)**

```
관측 코드(Route Query Service)가 장애 기준(12절 3번) 초과 감지 → incident_id 생성(코드)
  → Diagnosis: get_incident → get_route_metrics
      → verified_facts / hypotheses / unknowns / affected_features 기록
  → Recovery: list_allowed_actions → propose_recovery_action(select | reject | defer | rollback)
  → policy_gate(코드): allowlist·상한·권한 검사 → 실행 → action_enabled_at 기록
  → 같은 부하로 재측정(B0/B1/A1) → final_mode 5종 중 하나로 종료
  → 에이전트 시간 초과·형식 오류 → B1 규칙 정책으로 전환(FR-H15)
```

API `X-Request-ID` ↔ 에이전트 `run_id` ↔ `route_request_id` ↔ `incident_id`를 모든 로그에 같이 남겨, 사용자 화면과 운영 타임라인을 한 사건으로 이어 봅니다 (FR-H10, FR-O02).

---

## 6. API 목록

| # | 메서드 | 경로 | 인증 | 설명 | 관련 FR·결정 | 1차 시연 |
|---|---|---|---|---|---|---|
| A01 | GET | `/api/v1/health` | 없음 | 서버·DB·Redis 상태 | — | 필수 |
| A02 | GET | `/api/v1/festivals` | 없음 | 축제 검색(`region` 코드·기간·키워드·상태·지도 범위 `bbox`) | FR-F01/F10/F15 | **필수** |
| A03 | GET | `/api/v1/festivals/{festival_id}` | 없음 | 축제 상세(장소·좌표·기간·**간단한 소개·입장료**·출처·`last_synced_at`) | FR-F01, D11, **D-015** | **필수** |
| A04 | POST | `/api/v1/routes/return` | 없음 | **AI 안심 귀가 경로 요청** (2절) | FR-R13~R17, D-009 | **필수(대표)** |
| A05 | GET | `/api/v1/routes/return/{route_request_id}` | 요청 토큰 | 귀가 요청 처리 상태·결과 | FR-R14 | **필수** |
| A06 | POST | `/api/v1/assistant/query` | 없음 | 챗봇 질문 → 에이전트 실행. 응답에 `answer`, `run_id`, 사용한 도구·근거 | FR-C01~C09, D-012 | 귀가 안내 한정 |
| A07 | GET | `/api/v1/festivals/{festival_id}/notices` | 없음 | 공식 운영 공지·교통통제(무정차·우회 등). `type` 필터 | FR-F05/F13 | 최종 |
| A08 | GET | `/api/v1/festivals/{festival_id}/facilities` | 없음 | **지도 표시용 주변 시설**(`categories` 여러 개, `radius_m`). **1차 10종**: 화장실·주차장 위치·병원·응급실·지하철역·버스 정류장·자전거 존·택시 승강장(**둘 다** 전국 통합 공급원·좌표가 확인되면 전국, 없으면 검증된 서울 공급원으로, **위치 안내만** — 실시간 대여 가능 수·택시 호출 제외)·맛집·주변 관광지 (**보류**: 물품보관함¹·약국²). 공급원 미확인 항목은 `status:"unverified"`(0-3절) | FR-F04/F11, **D-014** | 최종 |
| A09 | GET | `/api/v1/festivals/{festival_id}/weather` | 없음 | 축제 위치 날씨·예보(발표 시각 포함, 기상청 전국) | FR-F09, D-012 | 최종 |
| A10 | GET | `/api/v1/festivals/{festival_id}/crowd` | 없음 | 서울 혼잡 구역(검증된 매핑만, 아니면 `unsupported`). 지도 빨강·노랑·초록 | FR-F02/F14, D-010 | 보조(서울만) |
| A11 | GET | `/api/v1/me/favorites` | user | 내 관심 축제 목록 | FR-A08 | 최종 |
| A12 | PUT | `/api/v1/me/favorites/{festival_id}` | user | 관심 저장(이미 있으면 그대로 200) | FR-A08 | 최종 |
| A13 | DELETE | `/api/v1/me/favorites/{festival_id}` | user | 관심 해제 | FR-A08 | 최종 |
| A14 | GET | `/api/v1/admin/incidents` | operator | 사건 목록(`failure_domain`, 상태, 기간) | FR-O02 | 필수 |
| A15 | GET | `/api/v1/admin/incidents/{incident_id}` | operator/service | 사건 상세: Route/Diagnosis/Recovery trace, offered load, 전후 지표, 상태 변경 이력, `final_mode` | FR-H10, O02 | **필수** |
| A16 | GET | `/api/v1/admin/route-metrics` | operator/service | 경로 조회 지표(시간창별 offered·완료·p50/p95·대기열·오류·거절·중복률) | FR-O01, H01 | **필수** |
| A17 | GET | `/api/v1/admin/route-metrics/risk` | operator/service | 지연 위험 예측(추세 기반) | FR-H19 | 후속 |
| A18 | GET | `/api/v1/admin/incidents/{incident_id}/allowed-actions` | operator/service | 지금 허용된 조치 목록·상한·현재 켜진 조치 | FR-H04/H05 | **필수** |
| A19 | POST | `/api/v1/admin/incidents/{incident_id}/recovery-plans` | operator/service | Recovery 결정 기록 → 정책 검사 → 실행 예약 | FR-H04/H05/H27 | **필수** |
| A20 | POST | `/api/v1/admin/simulations/route-load` | operator (시험 환경만) | **통제된 귀가 조회 부하 주입** (B0/B1/A1) | FR-O03, H21/H23 | **필수** |
| A21 | POST | `/api/v1/admin/simulations/{simulation_id}/stop` | operator | 부하 시험 즉시 중단 | FR-O03 | 필수 |
| **A31** | GET | `/api/v1/admin/simulations/{simulation_id}` | operator | 부하 시험 상태(`running`·`finished`·`stopped`·`failed`)·구간별 지표·연결된 사건 목록·결과 위치. 사건이 안 생긴 시험(평소 구간만)도 여기서 확인 | FR-O03, 수업 가이드 S29 | 필수 |
| **A32** | POST | `/api/v1/auth/signup` | 없음 | 회원 가입(이메일·비밀번호·표시 이름) → `users`·`profiles` 생성 | FR-A(회원), D-037 | 최종 |
| **A33** | POST | `/api/v1/auth/login` | 없음 | 로그인 → Access JWT + Refresh Token (1절) | D-037 | 최종 |
| **A34** | POST | `/api/v1/auth/refresh` | Refresh Token | 토큰 갱신(교체 방식) | D-037 | 최종 |
| **A35** | POST | `/api/v1/auth/logout` | user | 로그아웃(Refresh 폐기, `jti` 차단) | D-037 | 최종 |
| **A36** | GET | `/api/v1/me/festival-preferences` | user | 내 축제 취향·온보딩 상태 조회 | 기획서 최신본 5.18 (신규 필수: 맞춤 추천) | 설계안 — **v0.4 상세** |
| **A37** | PUT | `/api/v1/me/festival-preferences` | user | 취향 선택·변경·건너뛰기 저장 | 〃 | 설계안 |
| **A38** | GET | `/api/v1/festivals/recommended` | 선택(취향 계정 기준) | 맞춤 추천(필터·페이지·`recommendation_reason`, **규칙 기반**, 실제 축제 DB에 있는 것만) | 〃 | 설계안 |
| **A39** | GET | `/api/v1/festivals/popular` | 없음 | 실제 참여 지표(상세 조회·관심 추가) 기반 인기 | 〃 | 설계안 |
| **A40** | GET | `/api/v1/festivals/discover` | 없음 | 고정 시드 기반 전체 축제 둘러보기 | 〃 | 설계안 |
| **A41** | GET | `/api/v1/festivals/recent` | 없음 | 최초 공개일 기준 최신 등록 | 〃 | 설계안 |
| A22 | POST | `/api/v1/admin/simulations/crowd` | operator (시험 환경만) | 혼잡 API 500·stale·본문 오류 모의 (v2.5 보존) | FR-H20 | 보조 |
| A23 | GET | `/api/v1/admin/ingestion-jobs` | admin | 축제 수집 작업 이력·오류 | FR-O09, D01 | 최종 |
| A24 | GET/POST | `/api/v1/admin/festivals/review-queue` | admin | 중복·충돌 축제 검토·승인 | FR-D12/D14, O10 | 최종 |
| **A25** | POST | `/api/v1/routes/visit` (+ `GET /api/v1/routes/visit/{id}`) | 없음 | **축제 가는 길** (2-5절) | FR-R(기본 왕복), **D-015** | 최종 |
| **A26** | GET | `/api/v1/festivals/{festival_id}/transit` | 없음 | 주변 지하철역·버스 정류장 **실시간 도착**. 지하철 실시간은 서울만, 버스는 서울 = 서울시 버스도착정보·서울 밖 = TAGO | **D-010·D-012** | 최종 |
| **A27** | GET | `/api/v1/festivals/{festival_id}/parking` | 없음 | 주변 **공영주차장 실시간 빈자리**(서울만). 다른 지역은 위치만(`A08 parking`)과 `unsupported` | **D-010** | 최종 |
| **A28** | GET | `/api/v1/festivals/{festival_id}/traffic-incidents` | 없음 | 주변 **교통 돌발**(사고·공사·행사 통제). 경찰청(전국) + 서울 TOPIS | **D-012·D-019** | 최종 |
| **A29** | GET | `/api/v1/festivals/{festival_id}/visit-forecast` | 없음 | **방문 집중 예측**(향후 30일, 상대값 0~100) + 지역 관광 수요. '실시간 혼잡'과 다른 이름·색으로 표시 | **D-018** | 최종 |
| **A30** | GET | `/api/v1/data-sources` | 없음 | 데이터 공급원별 **지원 지역·실시간 여부·마지막 수집 시각** (화면의 '미지원' 안내·관리자 확인용) | D-016, 데이터 조사 | 최종 |

- **A36~A41 경로 규칙:** FastAPI에서 `/festivals/recommended`·`/popular`·`/discover`·`/recent` 같은 **고정 경로를 `/festivals/{festival_id}`보다 먼저 등록**하고, `festival_id`는 `^fst_` 형식을 검사합니다(라우터 작성 규칙·테스트 항목).
- **동행·친구·채팅(신규 필수):** 기획서 최신본 5.18의 '계약 영역'만 정해졌고 경로·번호는 W112에서 정합니다 → **v0.4에서 이 표에 추가**. 친구 검색은 **친구 코드** 기본(닉네임은 공개 허용한 경우만, 이메일·전화번호 검색 안 함 — 11/19 정예진 님 제안).

¹·² 물품보관함·약국: **보류**(D-021, 11/18). 11/18 회의 지도 목록에 없어 넣지 않기로 함. 다만 BFCL `get_facilities`의 `category` 값(`locker`·`pharmacy`)에는 이미 들어 있어서, 평가 기준을 바꾸지 않도록 값은 남기고 호출되면 `status:"unsupported"`로 응답합니다.

**상세 명세 작성 범위 (v0.3, 11/20 제출본)**

| 수준 | API | 상태 |
|---|---|---|
| 8칸 상세 + 필드 명세 + 예시 | A04(2절), A05(2-2), A19(7-4) | 작성 |
| 필드 명세 표 | A02(2-3), A03(2-4), A15(7-2), A20(7-1) | 작성 |
| 요청·응답 모양만 | A06, A14, A16, A18, A21, A25(2-5) | **v0.4 작성 예정**(구현 시작 전) |
| 목록·권한·지역 범위만 | A07~A13, A17, A22~A24, A26~A30 | 공급원 실호출 뒤 작성 예정 |
| 목록만(신규 필수 기능) | A36~A41 맞춤 추천, 동행·친구·채팅(번호 미정) | **v0.4**(W112에서 계약 확정 후) |

수업 가이드는 "최종 제출에는 구현하기로 확정한 API 전체의 명세"를 요구합니다. **v0.3에서 아직 부족한 것**(교차 검토로 확인): 1차 필수 중 A06·A14·A16·A18·A21의 8칸 상세와 필드 표, A05 응답 필드 표, 필수 도구 6개(`search_festivals`·`get_festival`·`get_route_request_status`·`get_incident`·`get_route_metrics`·`list_allowed_actions`)의 JSON Schema와 개별 출력 예시, A10 혼잡 응답 필드 표(11/16 원본 있음). → **v0.4(구현 시작 전)** 에 채웁니다.

**공통 오류 코드**

| 코드 | HTTP | 의미 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 입력 형식 오류(Pydantic) |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 | 인증 없음·만료 / 권한 부족·타인 자원 |
| `RATE_LIMITED` | 429 | 요청 수 제한 초과 |
| `FESTIVAL_NOT_FOUND` | 404 | 없는 축제 ID |
| `FESTIVAL_LOCATION_UNKNOWN` | 400 | 축제 좌표가 없어 출발점을 정할 수 없음 |
| `IDEMPOTENCY_CONFLICT` | 409 | 같은 `request_id`에 다른 본문 |
| `ROUTE_INVALID` | 400 | 목적지 해석 실패·지원하지 않는 수단 |
| `ROUTE_PROVIDER_UNVERIFIED` | 503 | 경로 공급원 미연동·미검증(현재 상태) |
| `ROUTE_TIMEOUT` | 504 | 경로 조회 제한 시간 초과 |
| `ROUTE_UPSTREAM_ERROR` | 502 | 외부 길찾기 API 오류(429·5xx 포함, 원본 코드는 로그에) |
| `ROUTE_QUOTA_EXCEEDED` | 503 | 길찾기 공급원 일일 한도 소진(1차·2차 모두) — 경로 확인 불가 + 공식 안내 |
| `ROUTE_QUEUE_TIMEOUT` | 504 | 내부 대기열에서 제한 시간 초과 |
| `ROUTE_OVERLOADED` | 503 | 과부하 보호로 거절(`route_status=rejected`, 경로 제공 성공 아님) |
| `ROUTE_REQUEST_NOT_FOUND` | 404 | 없는 `route_request_id` (A05) |
| `INCIDENT_NOT_FOUND` / `INCIDENT_CLOSED` | 404 / 409 | 없는 사건 / 이미 닫힌 사건에 결정 기록 (A19) |
| `DUPLICATE_PLAN` | 409 | 같은 사건에 실행 중인 조치가 있음 (A19) |
| `SIMULATION_RUNNING` | 409 | 이미 실행 중인 부하 시험 (A20) |
| `TOOL_TIMEOUT` | — (도구 출력) | 도구 호출 제한 시간 초과 (4-5) |
| `ROUTE_SECONDARY_SYNC_ONLY` | 200 (A05의 `error`) | 2차(카카오맵) 결과는 저장할 수 없어 비동기로 전달 불가 → 새로 요청 (5절) |
| `ROUTE_CONTROL_UNVERIFIED` | 200 (경고) | 경로는 있으나 공식 통제 반영 여부 확인 불가 — 오류가 아니라 `notices`에 표시 |
| `AI_AGENT_FAILED` | 200/503 | 에이전트 실패. 기본 귀가 조회·축제 기능은 계속 제공 |
| `REGION_UNSUPPORTED` | 200 | 그 지역에 해당 데이터가 없음(`status=unsupported`) |
| `SOURCE_HTTP_ERROR` / `SOURCE_RESULT_ERROR` / `SOURCE_STALE` | 502 / 502 / 200 | 외부 데이터: HTTP 오류 / 본문 결과 코드 오류 / 관측 시각이 오래됨 |
| `ACTION_NOT_ALLOWED` / `EVIDENCE_REQUIRED` / `POLICY_LIMIT_EXCEEDED` | 403 / 400 / 409 | 복구 결정이 정책을 통과하지 못함 |
| `SIMULATION_DISABLED` | 403 | 운영 환경에서 부하·장애 주입 시도 |

**화면 상태와의 대응:** `queued`→'대기 중', `processing`→'조회 중', `ready`→'검증된 경로', `unavailable`·`timed_out`→'확인 불가(재조회·공식 안내)', `rejected`→'요청 거절(잠시 후 재시도)', `unsupported`→'이 지역은 미지원', `unverified`→'준비 중인 정보', `stale`→'○분 전 정보'. (기획서 5.12)

### 6-1. 범위에서 뺀 것 (D-013)

| 항목 | 결정 | 이유 |
|---|---|---|
| 티켓·예약·결제 | ❌ API 없음 | 회의 결정, 기획서 v2.9 예매 보류 |
| 공연·전시 정보 | ❌ API 없음 | 축제만 다룸 |
| 웹 크롤링 | ❌ 1차 제외 | 공식 API·공공데이터만 사용. 멘토 권고(D-027)로 팀 결정 대기(14절) |
| SNS 후기 현장 요약 | ⏸ 2차(나중에) | 메인 기능 아님 |
| 정류장 눌러 버스 혼잡 보기, 자전거 추가 기능(따릉이 실시간 등) | ⏸ 나중에 | D-011, 회의록 ⚠9 |
| 물품보관함·약국 지도 표시 | ⏸ 보류 | D-021 (회의 지도 목록 밖) |

---

## 7. 상세 명세: 귀가 조회 부하 주입과 복구 결정

### 7-0. 복구 시험 설계: 감지부터 경로 제공 회복까지 (강사 일일 피드백 4)

시험 한 번(같은 `repeat_group`)은 **세 구간**을 같은 부하 조건(`scenario`·`concurrency`·`offered_rps`·`duration_s`·`unique_route_keys`·`seed`·`cache_state`)으로 이어서 잽니다.

| 구간 | 무엇을 하나 | 기록 위치 |
|---|---|---|
| ① 평소 (`baseline`) | 장애 없이 같은 부하 | `route_query_metrics`(`phase='baseline'`) |
| ② 장애 (`fault`) | 내부 처리 지연을 주입 → **감지 코드가 사건을 만들 때까지** | `phase='fault'`, `incident_logs.detected_at`·`detection_rule` |
| ③ 자동 조치 뒤 (`after_action`) | 조치가 켜진 뒤 같은 부하로 재측정 | `phase='after_action'`, `recovery_attempts.after_metrics` |

**대응 방식 세 가지를 같은 입력으로 비교**합니다. 어느 쪽이 낫다는 결론은 미리 쓰지 않고, 차이가 없거나 에이전트가 못하면 그대로 남깁니다.

| `comparison_arm` | 대응 방식(`responder_type`) | 조치를 누가 고르나 |
|---|---|---|
| `B0` | `none` 복구 없음 | 아무도 (대조군) |
| `B1` | `rule` 규칙 대응 | 고정 규칙 코드 |
| `A1` | `agent` 에이전트 대응 | Diagnosis·Recovery 에이전트 → 정책 코드 검사 |

**구간마다 남기는 지표:** p50·p95 지연, 오류율(시간 초과·거절·공급원 오류 포함), **유효한 경로 제공률 = 검증된 경로가 담긴 응답 수 ÷ 보낸 요청 수**(대기열 접수·HTTP 200은 성공에 넣지 않음), 감지까지 걸린 시간, 조치 후 회복까지 걸린 시간(MTTR).


### 7-1. `POST /api/v1/admin/simulations/route-load`

```http
POST /api/v1/admin/simulations/route-load
Authorization: Bearer <operator_access_token>
Content-Type: application/json

{ "scenario": "duplicate_keys", "comparison_arm": "B1", "concurrency": 120,
  "duration_s": 60, "unique_route_keys": 12, "cache_state": "cold",
  "repeat_group": "dup12-c120", "run_index": 1, "upstream": "mock_adapter", "seed": 7 }
```

```http
HTTP 202
{ "simulation_id": "sim_01JD…", "test_mode": true,
  "comparison_arm": "B1", "status": "running", "stop_url": "/api/v1/admin/simulations/sim_01JD…/stop" }
```

**요청 필드 명세 (A20)**

| 필드 | 타입 | 필수 | 제약 | 설명 |
|---|---|---|---|---|
| `scenario` | string | 예 | `duplicate_keys`·`unique_keys`·`mixed` | 요청 분포 |
| `comparison_arm` | string | 예 | `B0`·`B1`·`A1` | 대응 방식(7-0) |
| `concurrency` | int | 예 | 1~200(임시) | 동시 요청 |
| `offered_rps` | number | 아니요 | 0 초과 ~100 | 초당 요청 |
| `duration_s` | int | 예 | 5~300(임시) | 구간별 지속 시간 |
| `unique_route_keys` | int | 예 | 1~1000 | 서로 다른 경로 키 수 |
| `fault` | object | 아니요 | `{ "type": "internal_delay", "delay_ms": 1~5000 }` | 장애 주입(없으면 평소 구간만) |
| `cache_state` | string | 아니요 | `cold`·`warm` | 캐시 준비 상태 |
| `repeat_group` / `run_index` | string / int | 아니요 | ≤40자 / 1~20 | 반복 묶음·몇 번째 |
| `upstream` | string | 아니요 | `mock_adapter`만 | **외부 공급원 부하 금지** |
| `seed` | int | 아니요 | — | 재현 |

응답(202): `simulation_id`·`test_mode`·`comparison_arm`·`status`·`stop_url`·`status_url`. 결과는 **A31 `GET /api/v1/admin/simulations/{simulation_id}`**(조회 성공이면 시험이 실패했어도 200, 실패는 `status`·`error`로)로 확인합니다. 요청 헤더에 `Idempotency-Key`(필수)를 받아 같은 키면 처음 만든 `simulation_id`를 돌려줍니다.

- 부하 생성기는 **팀 서버 안의 경로 처리 구간과 시험용 어댑터**에만 요청을 보냅니다. 외부 공급원은 부르지 않습니다.
- 장애 기준을 넘으면 관측 코드가 `incident_id`를 만들고 시뮬레이션 기록에 연결합니다. **시뮬레이션 1회에 사건이 여러 건 생길 수 있습니다**(감지 → 원복 → 재감지). 시뮬레이션이 사건을 직접 만들지 않습니다 — 감지 로직도 시험 대상이기 때문입니다.
- B0/B1/A1을 비교할 때는 `scenario`·`concurrency`·`offered_rps`·`duration_s`·`unique_route_keys`·`seed`·`cache_state`를 **똑같이** 두고, 같은 `repeat_group`으로 여러 번(`run_index`) 돌립니다 (FR-H23, 강사 2차 의견 5).
- 끝나면 결과 JSON·보고서 위치를 `load_simulations.result_ref`·`report_ref`에 남깁니다.

| 상태 코드 | 조건 | 응답 코드 |
|---|---|---|
| 422 | 상한 초과·잘못된 시나리오(형식 검사) | `VALIDATION_ERROR` |
| 401 / 403 | 인증 실패 / operator 아님 | `UNAUTHORIZED` / `FORBIDDEN` |
| 403 | 운영 환경(`APP_ENV=prod`)에서 호출 | `SIMULATION_DISABLED` |
| 409 | 이미 실행 중인 시뮬레이션 있음 | `SIMULATION_RUNNING` |

### 7-2. `GET /api/v1/admin/incidents/{incident_id}` 응답 모양

```json
{
  "incident_id": "inc_01JD8Q3K2X",
  "failure_domain": "internal_route",
  "status": "closed",
  "detected_at": "…", "closed_at": "…",
  "simulation_id": "sim_…", "comparison_arm": "A1", "responder_type": "agent", "test_mode": true,
  "offered_load": { "offered_requests": 120, "concurrency": 120, "unique_route_keys": 12 },
  "detection_rule": "p95_ms > 기준 30초 지속",
  "metrics_baseline": { "p50_ms": null, "p95_ms": null, "error_rate": null, "valid_route_rate": null, "valid_completed": null, "rejections": null },
  "metrics_before":   { "p50_ms": null, "p95_ms": null, "error_rate": null, "valid_route_rate": null, "valid_completed": null, "rejections": null },
  "diagnosis": { "verified_facts": [], "hypotheses": [], "unknowns": [], "affected_features": ["return_route"], "evidence_refs": [] },
  "recovery_plans": [ { "decision": "select", "action": "singleflight_enable", "rejected_actions": [], "policy_verdict": "allowed" } ],
  "recovery_attempts": [ { "action": "singleflight_enable", "action_enabled_at": "…", "action_disabled_at": null, "validation_result": "pending", "stop_reason": null, "rollback_reason": null } ],
  "status_history": [ { "from": "open", "to": "diagnosing", "at": "…", "actor": "service" } ],
  "metrics_after":    { "p50_ms": null, "p95_ms": null, "error_rate": null, "valid_route_rate": null, "valid_completed": null, "rejections": null },
  "final_mode": "normal_recovered",
  "agent_runs": [ { "agent_name": "diagnosis", "status": "ok", "started_at": "…", "ended_at": "…" } ]
}
```

- `failure_domain` 값: `internal_route`(내부 경로 처리) / `route_upstream`(외부 길찾기 공급원) / `agent`(에이전트 실패) / `crowd_upstream`(혼잡 공급원, 보조) / `ingestion`(축제 수집). **BFCL 가상 응답과 같은 이름**입니다.
- `final_mode`는 같은 부하 재측정 결과가 있을 때만 채웁니다. 대기열 접수 수(`accepted`)는 성공 수에 넣지 않습니다 (BFCL NLD-17).

**응답 필드 명세 (A15)**

| 필드 | 타입 | 빈값 | 설명 | DB |
|---|---|---|---|---|
| `incident_id` | string | 불가 | `inc_…` | `incident_logs.incident_id` |
| `failure_domain` | string | 불가 | 5개 값 | `incident_logs.failure_domain` |
| `status` | string | 불가 | `open`→`diagnosing`→`recovering`→`validating`→`closed` | `incident_logs.status` |
| `detected_at`·`closed_at` | string | closed_at null 가능 | | `incident_logs` |
| `detection_rule` | string | 불가 | 넘은 기준 | `incident_logs.detection_rule` |
| `simulation_id`·`comparison_arm` | string | 시험 아니면 null | | `load_simulations` |
| `responder_type` | string | 시험 아니면 null | `none`·`rule`·`agent` | 진행 중: `comparison_arm`에서 계산(B0→none, B1→rule, A1→agent), 종료 뒤: `incident_outcomes.responder_type` |
| `test_mode` | bool | 불가 | 장애 주입 시험이면 true | `incident_logs.injected_test` |
| `offered_load` | object | 시험 아니면 null | 보낸 요청 수·동시 요청·고유 경로 키 수 | `load_simulations` |
| `metrics_baseline`·`metrics_before`·`metrics_after` | object | after는 재측정 전 null | 7-0의 세 구간, **같은 모양**(`p50_ms`·`p95_ms`·`error_rate`·`valid_route_rate`·`valid_completed`·`rejections`) | `route_query_metrics`·`incident_logs.before_metrics`·`recovery_attempts.after_metrics` |
| `diagnosis` | object | null 가능 | 사실·가설·확인 불가·영향 기능·근거 | `incident_diagnostics` |
| `recovery_plans[]`·`recovery_attempts[]` | array | 빈 배열 | 결정·실행 기록 | `recovery_plans`·`recovery_attempts` |
| `status_history[]` | array | 빈 배열 | 상태 변경 이력 | `incident_events` |
| `final_mode` | string | 재측정 전 null | 5종 | `incident_outcomes.final_mode` |
| `agent_runs[]` | array | 빈 배열 | 에이전트 실행 기록 | `agent_runs` |

### 7-3. 허용 조치 allowlist (1차 시연 후보)

| action | 하는 일 | 적용 조건(정책 코드가 검사) | 원복 조건 |
|---|---|---|---|
| `singleflight_enable` | 같은 `route_key`로 진행 중인 조회 결과를 공유 | 동일 키 중복률 근거 + 키에 방향·출발·목적지·수단·조건·시각 구간·통제 버전이 모두 포함 | 같은 부하에서 유효 경로 완료율이 오르지 않거나 거절·시간초과 증가 |
| `bounded_queue_adjust` | 내부 대기열 길이·대기 제한 조정(상한 안에서) | 내부 대기열 증가가 주원인이고 외부 지연이 정상 | 거절률이 기준 이상 증가 |
| `valid_cache_serve` | 조건이 같은 **유효** 캐시 경로 제공 | 캐시 `valid_until` 안 + 통제 버전 일치 + `verified_at` 있음. **목적지가 다른 요청에 비슷한 캐시를 주지 않음** | 통제 버전 변경·TTL 만료 |
| `fallback_provider_switch` | 길찾기 1차(TMAP)를 잠시 건너뛰고 2차(카카오맵)로 바로 보냄 | `failure_domain=route_upstream` + 1차 오류 근거 + **2차 공급원 키·응답 확인 완료** + 2차 일일 한도 여유 | 1차 정상 응답 회복, 또는 2차 한도 80% 도달(9절 규칙) |
| `safe_degrade` | 경로 대신 '확인 불가 + 공식 안내' 제공, 축제 기능 유지 | 다른 조치가 없거나 효과 없음 | 정상 지표 연속 회복 |
| `rollback` | 켜 둔 조치를 끄고 원래 정책으로 복귀 | 효과 미달·부작용 근거 | — |

이 목록에 없는 조치(새 공급원 전환, 무제한 재시도, 복구 정책 끄기 등)는 `ACTION_NOT_ALLOWED`입니다. `fallback_provider_switch`는 **2차 공급원(카카오맵)을 실제 호출로 확인한 뒤에만** 켤 수 있습니다(지금은 미확인 → 비활성). 켜는 동안 버스 혼잡 근거는 `unsupported`가 되고 경로는 캐시하지 않습니다. **목적지가 모두 다른 요청(고유 키)에서는 병합 효과가 없으므로** Recovery는 `singleflight_enable`을 기각하고 다른 조치나 보류를 고릅니다 (강사 2차 의견 3, BFCL NLD-24).


### 7-4. 복구 결정 기록: `POST /api/v1/admin/incidents/{incident_id}/recovery-plans` (A19)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | Recovery(에이전트 또는 규칙 코드)가 허용 조치 하나를 선택·기각·보류·원복한 결정을 기록 → 정책 코드가 검사 → 통과하면 실행 예약 (FR-H04/H05/H27). 호출 주체: Recovery Agent(`propose_recovery_action`), B1 규칙 코드 |
| 2 | 요청 헤더 | `Authorization: Bearer <service 또는 operator 토큰>`(필수) · `Content-Type: application/json` · `Idempotency-Key: <UUID>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | `incident_id`: string, 필수, `^inc_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 아래 필드 명세 |
| 5 | 검증·권한 | 형식 422 → 역할(operator/service 아니면 403 `FORBIDDEN`) → 사건 존재(404) → 사건이 닫혔으면 409 `INCIDENT_CLOSED` → `action`이 지금 allowlist에 있나(403 `ACTION_NOT_ALLOWED`) → `evidence_refs`가 실제 진단·지표 ID인가(400 `EVIDENCE_REQUIRED`) → 상한(동시에 켠 조치 수 등, 409 `POLICY_LIMIT_EXCEEDED`). **본문의 근거 ID는 주장일 뿐이라 서버가 DB에서 확인**합니다 |
| 6 | 정상 응답 | **202** — 결정을 기록하고 실행을 예약함(실행이 끝났다는 뜻 아님). 결과는 A15의 `recovery_attempts`로 확인. `decision`이 `reject`·`defer`면 실행 없이 **201** |
| 7 | 오류 응답 | 400 `EVIDENCE_REQUIRED` / 401 / 403 `FORBIDDEN`·`ACTION_NOT_ALLOWED` / 404 `INCIDENT_NOT_FOUND` / 409 `INCIDENT_CLOSED`·`POLICY_LIMIT_EXCEEDED`·`DUPLICATE_PLAN`(같은 사건에 실행 중인 조치가 있음) / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 같은 `Idempotency-Key`는 처음 만든 `plan_id`를 돌려줌 · 같은 사건에 실행 중인 조치가 있으면 409 · 재시도는 응답이 끊겼을 때 A15로 상태를 먼저 확인한 뒤 1회 |

**요청 필드 명세**

| 필드 | 타입 | 필수 | 빈값 | 제약 | DB |
|---|---|---|---|---|---|
| `decision` | string | 예 | 불가 | `select`·`reject`·`defer`·`rollback` | `recovery_plans.decision` |
| `action` | string | `select`면 예 | null 가능 | 7-3 allowlist 값. `rollback`에서 생략하면 **서버가 지금 켜진 조치로 채움** | `recovery_plans.action` |
| `reasons` | array<string> | 예 | 불가 | 1개 이상, 각 ≤300자 | `recovery_plans.reasons` |
| `rejected_actions` | array<object> | 아니요 | `[]` | `{action, reason}` | `recovery_plans.rejected_actions` |
| `stop_condition` | object | 아니요 | — | `{max_minutes, rollback_if}`. `select`에서 생략하면 **서버 기본값**(5분, '유효 경로 제공률이 오르지 않거나 거절 증가 시 원복')을 채워 저장 | `recovery_plans.stop_condition` |
| `evidence_refs` | array<string> | 예 | 불가 | 1개 이상, `diag_`·지표 ID | `recovery_plans.evidence_refs` |

**정상 응답 예시 (202)**

```json
{ "plan_id": "rp_01JD9A…", "incident_id": "inc_01JD8Q3K2X", "decided_by": "recovery_agent",
  "policy_verdict": "allowed", "execution": "scheduled_by_policy_gate", "attempt_id": "ra_01JD9B…" }
```

**거절 예시 (403)**

```json
{ "error": { "code": "ACTION_NOT_ALLOWED", "message": "허용 목록에 없는 조치예요.", "request_id": "req_…", "retryable": false } }
```

### 7-5. 조치 뒤 재검증·종료 기준 (강사 일일 피드백 4)

조치를 켠 뒤 **같은 부하로 재측정**하고, 결과에 따라 아래처럼 끝냅니다. 각 판정은 사건 기록에 남깁니다.

| 재측정 결과 | 판정(`validation_result`) | 다음 행동 | 기록 |
|---|---|---|---|
| 유효 경로 제공률 ≥ 기준, p95 < 기준 | `improved` | 사건 종료 `final_mode=normal_recovered` | `recovery_attempts`, `incident_outcomes` |
| 캐시·대체 경로로 제공했고 **유효성 검사 통과**(조건·시각·`valid_until`·통제 버전 일치) | `improved` | `final_mode=valid_cache` 또는 `alternate_source` | `route_results.validity_check` |
| 지표 변화 없음 | `no_effect` | 조치 원복(`rollback`) → 다른 허용 조치 1회 더 → 그래도 없으면 `safe_degrade` | `rollback_reason`, `incident_events` |
| 나빠짐(거절·시간 초과 증가) | `worse` | **즉시 원복** → `safe_degrade` | 같음 |
| 정해진 시간(`stop_condition.max_minutes`) 안에 판정 못 함 | `no_effect` (`stop_reason=time_limit`) | 원복 후 `final_mode=unresolved`, 운영자 확인 | 같음 |
| 허용 조치가 없음 | — (`stop_reason=no_allowed_action`) | `defer` + `safe_degrade`('경로 확인 불가 + 공식 안내') | `recovery_plans.decision='defer'`, `recovery_attempts.stop_reason` |

- **캐시·대체 경로 유효성 검사 규칙:** 같은 `route_key`(방향·출발·목적지·수단·조건·시각 구간·통제 버전)일 때만 씁니다. **목적지가 다른 요청에 비슷한 캐시를 주지 않습니다.** 검사 결과(통과/실패와 이유)를 `route_results.validity_check`에 남깁니다.
- 기준 숫자(유효 경로 제공률·p95)는 평소 구간(`baseline`) 시험 뒤 정합니다(12절 3번).

---

## 8. 도구 호출 정의 (입력 스키마·실행 조건)

| 도구 | 입력 스키마 | 실행 조건 / 호출하지 않는 경우 |
|---|---|---|
| `search_festivals` | `region?: RegionCode="ALL", date_from?: date, date_to?: date, q?: str, status?: enum, page_size?: int≤20` | 날짜가 "이번 주말"처럼 상대 표현이면 **대화의 기준 날짜**로 바꾼 뒤 호출. 기준 날짜가 없으면 묻기 |
| `get_festival` | `festival_id: str` | 대화에 선택된 축제가 있을 때. "그 축제"를 무엇으로 볼지 모르면 묻기 (BFCL NLD-20) |
| `request_return_route` | `festival_id: str, destination: {query \| lat,lng}, travel_mode?: enum="transit", route_preference?: enum="fastest", user_constraints?: obj` | 축제·목적지 모두 확정 시. 목적지 없으면 묻기 (BFCL NLD-19) |
| `get_route_request_status` | `route_request_id: str` | 이전 요청 ID가 대화 맥락에 있을 때. 폴링은 최대 5회·간격 2초(임시값) |
| `get_official_notices` | `festival_id: str, type?: enum[operation, traffic_control, no_stop, bus_detour, road_closure]` | 공지 공급원 연동 후. 없으면 "확인할 수 있는 공지 자료가 없음" 안내 |
| `get_facilities` | `festival_id: str, category: FacilityCategory` | 시설 공급원 연동 후 (BFCL NLD-08). 서비스 API(A08)는 여러 종류를 한 번에 받지만, 도구는 BFCL에 맞춰 한 종류씩 |
| `get_crowd` | `festival_id: str` | 서울 지원 장소 매핑이 있을 때만 값. 없으면 `unsupported` 결과를 그대로 안내 (BFCL NLD-07·28) |
| `save_favorite` | `festival_id: str` | **로그인 세션이 있을 때만**. 사용자 ID는 입력으로 받지 않고 세션에서 가져옴 |
| `get_incident` | `incident_id: str` | 운영자 맥락 + 사건 ID 있을 때 |
| `get_route_metrics` | `incident_id?: str, simulation_id?: str, window: str="5m"` | 진단 시작 시 필수 |
| `predict_route_delay_risk` | `window: str="15m", horizon: str="5m"` | 후속 구현. 구현 전에는 관측 추세만 설명하고 "예측 기능 미구현"으로 답 (BFCL NLD-03) |
| `list_allowed_actions` | `incident_id: str` | Recovery 판단 전 필수 |
| `propose_recovery_action` | `incident_id: str, decision: enum[select,reject,defer,rollback], action?: str, reasons: list[str], rejected_actions?: list, stop_condition?: obj, evidence_refs: list[str]≥1` | `list_allowed_actions` 결과 안의 action만. 근거 ID 없으면 호출 불가 |

**호출하지 않는 것이 정답인 요청** — 도구가 없거나 정책상 막힘 (BFCL 기준): 정보 부족 되묻기(NLD-19·20), 접근성 보장 확인(NLD-21), 지역 혼잡만으로 가장 한산한 경로 판정(NLD-22), 대기열 접수를 성공으로 집계(NLD-17), 일반 사용자의 장애 주입 요청(NLD-27), 행사장 내부 실시간 인원(NLD-28), 오래된 경로를 안전하다고 표시(NLD-29), 문서 속 지시로 정책 끄기(NLD-30, 프롬프트 인젝션).

30문항별 정답 호출은 **BFCL 문서(`받은자료/2026-11-18_한다영_놀다가_BFCL_30문항.md`)를 기준**으로 합니다(v0.1의 부록 A는 삭제).

---

## 9. 장애 격리·호출 제한 (API 쪽 장치)

| 장치 | 설정(초안) | 이유 |
|---|---|---|
| 작업 풀 분리 | 귀가 조회 처리와 축제 검색·상세를 서로 다른 동시성 한도로 처리 | 귀가 부하가 검색을 멈추지 않게 (FR-H18, BFCL NLD-06) |
| 타임아웃 | 길찾기 어댑터 5초 · 그 밖의 외부 데이터 3초 · **도구 호출 15초(`TOOL_TIMEOUT`)** · **에이전트 실행 전체(A06) 30초** (모두 임시) | 무한 대기 방지 |
| 재시도 | 일시적 오류(시간 초과·429·5xx)만 최대 1회, **1초 뒤**(429는 `Retry-After`), 같은 멱등 키 | 무제한 재시도 금지 (FR-H02) |
| 요청 수 제한 | 귀가·가는 길 요청 IP·세션당 분당 N회(N 미정) | 외부 쿼터·비용 보호 |
| **길찾기 일일 한도** | TMAP(1차: 무료 10건, 이후 0.88원/건 종량제)·카카오맵(2차: 무료 1,000건, 이후 10원/건) 호출 수와 **하루 비용 상한(임시 1,000원)**을 공급원별로 Redis에서 셈. **80%: 운영 경고 + 그 공급원으로 보내는 우회 조치(`fallback_provider_switch`) 원복. 100%: 그 공급원 호출 중지**(남은 공급원도 없으면 `ROUTE_QUOTA_EXCEEDED`) | 11/19 한태경 조사(공식 문서 기준, 실호출로 재확인) |
| 외부 데이터 캐시 | 날씨·도착 정보·주차·돌발은 공급원 갱신 주기만큼 캐시(초안: 도착 30초, 주차 1분, 돌발 1분, 날씨 10분) | 같은 화면을 여러 사람이 볼 때 외부 호출 줄이기 |
| LLM 실패 | `/api/v1/assistant/query` 실패해도 A02~A05는 독립 동작 | FR-C09, FR-H13 |
| 외부 429 | `ROUTE_UPSTREAM_ERROR` + 원본 코드 로그, 재시도는 `Retry-After` 이후 1회 | BFCL NLD-12·25 |
| 재시도하지 않는 오류 | 400·401·403·404·409·422 | 입력·권한 문제는 다시 보내도 같음(수업 가이드 S22) |
| 중복 실행 방지 | 경로 요청은 `request_id`, 복구 결정은 `Idempotency-Key`로 처음 결과를 돌려줌. 같은 사건에 실행 중인 조치가 있으면 409 | 수업 가이드 S22 |
| 실제 공급원 부하 금지 | 부하·장애 시험의 `upstream`은 `mock_adapter`만(3절 스키마에서 막음) | 강사 일일 피드백 2 |

---

## 10. 실제 호출 근거 (현재 확보분)

| API | 호출 일시 | 요청 조건(키 제외) | 결과 | 증빙 |
|---|---|---|---|---|
| 서울시 실시간 인구데이터 `citydata_ppltn` (OA-21778) | 2026-11-16 16:07경 | `sample` 키, JSON, 장소 `광화문·덕수궁` | `RESULT.CODE=INFO-000`, `AREA_CD=POI009`, `AREA_CONGEST_LVL=보통`, `AREA_PPLTN_MIN/MAX=48000/50000`, `PPLTN_TIME=2026-11-16 15:40`, `FCST_YN=Y` + `FCST_PPLTN[]` | `DB/notes/evidence/2026-11-16_citydata_ppltn_광화문덕수궁.json` (GitHub 연결 필요) |
| TourAPI `searchFestival2` | 2026-11-19 (한태경) | 정식 키, 서울·부산 지역 | ✅ 서울 28건·부산 6건. 지역 변수는 **`lDongRegnCd`(서울 11, 부산 26)**, `areacode`는 빈 값. 필드 `title`·`eventstartdate`·`eventenddate`·`mapx`(경도)·`mapy`(위도)·`contentid`. **시작 전 행사도 섞여 옴** → `event_status` 재계산. 틀린 키: `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` | `2026-11-19_tourapi_서울/부산/오류-키오류.json` (태경님 보관 → 팀 문서함·GitHub 연결 필요) |
| TourAPI `detailIntro2` | 2026-11-19 (한태경) | 서울 3035607·부산 3360113 | ✅ 입장료 `usetimefestival`, 행사 시간 `playtime`(형식 불규칙), 장소 `eventplace`, 주최 `sponsor1`. 2건 모두 무료라 유료 형식 미확인. **소개(overview)는 이 응답에 없음** → `detailCommon2` 확인 필요 | `2026-11-19_tourapi-상세_*.json` |
| 서울 실시간 인구 (정식 키) | 2026-11-19 (한태경) | 광화문·덕수궁, 서울역 | ✅ 정식 키 확인. **없는 장소도 HTTP 200 + 본문 `ERROR-500`** → `SOURCE_RESULT_ERROR`로 처리(HTTP 코드만 보면 안 됨). 예측 12건 | `2026-11-19_seoul-ppltn_*.json` |
| 기상청 초단기실황 | 2026-11-19 (한태경) | 격자 서울 60,127 · 부산 98,75 | ✅ 기온 `T1H`, 강수 `RN1`, 강수형태 `PTY`. **좌표 → 격자 변환이 필요**(부산역은 97,74로 재확인) | `2026-11-19_kma_*.json` |
| TAGO 버스 정류소 | 2026-11-19 (한태경) | 좌표 검색 부산역·광화문 | 부산역 21건(도시코드 21), **광화문 0건** → **서울 버스는 TAGO로 안 됨**, 서울시 버스도착정보(15000314)로 바꿈 | `2026-11-19_tago-정류소_*.json` |
| TAGO 버스 도착 | 2026-11-19 (한태경) | 부산역 정류소 | 종점이라 0건 → 도착 필드 미확인, 다른 정류소 재호출 필요 | `2026-11-19_tago-도착_부산역.json` |
| 서울 지하철 실시간 도착 | 2026-11-19 (한태경) | 서울역 | ✅ 19건. `barvlDt`(0이어도 도착 전일 수 있음 → `arvlMsg2` 함께 사용), `updnLine`, `recptnDt`. 틀린 키 `INFO-100` | `2026-11-19_seoul-subway_*.json` |
| 서울 시영주차장 실시간 | 2026-11-19 (한태경) | 전체 | ✅ 122건. `TPKCT`·`NOW_PRK_VHCL_CNT`·`NOW_PRK_VHCL_UPDT_TM`. **위경도 없음** → 지도 표시하려면 주차장 위치 데이터와 연결 필요 | `2026-11-19_seoul-parking.json` |
| 서울 TOPIS 돌발 `AccInfo` | 2026-11-19 (한태경) | 전체 | ✅ 28건. `acc_type`·`acc_dtype`·`link_id`·`occr_date/time`·`exp_clr_date/time`. XML, **좌표 `grs80tm_x/y` → 위경도 변환 필요**, 시각 자릿수 혼재 | `2026-11-19_seoul-accinfo.json` |
| 서울 문화행사 OA-15486 | 2026-11-19 (한태경) | 5건 | ✅ 19,783건, 대부분 공연류. 축제 포함 여부·TourAPI 중복 미확인, 날짜 이상값 1건 → **보강용 우선순위 낮춤** | `2026-11-19_seoul-culture.json` |
| TMAP 대중교통(1차) | **미호출** | — | — | 키 발급·종량제 결제 등록 후 (10-1, 담당 한태경) |
| 카카오맵 대중교통·도보(2차) | **미호출** | — | — | 키 발급 후 (10-1) |
| 경찰청 교통 돌발·카카오·서울 버스도착정보·3순위 정적 데이터 | **미호출** | — | — | `놀다가_설계/API키_정리표.md` '다음에 확인할 것' |

→ A10(`crowd`)의 응답 필드는 위 원본으로 정했습니다. **A02·A03(축제) 연결표는 11/19 실호출로 아래처럼 정했고**, A04(경로)는 10-2절(실호출 전)입니다.

| 내부 필드 (A02·A03) | TourAPI 원본 | DB 컬럼 | 상태 |
|---|---|---|---|
| `festival_id` 원본 키 | `contentid` | `festival_sources.source_item_id` | ✅ 확인 |
| `name` | `title` | `festivals.title` | ✅ |
| `start_date` / `end_date` | `eventstartdate` / `eventenddate` (YYYYMMDD) | `festivals.start_date` / `end_date` | ✅ |
| `lat` / `lng` | `mapy` / `mapx` | `festivals.latitude` / `longitude` | ✅ |
| `region_code` | `lDongRegnCd`(서울 11 → `SEOUL`, 부산 26 → `BUSAN`) | `festivals.region_code` | ✅ 2개 확인, 나머지 15개 시·도 대응은 참고문서로 채움 |
| `venue_name` | `eventplace`(detailIntro2) | `festivals.venue_name` | ✅ |
| `fee_text` | `usetimefestival`(detailIntro2) | `festivals.admission_fee_text` | ✅ (유료 형식 미확인) |
| 주최 | `sponsor1` | `festivals.organizer` | ✅ |
| `overview` | `detailCommon2` 예상 | `festivals.summary` | 미확인 |

### 10-1. 최소 실호출 계획 (강사 일일 피드백 2)

실제 공급원의 무료 한도를 아끼기 위해 **정상·오류 형식을 확인하는 최소 호출만** 합니다. 원본 응답은 키를 지우고 `DB/notes/evidence/`에 저장해 GitHub에 연결하고, 그 구조를 본뜬 모의 응답을 만들어 개발·부하 시험은 모의 응답으로만 합니다.

| 공급원 | 확인할 것 | 정상 호출 | 오류 호출 | 합계 | 담당 |
|---|---|---|---|---|---|
| TMAP 대중교통(1차) | 응답 필드(`legs[].steps`·`totalFare`·`stationID`·`routeId`·`lat`/`lon`), `searchDttm`, 지방 지원, 오류 형식 | 3회 — **같은 좌표 세트**: ① 서울 축제장 → 서울역(지금) ② 지방 축제장(예: 부산) → 부산역(지금) ③ ①을 축제 종료 시각 `searchDttm=22:00`으로 | 1회: 잘못된 좌표 | 4 (무료 10건 안) | 한태경(원본 보관) → 권오현 검토 |
| 카카오맵 대중교통·도보(2차) | 응답 필드(`fare`·`path.points`), 정류장 정보 부족 확인, 도보 API로 첫·끝 도보 보완, 지방 지원 | TMAP ①② 같은 좌표 2회 + 도보 2회 | 1회: 잘못된 좌표 | 5 (무료 1,000건 안) | 권오현 |
| TMAP `stationID` ↔ 서울 버스 `arsId` | 같은 값인지, 변환이 필요한지 | ①의 경로 속 버스 정류장 1개로 서울 버스 도착정보 조회 | — | 1 | 권오현 |
| 카카오 장소 검색 | 목적지 해석 | 2회: "서울역", "잠실" | 1회: 빈 결과 나오는 검색어 | 3 | 권오현 |
| 서울 버스 도착정보(혼잡 필드) | 차내 혼잡·재차 인원 필드가 실제로 있는지 | 1회: 축제장 근처 정류소 | 1회: 없는 정류소 ID | 2 | 권오현 |
| TourAPI 축제 검색·상세 | ✅ **11/19 한태경 완료**(10절). 남은 것: `detailCommon2` 소개 1회 | 1회 | — | 1 | 한태경 |

- 남길 것: 요청 조건(키 제외)·호출 시각·HTTP 코드·원본 결과 코드·응답 JSON 위치. 시연 날에는 실제 호출 수를 세어 9절 한도 규칙(80% 경고·우회 원복, 100% 중지)을 따릅니다.
- 같은 요청을 반복하는 개발 호출, 부하 시험, 장애 주입은 **실제 공급원에 하지 않습니다.**

### 10-2. 원본 응답 → 내부 API → DB 연결표 (실호출 뒤 채움)

| 내부 필드 (A04 `route_candidates[]`) | TMAP 원본 필드(1차, 문서 기준) | 카카오맵 원본 필드(2차, 문서 기준) | DB 컬럼 | 상태 |
|---|---|---|---|---|
| 경로 구간 `legs[]`(도보 포함) | `legs[]`, 도보 `legs[].steps`, 경로선 `passShape.linestring`·`steps[].linestring`(**경도,위도 순서** → 어댑터가 `[위도, 경도]`로 뒤집음) | 구간 `path`(첫·끝 도보 없음 → 도보 API로 보완) | `route_results.candidates` (JSONB, **카카오는 저장 안 함**) | 미확인 |
| 소요 시간 `duration_min` | 실호출 후 | 실호출 후 | 같음 | 미확인 |
| 요금 `fare_krw` | `totalFare` | `fare.value`(min/max 의미 문서에 없음) | 같음 | 미확인 |
| 정류장·노선 `legs[].stops[]`·`route_id` | `stationID`·`routeId`, 좌표 `lat`/`lon` | 없음(정류장 이름만) | 같음 | 미확인 |
| 운행 여부 `service_running` | `service`(1 운행 중 / 0 운행 종료) | 없음 | 같음 | 문서 확인(11/19 한태경) |
| 출처 `provider`·`provider_tier` | 어댑터가 붙임 | 어댑터가 붙임 | `route_results.provider`·`provider_tier` | 설계 확정 |
| 조회 시각 `queried_at` | 어댑터가 호출 시각 기록 | 같음 | `route_results.queried_at` | 설계 확정 |

원본 필드 이름은 공식 문서(태경님 11/19 대조) 기준이며 실호출로 확인한 뒤 '미확인'을 지웁니다.


---

## 11. 미확인 항목·확인 계획

| 항목 | 현재 상태 | 확인 담당 | 확인 시점 |
|---|---|---|---|
| TMAP 실호출(1차, D-038): 필드·`searchDttm`이 막차 판단에 충분한지·지방 지원·**응답 저장 조건(약관)**·VAT 포함 여부·종량제 결제 등록 | 공식 문서 대조만(11/19 한태경) | W10: 한태경(키·종량제 결제 등록·원본) → 권오현(검토) | 11/20~ |
| 카카오맵 실호출(2차): 정류장 정보 부족·도보 보완·저장 제한 원문 | 문서·개발자 포럼 답변만 | 권오현 | 11/20~ |
| **TMAP 경로를 카카오맵(다른 회사 지도) 위에 표시해도 되는지** | TMAP 약관에 금지 문구는 없으나 전체 계약 조건 미확인, 카카오 쪽도 미확인(11/19 한태경) | 한태경 → 양쪽 개발 문의 | 발표·운영 전 |
| TMAP 무료 체험 사용 조건 | 하루 10건, **같은 서비스로 프로젝트를 여러 개 만들면 중지될 수 있음 → 팀 키 하나만** 사용 | 한태경 | 진행 중 |
| 지방 축제의 실시간 결합 정보 | 버스 도착·지하철·돌발 등 실시간 결합 API가 서울 중심 → 지방은 경로만 + '실시간 정보 미지원' 안내 | 권오현 | 실호출 후 |
| TourAPI 팀 키 실호출 (A02·A03 필드, 지역 코드 대응) | 미호출 | 권오현 (W98) | 키 발급 후 |
| 목적지·출발지 장소 검색(지오코딩) | **카카오 장소 검색으로 정함**(D-035). 응답 필드는 실호출 후 | 권오현 | 길찾기와 함께 |
| **버스 차내 혼잡도** 공급원 | 후보: 서울시 버스 도착정보의 혼잡·재차 인원 필드(서울만, D-033). 실제 필드 확인 전 | 권오현 | 키 발급 후 (10-1) |
| 지하철 실시간 도착 범위(수도권 노선 포함 여부) | 서울 열린데이터광장 확인 필요 | 권오현 | 키 발급 후 |
| 공영주차장 실시간 빈자리 | 서울 시영주차장만 확인됨 | 권오현 | 키 발급 후 |
| 경찰청 교통돌발 실제 지역 범위·행사/공사 구분 | 웹 조사만 | 권오현 | 키 발급 후 |
| 방문 집중 예측: 축제 장소가 '관광지' 목록과 맞는 비율 | 웹 조사만 | 권오현 | 키 발급 후 |
| 자전거 존·택시 승강장 데이터 공급원 | 자전거: 행정안전부 '전국 공영자전거 실시간 정보' 후보(공공데이터포털에서 확인 필요) → 확인되면 전국. 택시 승강장: 전국 통합 공급원을 아직 못 찾음 → 찾으면 전국, 없으면 서울 공급원(D-036, 기획서 FR-F04) | 권오현 | 11/20 이후 |
| 경로 점수 비율(시간·거리·비용·혼잡) | 미정(D-025) | 권오현·정예진 | 실제 응답 확보 후 |
| 서비스 범위 | ✅ **D-020·D-022로 정함**: 전국에 있는 데이터 = 전국, 지역별로만 있는 데이터 = 서울만 (0-2절) | 팀 | 정함 |
| DB·인증 방식 | ✅ D-037(11/19 사용자): AWS 위 Docker PostgreSQL + FastAPI 자체 JWT. **기획서·WBS는 아직 'Supabase 확정'** → 팀 공유·수정 필요. AWS 서버 사양·배포 방식은 인프라 담당과 확정 | 권오현 → 신유빈·정예진 | 11/20 전 |
| 숫자 상한(동시 요청, 지속시간, 타임아웃, 요청 수 제한, 폴링 횟수, 캐시 시간) | 임시값 | 권오현·신유빈 | 첫 기준 성능 시험 후 |
| 장애 감지·복구 성공 기준 숫자 | 12절 3번에 초안 | 신유빈·한다영 | 기준 시험 후 |
| 과거 구간 혼잡 DB (BFCL NLD-12) | 기능 없음으로 정리(BFCL과 같음) | 정예진 | 기능 추가 결정 시 |

---

## 12. 예진님 '수정 전 결정할 사항 6가지'에 대한 API·DB 쪽 제안

> 정예진 님 11/18 11:13 Discord 표. 아래는 **API·DB 설계 쪽에서 제안하는 답**이고, 팀이 확정하면 기획서·WBS에 반영합니다.

| # | 결정할 사항 | API·DB 제안 | 근거 |
|---|---|---|---|
| 1 | 실제 길찾기 API 선정 | **1차 TMAP · 2차 카카오맵**(11/19 D-038, 한태경 님 공식 문서 대조). ODsay는 한도·요금 미확인으로 뺌. 개발·부하 시험은 모의 어댑터만 | D-029·D-038 |
| 2 | 인증·DB 운영 방식 | **D-037(11/19): DB = AWS 위 Docker PostgreSQL 17 + pgvector, 인증 = FastAPI 자체 JWT**(Supabase 사용 안 함). 이전 제안: DB = Supabase PostgreSQL(확정). 인증 = **Supabase Auth 제안**(`profiles.user_id = auth.users.id`, RLS를 바로 쓸 수 있음). 쓰지 않으면 FastAPI JWT로 같은 규칙 | 기획서 v2.9, 04 문서 3·4절 |
| 3 | 장애와 복구 성공 기준 | **장애(초안)**: 귀가 조회 p95가 기준값을 30초 이상 넘거나, 대기열이 계속 늘거나, 시간초과·거절 비율이 기준을 넘을 때. **복구 성공(초안)**: 같은 부하 재측정에서 *검증된 경로 완료율*이 기준 이상이고 p95가 기준 아래. 숫자는 B0 기준 시험 뒤 확정. 대기열 접수·HTTP 200은 성공에 넣지 않음 | 0절 '접수 ≠ 완료', 7-2 |
| 4 | 실제 사용할 복구 조치 | 1차 후보 = **`singleflight_enable`(동일 요청 묶기)**. 단 **중복 키가 있을 때만**. 고유 키에서는 `bounded_queue_adjust`·`safe_degrade`·`defer`. 목록은 7-3 | 예비 실험, 강사 2차 의견 3 |
| 5 | DB 관계·감사 기록 정책 | 시뮬레이션 1회 : 사건 N건, 사건 1건 : 요청 N건. 사건 **상태 변경은 `incident_events`에 추가만** 하고(수정·삭제 금지), `incident_logs.status`는 최신 상태를 보여 주는 칸으로만 씀 | 04 문서 1·7절 |
| 6 | 1차 구현 범위 | 지역: 0-2절(D-020·D-022: 전국 데이터 = 전국, 지역별 데이터 = 서울만). 기능: 6절 표의 '1차 시연' 칸: **필수** = A01~A06, A14~A16, A18~A21. 나머지(시설·지도·날씨·교통·주차·RAG·관리자 수집)는 최종 | 6절 |

---

## 13. 외부 데이터 공급원과 지역 범위 (11/18 회의 반영)

> 키 발급 가이드·키 정리표의 기준 목록입니다. **실제 키 값은 이 문서에 적지 않습니다.** `scope`는 데이터가 존재하는 지역이고, 1차에 실제로 켜는 지역은 0-2절(D-022: 전국 데이터 = 전국, 지역별 데이터 = 서울만)을 따릅니다.

| 데이터 | 공급원 | `scope`(데이터가 있는 지역) | 실시간 | 쓰는 API | 회의 결정 |
|---|---|---|---|---|---|
| 축제 목록·상세 | 한국관광공사 TourAPI (국문 관광정보_GW) | national | 정기 수집 | A02·A03 | D-012·D-015 |
| 축제 보완 | 전국문화축제표준데이터 | national | 정기 수집 | A02·A03 | 조사 1절 |
| 축제 보완(서울) | 서울시 문화행사 OA-15486 | seoul_only | 정기 수집 | A02·A03 | D-019 |
| 날씨 | 기상청 단기예보·초단기실황 | national | 예 | A09 | D-012 |
| 혼잡 구역 | 서울시 실시간 인구 OA-21778 | seoul_only | 예 | A10, 경로 근거 | D-010 |
| 지하철 도착 | 서울 지하철 실시간 도착 | seoul_only | 예 | A26 | D-010 |
| 버스 도착(서울 밖) | 국토교통부 TAGO (서울 정류소 없음, 11/19 확인) | national(서울 제외) | 예 | A26 | D-010·D-022 |
| 버스 도착·차내 혼잡(서울) | 서울시 버스도착정보 15000314 (혼잡·`arsId`) | seoul_only | 예 | A26, `mode_evidence` | D-033 |
| 버스 차내 혼잡 | 서울시 버스 도착정보 혼잡·재차 인원 필드(후보, 확인 필요) | seoul_only | 예 | 교통수단 선택 근거(`mode_evidence`) | D-024·D-033 |
| 공영주차장 빈자리 | 서울 시영주차장 실시간 | seoul_only | 예 | A27 | D-010 |
| 주차장 위치 | 전국주차장정보표준데이터 | national | 아니요 | A08 | D-014 |
| 교통 돌발 | 경찰청 교통돌발정보 | national | 예 | A28, 경로 근거 | D-012 |
| 교통 통제(서울) | TOPIS 돌발·통제 | seoul_only | 예 | A07·A28 | D-019 |
| 길찾기 1차 | TMAP 대중교통 `POST /transit/routes` (무료 10건/일, 0.88원/건) | 문서에 지원 지역 목록 없음 → 지방 실호출로 확인 | 호출 시 계산 | A04·A25 | D-038 |
| 길찾기 2차 | 카카오맵 대중교통·도보 `GET /v2/routing/publictraffic` (무료 1,000건/일, 10원/건, 응답 저장 제한) | 같음 | 호출 시 계산 | A04·A25 | D-038 |
| 지도·장소 검색 | 카카오 지도·로컬 | national | — | 화면, 목적지 해석 | D-035 |
| 화장실 | 행정안전부 공중화장실정보 | national | 아니요 | A08 | D-014 |
| 병원·응급실 | 국립중앙의료원 | national | 위치만 | A08 | D-014 (약국은 보류, D-021) |
| 맛집·주변 관광지 | 카카오 로컬 | national | 아니요 | A08 | D-014 |
| 자전거 존 | 전국 공영자전거 실시간 정보(행정안전부, 확인 필요) — 안 되면 서울 따릉이 대여소 정보 | national(확인 시) / 아니면 seoul_only | 확인 필요(1차는 위치만, 실시간 대수는 나중에 — 6-1) | A08 | D-036 |
| 택시 승강장 | 전국 통합 공급원 조사 중 — 없으면 서울 공급원 | national(확인 시) / 아니면 seoul_only | 아니요(위치만) | A08 | D-036 |
| 지하철역·버스 정류장 위치 | 도시철도 노선정보·TAGO 정류소 | national | 아니요 | A08 | D-014 |
| 방문 집중 예측·지역 수요 | 한국관광공사 (집중률 예측·관광 수요 강도) | national | 30일 예측 | A29 | D-018 |
| 지도 | 카카오 지도 (프론트) | national | — | 화면 | D-035 |

---

## 14. 확장 지점 (D-034: 완성본이 아님)

**11/19 기획서 최신본에서 신규 필수 기능 2종(맞춤 추천 A36~A41, 동행·친구·채팅)이 정해졌습니다.** 이 문서는 이 기능들을 **기존 A01~A35 계약을 바꾸지 않고 추가만** 해서 붙입니다(6절 A36~A41, 상세는 v0.4).

| 확장 대상 | 붙이는 방법 | 지켜야 할 것 |
|---|---|---|
| 새 서비스 기능(예: 일행 찾기·명당 찾기·취향 맞춤) | `/api/v1/<기능 이름>/…` API 묶음 + 필요한 도구 + 테이블을 새로 추가, 6절 목록에 행 추가 | 기존 API·도구 이름·필드는 바꾸지 않음. 위치 공유처럼 개인정보가 생기면 동의·보존 정책을 04 문서에 먼저 씀 |
| 새 지역 | 표준 입력 형태 + 지역별 전처리 어댑터 추가, `data_sources.enabled_region_codes`에 지역 추가 | 데이터가 없는 지역은 `unsupported` 유지(D-023) |
| 새 공급원 | 같은 내부 형식의 어댑터 추가(0절 '공급원 어댑터') | 실호출로 확인 전에는 `unverified` |
| 새 에이전트 도구 | 4절 표에 추가하고 BFCL 문항 추가 여부 결정 | 평가가 시작된 문항의 정답은 바꾸지 않음 |
| 크롤링 보완(D-027, 멘토 권고) | 팀이 D-013(크롤링 제외)을 바꾸면 수집 작업 추가 | 지금은 **팀 결정 대기**, 이 문서 범위 밖 |

---

## 15. 기획서·WBS와 대조 (강사 일일 피드백 1)

**기획서 최신본(11/19 05:18 신유빈 님 공유, v3.1 다음판)** 과 이 문서 v0.3을 비교했습니다. 11/18 v2.9와 다르던 항목(DB·인증·길찾기·버스 혼잡)은 **기획서가 이미 v0.3 기준으로 고쳐졌습니다**.

| 항목 | 기획서 최신본 | API v0.3 | 판정 |
|---|---|---|---|
| DB·인증 | AWS Docker PostgreSQL 17 + pgvector, 자체 JWT 확정 | 같음(D-037) | ✅ |
| 길찾기 공급원 | 1차 TMAP · 2차 카카오맵(카카오 본문 미저장) | 같음(D-038) | ✅ |
| 버스 차내 혼잡 | 서울만, 교통수단 선택 근거 | 같음(D-033) | ✅ |
| 자전거 존·택시 승강장 | **둘 다** 전국 통합 공급원·좌표 확인 시 전국, 없으면 서울, 위치만 | v0.3 수정본에서 같게 고침 | ✅ (11/19 수정) |
| 고급 경로 5유형 | FR-R01 최단시간·R02 혼잡 회피·R03 교통약자·R04 최소 도보·R05 최소 환승(Should) | `route_preference` 5값을 같은 뜻으로 바꿈 | ✅ (11/19 수정) |
| `created` 상태 | 내부 상태, 화면은 `queued`부터 | API 응답에 `created` 없음(DB 내부만) | ✅ |
| 추적 ID | `X-Request-ID`·`run_id`·`agent_run_id`·`route_request_id`, `trace_id` 미도입 | 같음(0절) | ✅ |
| 기본 API | A01~A35 | 같음 | ✅ |
| 맞춤 추천 | A36~A41 설계안 | 6절에 목록만, 상세 v0.4 | ⏳ v0.4 |
| 동행·친구·채팅 | 계약 영역, 번호는 W112 | 6절에 메모만 | ⏳ v0.4 |
| 2차 공급원 비동기 전달 | 카카오 결과는 저장 불가 → 동기 전달만 | 5절 규칙·`ROUTE_SECONDARY_SYNC_ONLY` | ✅ (11/19 추가) |

**WBS(128개, 기획서 최신본 7절)와 대조**

| 항목 | WBS | API v0.3 | 판정 |
|---|---|---|---|
| 담당 | M02: R03 권오현 작성·취합, R06 신유빈 검토, 11/20 제출 | 같음 | ✅ (11/19 신유빈 님 검토 완료) |
| W10 실제 경로 응답 | 경로 원본 확보 → 검토 | TMAP·카카오맵 같은 좌표 비교 호출(10-1), 한태경 님 담당 | ✅ |
| 신규 W112~W128 | 추천·동행·친구·채팅 계약·구현·시험 | A36~A41 목록, 나머지 v0.4 | ⏳ |
| A31(부하 시험 조회) | — | 추가 | ⚠ W95/W96에 연결 요청 |

---

## 16. API 필드 ↔ DB 컬럼 대응 (1차 필수 API)

이름은 가능한 한 같게 썼고, 다른 것은 아래 표가 기준입니다. ID 형식은 0절과 같습니다.

| API 필드 | DB 컬럼 | 비고 |
|---|---|---|
| `request_id` | `route_requests.request_id` (UNIQUE) | 멱등 키 |
| `route_request_id` | `route_requests.route_request_id` (PK) | `rr_…` |
| `festival_id` | `route_requests.festival_id` → `festivals.festival_id` | `fst_…` |
| `destination` | `route_requests.user_place_hash` + `user_place_label` | **원문 저장 안 함**(해시·24시간 라벨) |
| `travel_mode` · `route_preference` · `user_constraints` | `route_requests.travel_mode` · `route_preference` · `constraints` | |
| `route_status` | `route_requests.status` | |
| `route_candidates[]` (근거 제외) | `route_results.candidates` (JSONB) | 후보·구간·점수 |
| 후보별 `area_evidence` · `mode_evidence` | `route_results.evidence` (JSONB: `{candidate_id: {area_evidence, mode_evidence}}`) | 근거는 이 컬럼 한 곳에만 저장, 응답 때 후보에 붙임 |
| `validity_check` (캐시·대체 경로) | `route_results.validity_check` | 7-5 |
| `stop_reason` · `rollback_reason` | `recovery_attempts.stop_reason` · `rollback_reason` | 7-5 |
| A02·A03 축제 필드(`name`·`venue_name`·`lat`·`lng`·`overview`·`fee_text`·`homepage_url`) | `festivals.title`·`venue_name`·`latitude`·`longitude`·`summary`·`admission_fee_text`·`official_url` | **이름 다름** — API 이름이 기준, DB는 위 컬럼 |
| A06 `run_id`·사용한 도구 | `agent_runs.run_id`·`tool_calls` | |
| A16 지표 필드 | `route_query_metrics` 같은 이름 (`phase` 포함) | |
| `provider` · `provider_tier` · `queried_at` | `route_results.provider` · `provider_tier` · `queried_at` | |
| `verification_status` | `route_results.validation_status` | 이름 다름(같은 값) |
| `is_mock` | `route_requests.is_mock`, `route_results.is_mock` | |
| `incident_id` | `incident_logs.incident_id` | `inc_…` |
| `failure_domain` · `status` · `detected_at` | `incident_logs` 같은 이름 | |
| `decision` · `action` · `reasons` · `rejected_actions` · `stop_condition` · `evidence_refs` | `recovery_plans` 같은 이름 | |
| `plan_id` · `attempt_id` | `recovery_plans.plan_id` · `recovery_attempts.attempt_id` | `rp_…` · `ra_…` |
| `final_mode` | `incident_outcomes.final_mode` | |
| `simulation_id` · `comparison_arm` · `scenario` 등 부하 조건 | `load_simulations` 같은 이름 | `sim_…` |


---

## 변경 이력

| 버전 | 날짜 | 바뀐 점 |
|---|---|---|
| v0.1 | 2026-11-17 | 첫 초안 (A01~A24, 도구 13개, 부록 A) |
| v0.2 | 2026-11-18 | **11/18 회의 반영**: A25~A30 추가(가는 길·지하철/버스 도착·공영주차장·교통 돌발·방문 집중 예측·데이터 지원 범위), A08 지도 표시 1차 10종(물품보관함·약국 보류, D-021), A03 입장료·소개, 경로 `evidence`(혼잡 구역·교통 돌발·버스 혼잡), 제외 항목 6-1절, 외부 공급원 13절, 지역 코드 0-1절·`coverage`·`REGION_UNSUPPORTED`, ODsay 일일 한도. **BFCL 맞춤**: `failure_domain` 값을 `route_upstream`·`crowd_upstream`으로 통일, 지역 값 `SEOUL`/`ALL`, 평가용 ID 설명, 부록 A 삭제(BFCL 문서가 기준). **기획서 v2.8 맞춤**: Supabase PostgreSQL 확정, Supabase Auth 제안. **강사 2차 의견**: 부하 시험 `cache_state`·`repeat_group`·`run_index`, 시뮬레이션 1회 : 사건 N건, 고유 키에서 병합 기각. 12절 예진님 6가지 결정 사항 제안 추가. **회의록 대조(11/18)**: 물품보관함·약국 보류(D-021), ODsay 결정 확인(사용자), 버스(TAGO)는 1차 서울만. **서비스 범위 D-020(멘토)·D-022(팀)**: 0-2절 — 전국에 있는 데이터는 전국, 지역별로만 있는 데이터는 서울만, 설정으로 지역 확대 |
| v0.3 | 2026-11-19 | **11/19 한태경 님 TMAP↔카카오맵 확인 반영**: 좌표 순서 변환, 정류장 연결 규칙, `service_running`(막차), TMAP 데이터 24시간 사용 제한. **기준**: 강사 일일 피드백(11/19) 5개, 멘토 2차 회의, 결정 D-033~D-039, 수업 가이드 「API 설계 문서 작성법」, 기획서 최신본(11/19). **공통**: 머리말(정본·진행 단계·검토 기록·서버 주소·`/docs`), 경로 `/api/v1`, ID 형식 통일(`trace_id` 미도입), 422(형식)와 400/403/409(서버 판단) 경계. **DB·인증(D-037)**: AWS Docker PostgreSQL, 자체 JWT, 인증 API A32~A35. **길찾기(D-038·D-039)**: 1차 TMAP · 2차 카카오맵(ODsay 제외), 카카오 결과는 저장·캐시 안 함·동기 전달만(`ROUTE_SECONDARY_SYNC_ONLY`), 공급원별 한도·비용 상한, 같은 좌표 비교 호출 계획, TMAP 정류장 ID로 버스 혼잡 연결. **상세 명세**: A04·A05·A19 8칸 + 필드 표, A02·A03·A15·A20 필드 표, A31 추가. **경로**: 근거를 지역 선택·교통수단 선택으로 분리, 추천 기준 5유형(기획서 FR-R01~R05와 같은 이름). **범위**: 버스 차내 혼잡 서울만(D-033), 자전거 존·택시 승강장 전국 공급원 없으면 서울(D-036), '확인 불가' 표시 규칙. **도구**: 공통 출력(`ok`·`retryable`)·실패 뒤 처리·description·JSON Schema 2개, BFCL 대조표. **복구 시험**: 세 구간 × 세 대응 방식, 재검증·종료 기준. **실호출 근거**: 11/19 한태경 님 10종(10절). **신규 기능**: A36~A41 목록(상세 v0.4). **검토**: AI 교차 검토 25건, 신유빈 님 검토(11/19), 정예진 님 피드백 6건 반영 |
| v0.3.1 | 2026-11-19 | **v0.3(팀 문서함 1차 업로드본) 이후 수정분**: 신유빈 님 검토 4건(변경 이력 정리·택시 범위·`trace_id` 미도입·최신 기획서 대조와 신규 기능 표기), 정예진 님 피드백 6건(경로 5유형 = FR-R01~R05, `created` 내부 상태, 카카오 2차 동기 전달만 `ROUTE_SECONDARY_SYNC_ONLY`), 한태경 님 TMAP↔카카오맵 확인(좌표 순서, 정류장 연결 규칙, `service_running`, TMAP 24시간 사용 제한), A36~A41 목록 |
