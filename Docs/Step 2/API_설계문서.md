# 03. API 설계 문서

놀다가(NOLDAGA) / 3팀 수다수다 | 문서 버전 **v0.7** | 작성 상태: **제출본**

문서명: REST API 및 Function Calling 명세서

## 1. 문서 개요

- **서비스 범위:** 놀다가는 전국 축제 탐색, AI 안심 귀가, 귀가 조회 장애 자동 복구를 핵심 기능으로 하고, 맞춤 추천·친구·동행·채팅·알림·방문 코스·관리 기능을 추가 기능으로 둡니다.
- **이 문서가 정하는 것:** 내부 API의 경로, 요청·응답 필드, 오류 코드, 검증·권한 규칙, 에이전트 Tool 정의와 실행 규칙(계약)입니다.
- **읽는 순서:** 공통 규칙(2절) → 전체 API 목록(3절) → 핵심 서비스 흐름(4절) → 장애 대응(5절) → AI Tool(6절) → 추가 기능(7절) → 검증·실행 규칙(8절).
- **설계·구현·검증 상태 구분:** 이 문서는 계약(설계)만 적습니다. 각 API가 실제로 구현·연동·검증됐는지, 실호출 근거와 미확인 항목은 [API 구현·검증 기록](API_구현_검증기록.md)에서 확인합니다.


### 1-1. 문서 정보

| 항목 | 내용 |
|---|---|
| **정본(이 문서의 기준 위치)** | GitHub `yubeenjjang/Final3team` → `Docs/Step 2/API_설계문서.md`. **이 경로만 정본**이며 로컬 파일·Discord 첨부는 사본입니다. 대시보드 제출 링크도 이 경로를 씁니다 |
| 짝 문서 | `Docs/Step 2/DB_스키마_설계서.md` v0.7 (같은 ID 형식·필드↔컬럼 대응은 3-2절) |
| 구현·검증 기록 | [`Docs/Step 2/API_구현_검증기록.md`](API_구현_검증기록.md) — 진행 단계·제출 기준 커밋·배포 주소, 검토 기록, 피드백 반영표([기록 0-A](API_구현_검증기록.md#0-a-강사-1120-피드백-반영표-v05-2026-11-24)), 실호출 근거([기록 10](API_구현_검증기록.md#10-실제-호출-근거-현재-확보분)), 미확인 항목([기록 11](API_구현_검증기록.md#11-미확인-항목확인-계획)), 공급원([기록 13](API_구현_검증기록.md#13-외부-데이터-공급원과-지역-범위-1118-회의-반영)), 기획서 대조([기록 15](API_구현_검증기록.md#15-기획서wbs와-대조-강사-일일-피드백-1)), 실행 기록([기록 17](API_구현_검증기록.md#17-실행-확인-첫-흐름을-모의에서-실제로-강사-1120-api-12-2026-11-23)), 결정 기록([기록 19](API_구현_검증기록.md#19-결정-반영-기록-강사-1120-api-4)), 시험 추가 기록([기록 20](API_구현_검증기록.md#20-시험-추가-기록-설계-문서에서-옮김)). 이 문서에서 '기록 N절'은 그 문서의 절입니다 |
| 목차 | 1 문서 개요 · 2 공통 규칙(2-4 인증 방식·2-5 인증 API) · 3 전체 API 목록(3-0 상태 확인 A01·3-1 범위에서 뺀 것·3-2 필드↔DB·3-3 공통 오류 코드) · 4 핵심 서비스 흐름 API(A02→A03→A04 대표→A05→A25) · 5 장애 대응 API · 6 AI Tool(6-8 도구 호출 정의·6-9 챗봇 A06) · 7 추가 기능 API · 8 검증·실행 규칙과 변경 이력(8-1 Pydantic·8-2 정보 전달 범위·8-3 실행 규칙·8-4 제한값) |
| 기준 문서 | [놀다가 기획서](../Step%201/놀다가_기획서.md) · [WBS](../Step%201/놀다가_WBS.md) · 팀 자체 평가 30문항(이하 BFCL) · 17개 시·도 데이터 조사 · 수업 가이드 「API 설계 문서 작성법」 |
| 범위 | **핵심 기능**(전국 축제 탐색 + AI 안심 귀가 + 귀가 조회 장애 자동 복구, 4~6절) + **추가 기능**(맞춤 추천·지금 핫한 축제·요즘 올라온 글·친구·동행·채팅·알림·신고·마이페이지·AI 방문 코스·공지·축제 관리, A36~A81 — 7절, 작업 순서는 [기록 6-3](API_구현_검증기록.md#6-3-추가-기능-범위작업-순서-강사-1119-피드백-5)절). 그 밖의 새 기능은 [기록 14](API_구현_검증기록.md#14-확장-지점-d-034-완성본이-아님)절 '확장 지점' 규칙으로 붙입니다 |

> **이 문서의 모든 API는 설계안입니다.** 구현·외부 공급원 연동·배포가 끝났다는 뜻이 아닙니다. 미확인 항목은 [기록 11](API_구현_검증기록.md#11-미확인-항목확인-계획)절, 기획서와 다른 점은 [기록 15](API_구현_검증기록.md#15-기획서wbs와-대조-강사-일일-피드백-1)절, 바뀐 점은 맨 아래 '변경 이력'에 있습니다.

### 1-2. 공통 정보

| 항목 | 내용 |
|---|---|
| 개발 서버 | `http://localhost:8000/api/v1` |
| 배포 서버 | AWS Docker. 실제 주소와 준비 상태는 [API 구현·검증 기록 '진행 상태'](API_구현_검증기록.md#진행-상태-설계서-머리말에서-옮김--병합제출시험-때-여기만-갱신)에 적습니다(주소가 정해져도 이 문서는 바뀌지 않음) |
| 자동 문서 | 개발: `http://localhost:8000/docs`(Swagger UI), `http://localhost:8000/openapi.json` — API 기본 경로(`/api/v1`)가 아니라 **서버 루트**에 있음(FastAPI 기본값, `backend/api/main.py`). 구현 후 이 문서와 대조하고, 다르면 문서 버전을 올립니다 |
| 인증 | `Authorization: Bearer <JWT>` (2-4절) |
| 오류 형식 | 모든 API 공통 (2절) |
| 시각 | ISO 8601 + `+09:00`(KST) |

---

## 2. 공통 규칙 (설계 원칙·ID 형식·오류 형식 — 모든 API 공통)

| 원칙 | 내용 | 근거 |
|---|---|---|
| 내부 API와 외부 공급원 분리 | 화면·에이전트는 **놀다가 내부 API만** 부릅니다. 외부 API(TourAPI·TMAP·카카오·서울시·TAGO·경찰청 등)는 백엔드 어댑터만 호출합니다. 축제 목록은 수집된 DB에서 제공하고 요청마다 외부 API를 부르지 않습니다 | 기획서 5.12 |
| 접수 ≠ 완료 | `queued`·`accepted`는 경로 제공 성공이 아닙니다. 검증을 통과한 경로가 응답에 담길 때만 `ready` | FR-R14, FR-H24 |
| 모의/실제 구분 | 시험용 경로 어댑터·장애 주입으로 만든 응답은 항상 `is_mock=true`, `test_mode` 표기 | 기획서 3.6, 5.17 |
| 출처·시각 표시 | 외부 데이터가 들어간 응답에는 `provider`(또는 `source`), `queried_at`/`observed_at` 필수 | FR-R08, FR-C06 |
| **지역 지원 범위 표시** | 외부 데이터 응답에는 `coverage`를 넣습니다. 그 지역에 데이터가 없으면 오류가 아니라 `status:"unsupported"`로 돌려주고 화면은 '이 지역은 미지원'으로 표시합니다. 다른 지역 값으로 채우지 않습니다 | 데이터 조사 3절 |
| 에이전트는 제안, 코드는 실행 | 복구 조치는 에이전트가 고르고(`select/reject/defer/rollback`) **정책 코드가 allowlist·상한을 검사한 뒤 실행**합니다. 에이전트가 직접 실행하는 도구는 없습니다 | FR-H05, 기획서 6.22 |
| 장애 격리 | 귀가 조회 부하·외부 API 장애·LLM 장애가 축제 검색·상세를 멈추지 않게 엔드포인트와 작업 풀을 분리 | FR-H18, FR-C09, NFR-12 |
| 비밀정보 | 외부 API 키는 서버 환경변수에만 둡니다. 응답·로그·저장소·문서에 노출 금지 | NFR-09 |
| **공급원 어댑터** | 같은 데이터를 주는 공급원(예: 길찾기 1차 TMAP · 2차 카카오맵 · 모의)은 **같은 내부 형식**으로 바꿔 돌려주는 어댑터 뒤에 둡니다. 공급원을 바꿔도 내부 API 응답은 같습니다 | — |
| **외부 공급원 보호** | 실제 외부 API에는 부하 시험·반복 개발 호출을 하지 않습니다. 개발·부하 시험은 실제 응답 구조를 본뜬 모의 응답만 씁니다([기록 10](API_구현_검증기록.md#10-실제-호출-근거-현재-확보분)절 최소 호출 계획) | — |
| **확장 가능** | 지금 문서는 완성본이 아닙니다. 새 서비스 기능은 기존 계약을 바꾸지 않고 API 묶음·도구·테이블을 **추가**하는 방식으로 붙입니다([기록 14](API_구현_검증기록.md#14-확장-지점-d-034-완성본이-아님)절) | — |

**공통 규칙**
- 기본 경로: **`/api/v1`** (수업 가이드 S10. 규격이 깨지게 바뀌면 `/api/v2`를 새로 열고 `v1`은 유지). 경로는 소문자·하이픈, 자원은 복수형 명사. 형식: JSON, UTF-8, 시각은 ISO 8601 + `+09:00`. ID는 접두사+ULID가 기본이고, 예외는 `user_id`(UUID)와 `message_id`·`notification_id`·A24 `queue_id`(64비트 정수)입니다.
- **검증 오류의 경계**: 입력 **형식**(타입·허용값·길이·패턴)은 Pydantic이 검사하고 **422 `VALIDATION_ERROR`**. 형식은 맞지만 서버가 판단해야 하는 것은 따로: 권한·소유권은 **403**, 대상 없음은 **404**, 중복·충돌은 **409**, 해석 불가(목적지를 찾을 수 없음 등)는 **400**. 두 검사를 섞지 않습니다(수업 가이드 S19·S31). FastAPI 기본 422 응답도 공통 오류 형식으로 바꾸는 예외 핸들러를 둡니다.
- **ID 형식(두 문서 공통)**: 기본은 `소문자 접두사_` + ULID(예외는 바로 위 문장) — `fst_`(축제) · `rr_`(경로 요청) · `inc_`(사건) · `diag_`(진단) · `rp_`(복구 계획) · `ra_`(복구 시도) · `sim_`(부하 시험) · `run_`(에이전트 실행 묶음) · `ar_`(에이전트 1회 실행) · `cv_`(대화 세션, LangGraph `thread_id`) · `rv_`(후기) · `rt_`(Refresh Token). `request_id`(경로·챗봇 요청 본문의 **멱등 키**)는 클라이언트가 만드는 8~64자 문자열(UUID 권장, 코드 `RouteRequest`·`AssistantRequest`). 서버가 만드는 자원 ID는 모두 `접두사_` + ULID 26자이고, 형식 검사는 `접두사_[0-9A-Za-z]{6,26}`을 허용합니다. 조회 토큰(`rrt_`·`rat_`)은 ID가 아니라 무작위 비밀값이라 ULID를 쓰지 않습니다. **추적 ID**(`X-Request-ID` 헤더·로그·오류 응답의 `request_id`)는 `req_` + ULID로, 둘은 다른 값입니다. BFCL의 `F01`·`RR02`·`INC-003`은 평가용 가짜 ID입니다([기록 4-7](API_구현_검증기록.md#4-7-bfcl-30문항과의-대조-강사-일일-피드백-5)절). **별도 `trace_id`는 도입하지 않습니다** — 추적은 `X-Request-ID`(`req_`) → `run_id` → `agent_run_id` → `route_request_id`·`incident_id`를 이어서 합니다(기획서 최신본과 같음).
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

`scope`는 `national`(전국 공통) / `seoul_only`(서울만) / `region_specific`(일부 시·도) 중 하나입니다([기록 13](API_구현_검증기록.md#13-외부-데이터-공급원과-지역-범위-1118-회의-반영)절 표).

### 2-1. 지역 코드

| 코드 | 시·도 | 코드 | 시·도 | 코드 | 시·도 |
|---|---|---|---|---|---|
| `ALL` | 전체(검색 기본값) | `SEOUL` | 서울 | `BUSAN` | 부산 |
| `DAEGU` | 대구 | `INCHEON` | 인천 | `GWANGJU` | 광주 |
| `DAEJEON` | 대전 | `ULSAN` | 울산 | `SEJONG` | 세종 |
| `GYEONGGI` | 경기 | `GANGWON` | 강원 | `CHUNGBUK` | 충북 |
| `CHUNGNAM` | 충남 | `JEONBUK` | 전북 | `JEONNAM` | 전남 |
| `GYEONGBUK` | 경북 | `GYEONGNAM` | 경남 | `JEJU` | 제주 |

- BFCL의 `region="SEOUL"`·`region="ALL"`과 같은 값입니다. TourAPI는 `areaCode`가 아니라 **법정동 시·도 코드 `lDongRegnCd`** 로 지역을 받습니다(서울 11, 부산 26 — [기록 10](API_구현_검증기록.md#10-실제-호출-근거-현재-확보분)절).

### 2-2. 서비스 범위

**기준: 전국에 있는 데이터는 전국으로, 지역별로만 있는 데이터는 서울만** 씁니다.

축제 검색·상세는 축제만 제공합니다. TourAPI는 `lclsSystm2=EV01`만 공개 대상으로 삼습니다. 공연(`EV02`), 박람회·마켓·전시 등 행사(`EV03`), 미분류 항목은 수집 후 검토 대기로 보관합니다.

| 구분 | 1차 범위 | 데이터·API |
|---|---|---|
| **전국 공통 데이터** (정적·실시간 모두) | **전국** | 축제 검색·상세(A02·A03, TourAPI·전국문화축제표준데이터), 지도·장소 검색(카카오), 지도 시설 위치(A08), 날씨(A09, 기상청), 버스 도착(A26 버스: **서울 밖은 TAGO, 서울은 서울시 버스도착정보**), 교통 돌발(A28 경찰청), 길찾기 귀가·가는 길(A04·A05·A25: **1차 TMAP, 2차 카카오맵**), 방문 집중 예측·지역 수요(A29), 주변 상권(카카오 로컬), **자전거 존·택시 승강장** |
| **지역별로만 있는 데이터** | **서울만** | 혼잡 구역(A10, OA-21778 — **지도 표시 + 귀가 근거**), 지하철 실시간 도착(A26 지하철), TOPIS 통제(A07·A28 보강), 서울 문화행사(A02·A03 보강), **버스 차내 혼잡(교통수단 선택 근거)** |
| 부하·장애 시뮬레이션 | 서울 축제 기준 | A20~A22 |
| 서울 밖 시·도 자체 데이터 (대구 돌발·주차, 대전 축제, 비짓제주 등) | 1차 사용 안 함 | 지역마다 형태가 달라 서울 먼저. 나중에 기능별로 확대 |

- 서울만 켜는 데이터는 `data_sources.enabled_region_codes`(04 문서)에 `SEOUL`만 넣어 둡니다. 서울 밖 축제에서 부르면 오류가 아니라 `status:"unsupported"`(`REGION_UNSUPPORTED`)로 답하고, 화면은 '이 지역은 아직 지원하지 않아요'로 표시합니다. 지역을 넓힐 때는 **이 값에 지역을 추가하는 것만으로** 됩니다.
- 그래서 **부산 축제**에서도 축제 정보·지도·날씨·버스 도착·교통 돌발·**귀갓길 안내**는 나오고, 혼잡도·지하철 도착은 '미지원'으로 표시됩니다.
- 귀갓길 경로 근거(`evidence`)도 같은 기준입니다: 교통 돌발은 전국, 혼잡 구역·버스 차내 혼잡은 서울만.
- **지역 범위를 정하는 규칙:** 한 공급원에서 전국을 한 번에 불러올 수 있으면 전국, 지역마다 공급원이 따로면 서울만. 개발은 서울 기준으로 하고, 다른 지역은 표준 입력 형태 + 지역별 전처리로 나중에 붙입니다.

### 2-3. '확인 불가' 표시 규칙

데이터가 없거나 믿을 수 없을 때는 **다른 값으로 채우지 않고** 아래처럼 구분해 표시합니다. 지도에 넣을 수 있다는 것만으로 기능 완료로 보지 않습니다.

| 경우 | 응답 | 화면 문구(초안) |
|---|---|---|
| 서울 한정 데이터를 서울 밖 축제에서 요청 | `status:"unsupported"`, `REGION_UNSUPPORTED` | 이 지역은 아직 지원하지 않아요 |
| 공급원은 있으나 관측 시각이 오래됨(기준: 공급원 갱신 주기의 2배, 초기값) | `status:"stale"`, `SOURCE_STALE`, `observed_at` 그대로 | ○분 전 정보라 지금과 다를 수 있어요 |
| 공급원 오류·한도 소진 | `status:"unavailable"`, `SOURCE_HTTP_ERROR` 등 | 지금은 확인할 수 없어요 (공식 안내 링크) |
| 공급원 미확인(아직 실호출·검증 전) | `status:"unverified"` | 준비 중인 정보예요 |
| 모의 데이터 | `is_mock:true` | 시험용 자료 표시 |

### 2-4. 인증 방식

수업 가이드의 네 줄(인증·전달·검증·오류) 기준입니다. **DB는 AWS 위 Docker PostgreSQL, 인증은 FastAPI 자체 JWT**입니다(Supabase 사용 안 함).

| 항목 | 명세 |
|---|---|
| **인증(발급)** | `POST /api/v1/auth/login`(이메일·비밀번호) → Access JWT(30분, `sub`·`role`·`jti`) + Refresh Token(14일). 갱신은 `POST /api/v1/auth/refresh`(Refresh를 쓸 때마다 새로 발급, 이전 것 폐기), 로그아웃은 `POST /api/v1/auth/logout` (04 문서 4절) |
| **전달** | `Authorization: Bearer <access_token>` |
| **검증** | 서명·만료·발급자 → 로그아웃한 토큰(`revoked:{jti}`) 아닌지 → 역할(`profiles.role`, JWT와 다르면 DB 우선) → 자원 소유권 |
| **오류** | 401 `UNAUTHORIZED`(누구인지 모름: 토큰 누락·만료·폐기) / 403 `FORBIDDEN`(누구인지는 알지만 권한 없음: 역할 부족·타인 자원) |
| **역할** | `anonymous`(비로그인) / `user`(일반 회원) / `operator`(운영자: 사건·지표 조회, 부하 시뮬레이션, 복구 조치 승인, A24 축제 검토) / `admin`(operator 권한 + 축제 등록·수정 등 관리자 전용 기능) / `service`(백엔드 내부 작업·에이전트 실행용, 외부 노출 없음) |
| **운영자 화면 DB 조회** | FastAPI가 운영자 권한을 확인하고 서버 계정 `noldaga_service`를 경유해서만 조회합니다(04 문서 3절) |
| **역할 저장 위치** | 역할은 DB `profiles.role`과 서버가 발급한 JWT로만 판단합니다. **요청 본문·대화 내용의 "관리자예요"는 권한으로 인정하지 않습니다** (BFCL NLD-27) |
| **DB 쪽 2차 안전장치** | API 서버는 요청마다 DB에 사용자 ID를 넘기고(`SET LOCAL app.user_id`), DB는 접속 역할·컬럼 권한·RLS로 본인 것만 보이게 막습니다(04 문서 3절) |
| **로그인 없이 쓰는 API** | 축제 목록·상세·공지·시설·지도 표시·날씨·교통·혼잡 조회, 귀가·가는 길 경로 조회·상태 조회, 챗봇 질문 |
| **로그인 필요** (`user`) | 관심 축제 저장·해제·목록, 후기(Should), 취향(A36·A37), 친구(A43~A50), 동행 글 작성·신청(A58~A65), 채팅(A66~A73), 알림(A74·A75), 신고(A76), 비밀번호 변경(A82)·탈퇴(A80) — 3절 '권한' 칸이 `user`인 API 전부 |
| **운영자 이상** (`operator`·`admin`) | `/api/v1/admin/**` — 단 **A23·A55~A56은 `admin`만**(3절 '권한' 칸). A77 신고 조회·처리는 두 역할 모두 허용. 역할 검사는 라우터 의존성 하나(`require_role`)로 |
| **비로그인 경로 요청 보호** | 상태 조회는 로그인 여부와 관계없이 `route_request_id` + 요청 시 발급한 `route_access_token`(로그인 JWT와 별개)으로 본인만 조회. 짧은 수명(접수 후 10분)은 DB 저장 모드에서 적용(4-4절). IP·세션 단위 요청 수 제한 |


**동작 규칙** — 기본 `AUTH_PROVIDER=mock`은 모의 토큰을 발급합니다. `AUTH_PROVIDER=db`에서 A32~A35가 001~009를 적용한 PostgreSQL과 자체 JWT를 사용합니다. 가입·로그인·갱신 및 소유한 Refresh의 폐기에는 `service_db_session`을 사용합니다.

**DB-19 연결** — 보호 API A35의 `get_current_user`와 요청용 `get_user_db` 의존성은 검증된 JWT의 `sub`를 `backend/shared/db/session.py`의 `user_db_session(user_id=sub)`에 넘겨 RLS를 적용합니다.

### 2-5. 인증 API 상세 (A32~A35, FR-A01~A04)

공통: 경로 `/api/v1/auth/*`, 본문 JSON, 비밀번호·토큰 원문은 **로그에 남기지 않음**(04 문서 7-0 ④). 로그인 요청 수 제한은 IP당 분당 10회(`AUTH_RATE_LIMIT_PER_MIN`, 8-4 ⑤). 오류 형식은 2절 공통 오류 형식과 같음(오류 코드는 3-3절 공통 오류 코드 표).

| API | 요청 | 정상 응답 | 검증·처리 규칙 | 오류 | 저장·처리 |
|---|---|---|---|---|---|
| **A32** `POST /auth/signup` | `{email, password, display_name, birth_year, gender}` **모두 필수**(시나리오 S03) — 이메일 형식·254자 이하, 비밀번호 8~64자(영문·숫자 포함), **닉네임(`display_name`) 2~12자·대소문자 무시 중복 불가**, 출생연도 1900~올해, 성별 `male`·`female`, 닉네임은 제어문자를 거부하고 앞뒤 공백 제거 후 길이를 검사 | **201** `{user_id, display_name}` (로그인은 따로 A33) | 이메일은 소문자로 바꿔 비교. 비밀번호는 argon2id로 해시만 저장. **한 트랜잭션**에서 `users`(status `active`) + `profiles`(role `user`, 닉네임·출생연도·성별) 생성. 나이·성별은 **동행 신청 때 그 모집 글 작성자에게만** 보임(A61, DB `app_applicant_profile`) | 422 형식 / 409 `EMAIL_ALREADY_EXISTS`·`NICKNAME_TAKEN` / 429 | DB에 계정·프로필을 한 트랜잭션으로 저장 |
| **A33** `POST /auth/login` | `{email, password}` | **200** `{access_token, token_type:"bearer", expires_in:1800, refresh_token, refresh_expires_at, user:{user_id, display_name, role}}` | 계정 `status='active'`만. 실패 이유를 구분하지 않음(이메일 존재 여부 노출 금지). 성공 시 `users.last_login_at`, `refresh_tokens`에 **해시만** 저장(14일) | 401 `INVALID_CREDENTIALS` / 403 `ACCOUNT_DISABLED` / 429 `RATE_LIMITED` / 503 `AUTH_CHECK_UNAVAILABLE` | DB에 로그인 시각·Refresh 해시 저장, IP별 로그인 제한 |
| **A34** `POST /auth/refresh` | `{refresh_token}` | **200** A33과 같은 토큰 묶음(새 Access + **새 Refresh**) | **교체 방식**: `refresh:lock:{token_id}`(5초)로 동시 교체 방지 → 기존 행 `revoked_at` 기록 → 새 행 추가(한 트랜잭션). **이미 폐기된 Refresh가 다시 오면 재사용으로 보고 그 사용자의 Refresh 전부 폐기** | 401 `REFRESH_INVALID`(없음·만료) / 401 `REFRESH_REUSED`(재사용 — 다시 로그인) / 409 `REFRESH_IN_PROGRESS`(잠금 중) / 503 `AUTH_CHECK_UNAVAILABLE` | DB 트랜잭션으로 교체·재사용 폐기 |
| **A35** `POST /auth/logout` | 헤더 Access JWT + 본문 `{refresh_token}` | **204** | 그 Refresh 행 `revoked_at` + Access의 `jti`를 `revoked:{jti}`(남은 수명만큼)에 넣음 → 이 기기만 로그아웃. 그 계정의 Refresh를 모두 폐기하는 경우는 탈퇴(A80, 남은 Access도 계정 상태 검사로 거부)·비밀번호 변경(A82)·Refresh 재사용 감지뿐 | 401 / 503 `AUTH_CHECK_UNAVAILABLE` | 본인 Refresh 폐기, Access jti 만료까지 차단 |

**A32 회원 가입 (201)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `email` | body | string | 예 | 254자 이하, 이메일 형식, 로컬 부분 64자 이하, 점으로 구분된 도메인 레이블 2개 이상, 소문자로 정규화 |
| `password` | body | string (SecretStr) | 예 | 8~64자, 영문과 숫자를 각각 1개 이상 포함 |
| `display_name` | body | string | 예 | 제어문자 없이 앞뒤 공백 제거 후 2~12자, 대소문자 무시 중복 불가 |
| `birth_year` | body | int | 예 | 1900 이상 올해 이하 |
| `gender` | body | string | 예 | `male`·`female` |
| `user_id` | 응답 | string (UUID) | 예 | 생성된 사용자 ID |
| `display_name` | 응답 | string | 예 | 저장한 닉네임 |
| `is_mock` | 응답 | boolean | 예 | 모의 모드는 `true`, DB 모드는 `false` |

**A33 로그인·A34 갱신·A35 로그아웃 요청**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `email` | body | string | A33 예 | 로그인 계정 이메일 |
| `password` | body | string (SecretStr) | A33 예 | 로그인 비밀번호 |
| `refresh_token` | body | string (SecretStr) | A34·A35 예 | A34는 교체할 토큰, A35는 폐기할 토큰 |
| `Authorization` | header | string | A35 예 | `Bearer` Access 토큰 |

**A33·A34 공통 정상 응답 (200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `access_token` | 응답 | string | 예 | 로그인 또는 갱신으로 발급한 Access 토큰 |
| `token_type` | 응답 | string | 예 | `bearer` |
| `expires_in` | 응답 | int | 예 | Access 유효 시간(초), 1800 |
| `refresh_token` | 응답 | string | 예 | 새로 발급한 Refresh 토큰 |
| `refresh_expires_at` | 응답 | string(date-time) | 예 | Refresh 만료 시각 |
| `user` | 응답 | object | 예 | 사용자 정보 |
| `user.user_id` | 응답 | string (UUID) | 예 | 사용자 ID |
| `user.display_name` | 응답 | string | 예 | 닉네임 |
| `user.role` | 응답 | string | 예 | 모의 모드는 `user`, DB 모드는 `profiles.role` |
| `is_mock` | 응답 | boolean | 예 | 모의 모드는 `true`, DB 모드는 `false` |

- **보호 API의 인증 순서:** 서명·만료·발급자 검증 → `revoked:{jti}` 확인 → 역할 확인. **Redis 장애로 `revoked` 확인이 안 되면** 읽기 API는 그대로 처리하고, 쓰기·관리자 API는 503 `AUTH_CHECK_UNAVAILABLE`(안전 쪽). DB 모드에서 같은 규칙을 현재 메모리 어댑터와 이후 Redis 어댑터의 인터페이스 오류에 적용합니다.
- **탈퇴·정지 계정:** Access JWT가 남아 있어도 보호 API마다 `users.status='active'`를 확인합니다(탈퇴 직후 30분 동안 쓰는 것 방지).

---

## 3. 전체 API 목록

| # | 메서드 | 경로 | 인증 | 설명 | 관련 FR | 1차 시연 |
| --- | --- | --- | --- | --- | --- | --- |
| A01 | GET | `/api/v1/health` | 없음 | 서버·DB·Redis 상태 | — | 필수 |
| A02 | GET | `/api/v1/festivals` | 없음 | 축제 검색(`region` 코드·기간·키워드·상태·지도 범위 `bbox`) | FR-F01/F10/F15 | **필수** |
| A03 | GET | `/api/v1/festivals/{festival_id}` | 없음 | 축제 상세(장소·좌표·기간·**간단한 소개·입장료**·출처·`last_synced_at`) | FR-F01, D11 | **필수** |
| A04 | POST | `/api/v1/routes/return` | 없음 | **AI 안심 귀가 경로 요청** (4-3절) | FR-R13~R17 | **필수(대표)** |
| A05 | GET | `/api/v1/routes/return/{route_request_id}` | 요청 토큰 | 귀가 요청 처리 상태·결과 | FR-R14 | **필수** |
| A06 · A06-1 · A06-2 | POST / GET / GET | `/api/v1/assistant/query` · A06-1 `/api/v1/assistant/runs/{run_id}` · A06-2 `…/{run_id}/events`(SSE) | 없음(선택 로그인). A06-1·A06-2는 로그인해서 만든 작업이면 작업 주인의 Access JWT, 비로그인 작업이면 로그인하지 않은 상태로 `X-Run-Access-Token` | 챗봇 질문을 **작업으로 등록 → 202 + `run_id`**, 워커가 에이전트 실행. 결과(`answer`·사용한 도구·근거)는 상태 조회로 (6-9) | FR-C01~C09 | 귀가 안내 한정 |
| A07 | GET | `/api/v1/festivals/{festival_id}/notices` | 없음 | 공식 운영 공지·교통통제(무정차·우회 등). `type` 필터 | FR-F05/F13 | 최종 |
| A08 | GET | `/api/v1/festivals/{festival_id}/facilities` | 없음 | **지도 표시용 주변 시설**(`categories` 여러 개, `radius_m`). **1차 10종**: 화장실·주차장 위치·병원·응급실·지하철역·버스 정류장·자전거 존·택시 승강장(**둘 다** 전국 통합 공급원·좌표가 확인되면 전국, 없으면 검증된 서울 공급원으로, **위치 안내만** — 실시간 대여 가능 수·택시 호출 제외)·맛집·주변 관광지 (**보류**: 물품보관함¹·약국²). 공급원 미확인 항목은 `status:"unverified"`(2-3절) | FR-F04/F11 | 최종 |
| A09 | GET | `/api/v1/festivals/{festival_id}/weather` | 없음 | 축제 위치 날씨·예보(발표 시각 포함, 기상청 전국) | FR-F09 | 최종 |
| A10 | GET | `/api/v1/festivals/{festival_id}/crowd` | 없음 | 축제에 연결이 승인된 서울시 공식 구역 중 1km 이내 최대 3곳의 주변 지역 혼잡 | FR-F02/F14 | 보조(서울만) |
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
| **A32** | POST | `/api/v1/auth/signup` | 없음 | 회원 가입(이메일·비밀번호·닉네임·출생연도·성별, 2-5절) → `users`·`profiles` 생성 | FR-A(회원) | 최종 |
| **A33** | POST | `/api/v1/auth/login` | 없음 | 로그인 → Access JWT + Refresh Token (2-4절) | — | 최종 |
| **A34** | POST | `/api/v1/auth/refresh` | Refresh Token | 토큰 갱신(교체 방식) | — | 최종 |
| **A35** | POST | `/api/v1/auth/logout` | user | 로그아웃(Refresh 폐기, `jti` 차단) | — | 최종 |
| **A36** | GET | `/api/v1/me/festival-preferences` | user | 내 축제 취향·온보딩 상태 조회. 취향 값 5개: `family_relaxed`(가족 + 한가로운) · `friends_activity`(친구 + 액티비티) · `couple_photo`(연인 + 포토존) · `pet`(반려견과 함께하는 축제) · `solo`(혼자 즐기기), 복수 선택 | 기획서 최신본 5.18 (신규 필수: 맞춤 추천) | 최종 |
| **A37** | PUT | `/api/v1/me/festival-preferences` | user | 취향 선택·변경·건너뛰기 저장 (7-2-2) | 〃 | 최종 |
| **A38** | GET | `/api/v1/festivals/recommended` | 선택(취향 계정 기준) | 맞춤 추천(필터·페이지·`recommendation_reason`, **규칙 기반**, 실제 축제 DB에 있는 것만) | 〃 | 최종 |
| **A39** | GET | `/api/v1/festivals/popular` | 없음 | 실제 참여 지표(상세 조회·관심 추가) 기반 인기 | 〃 | 최종 |
| **A43~A50** | — | `/api/v1/users/search`, `/api/v1/friend-requests`(+`/{id}/{action}`), `/api/v1/me/friend-requests`, `/api/v1/me/friends`(+`/{user_id}`), `/api/v1/me/blocks/{user_id}` | user | **친구 검색(닉네임 정확히 일치, 친구 코드 없음)·신청·수락·거절·취소·목록·삭제·차단·차단 해제** (7-2-3) | FR-COM12~14 | 최종 |
| **A51** | POST | `/api/v1/assistant/visit-course` (결과는 A06-1) | 없음(선택 로그인) | **AI 방문 코스**: 동행 유형·시간에 맞춘 축제 안 코스, 코드가 실존·운영 시각·동선 검증 (7-3) | FR-P01·P03 | 최종 |
| **A52~A54** | POST/PATCH/POST | `/api/v1/admin/notices`, `/{notice_id}`, `/{notice_id}/review`·`/{notice_id}/end` | operator·admin | 공식 공지 등록·수정·승인·반려·종료, 이력 추가만 (7-3) | FR-O06·D05 | 최종 |
| **A55~A56** | POST/PATCH | `/api/v1/admin/festivals`, `/{festival_id}` | admin | 축제 직접 등록·수정·게시, 변경 이력 (7-3) | FR-D12·O10 | 최종 |
| **A57~A65** | — | `/api/v1/festivals/{id}/companion-posts`, `/api/v1/companion-posts`(+`/{id}`, `/applications`, `/meeting-place`, `/{action}`), `/api/v1/companion-applications/{id}/{action}` | 공개·user | **동행**: 모집 목록·작성·신청·승인(정원 잠금)·만남 장소·종료/취소 (7-2-4) | FR-COM01~11·18·19 | 최종 |
| **A66~A73·WS** | — | `/api/v1/me/chat-rooms`, `/api/v1/chat-rooms`(+`/invitations`, `/{action}`, `/messages`, `/read`, A70 `PATCH /{room_id}`), `/api/v1/ws-tickets`, `WS /api/v1/ws/chat` | user. WS는 A73이 발급한 1회용 `ticket` | **채팅**: 방 목록·1:1·단체방·초대·수락·퇴장·방장 승계·메시지 이력·읽음, WebSocket 전송(DB 저장 뒤 ACK) (7-2-5) | FR-COM09·15~17·20 | 최종 |
| **A74~A77·A80** | — | `/api/v1/me/notifications`(+`/read`), `/api/v1/reports`, `/api/v1/admin/reports`, `DELETE /api/v1/me` | user / A77은 operator·admin | **알림·신고·탈퇴**(7-2-6). 마이페이지는 7-2-6절 | FR-COM21~24 | 최종 |
| **A78·A79** | GET·PATCH / GET | `/api/v1/me/profile`, `/api/v1/me/companion-activity` | user | **본인 프로필·내 동행 내역**(7-2-6) | FR-COM22 | 최종 |
| **A82** | POST | `/api/v1/me/password` | user | **비밀번호 변경**: 현재 비밀번호 확인 → 새 비밀번호 저장. 이 기기는 즉시 로그아웃(폐기 저장소 장애 때의 예외는 7-2-6), 모든 기기의 Refresh 폐기(다른 기기의 남은 Access는 만료까지) | FR-COM22 | 최종 |
| **A42** | GET | `/api/v1/festivals/trending` | 없음 | **지금 핫한 축제**. 네이버 데이터랩과 대한민국 구석구석 점수를 60:40으로 합산해 정렬(7-1) | FR-REC17 | 최종 |
| **A81** | GET | `/api/v1/festivals/{festival_id}/posts` | 없음 | **요즘 올라온 글**. 축제 상세에서 네이버 블로그·뉴스·카페의 최신 글 링크와 출처 표시(7-1) | FR-REC18 | 최종 |
| **A40** | GET | `/api/v1/festivals/discover` | 없음 | 고정 시드 기반 전체 축제 둘러보기 | 〃 | 최종 |
| **A41** | GET | `/api/v1/festivals/recent` | 없음 | 최초 공개일 기준 최신 등록 | 〃 | 최종 |
| A22 | POST | `/api/v1/admin/simulations/crowd` | operator (시험 환경만) | 혼잡 API 500·stale·본문 오류 모의 (v2.5 보존) | FR-H20 | 보조 |
| A23 | GET | `/api/v1/admin/ingestion-jobs` | admin | 축제 수집 작업 이력·오류 | FR-O09, D01 | 최종 |
| A24 | GET/POST | `/api/v1/admin/festivals/review-queue` | operator·admin | 축제 검토 대기열 조회·결정 | FR-D12/D14, O10 | 최종 |
| **A25** | POST | `/api/v1/routes/visit` (+ `GET /api/v1/routes/visit/{id}`) | 없음. 상태 조회 GET은 A05와 같은 경로 조회 토큰 | **축제 가는 길** (4-5절) | FR-R(기본 왕복) | 최종 |
| **A26** | GET | `/api/v1/festivals/{festival_id}/transit` | 없음 | 주변 지하철역·버스 정류장 **실시간 도착**. 지하철 실시간은 서울만, 버스는 서울 = 서울시 버스도착정보·서울 밖 = TAGO | — | 최종 |
| **A27** | — | — | — | 실시간 주차 빈자리 제외. 주차장 위치는 A08 `parking` | — | **채택 안 함** |
| **A28** | GET | `/api/v1/festivals/{festival_id}/traffic-incidents` | 없음 | 주변 **교통 돌발**(사고·공사·행사 통제). 경찰청(전국) + 서울 TOPIS | — | 최종 |
| **A29** | GET | `/api/v1/festivals/{festival_id}/visit-forecast` | 없음 | **방문 집중 예측**(향후 30일, 상대값 0~100) + 지역 관광 수요. '실시간 혼잡'과 다른 이름·색으로 표시 | — | 최종 |
| **A30** | GET | `/api/v1/data-sources` | 없음 | 데이터 공급원별 **지원 지역·실시간 여부·마지막 수집 시각** (화면의 '미지원' 안내·관리자 확인용) | 데이터 조사 | 최종 |

- **A36~A42 경로 규칙:** FastAPI에서 `/festivals/recommended`·`/popular`·`/discover`·`/recent`·`/trending` 같은 **고정 경로를 `/festivals/{festival_id}`보다 먼저 등록**하고, `festival_id`는 `^fst_` 형식을 검사합니다(라우터 작성 규칙·테스트 항목).
- **동행·채팅:** A57~A73으로 상세 작성(7-2-4·7-2-5, 채팅은 WebSocket), 권한은 권한 기준안(04 문서 7-1). **채팅 경로 규칙:** `/chat-rooms/{room_id}/invitations`·`/read`·`/messages`를 `/{action}`(A69)보다 **먼저 등록**하고, `action`은 `accept`·`decline`·`leave`만 받음(그 밖은 404 `NOT_FOUND`). **친구는 A43~A50으로 상세 작성(7-2-3).** 친구 검색은 **닉네임 정확히 일치**(닉네임은 겹치지 않음, 친구 코드 없음, 이메일·전화번호 검색 안 함, 009).


¹·² 물품보관함·약국: **보류**(서비스 범위의 지도 목록에 없음). 다만 BFCL `get_facilities`의 `category` 값(`locker`·`pharmacy`)에는 이미 들어 있어서, 평가 기준을 바꾸지 않도록 값은 남기고 호출되면 `status:"unsupported"`로 응답합니다.

### 3-0. 상태 확인: `GET /api/v1/health` (A01)

조회 파라미터와 본문 없이 호출합니다. `FESTIVAL_DATA=db`, `AUTH_PROVIDER=db`, `ROUTE_PROVIDER=real`과 `ROUTE_STORE=db`의 조합, `NOTICES_PROVIDER=real`, `TRANSIT_PROVIDER=real`, `VISIT_FORECAST_PROVIDER=real`과 `VISIT_FORECAST_STORE=db`의 조합 중 하나라도 적용되면 DB를 확인합니다. 앱 계정으로 연결해 `SELECT 1`을 실행하며 연결·쿼리의 전체 제한은 1초입니다. Redis는 공통 연결이 준비될 때까지 `not_configured`입니다.

**A01 상태 응답 (200·503)**

| 필드 | 타입 | 필수 | 모의(200) | DB 확인 성공(200) | DB 확인 실패(503) |
|---|---|---|---|---|---|
| `status` | string | 예 | `ok` | `ok` | `degraded` |
| `db` | string | 예 | `mock` | `ok` | `unavailable` |
| `redis` | string | 예 | `mock` | `not_configured` | `not_configured` |
| `version` | string | 예 | FastAPI 앱 버전 | FastAPI 앱 버전 | FastAPI 앱 버전 |
| `is_mock` | boolean | 예 | `true` | `false` | `false` |

모의 응답에는 `X-Mock: true`가 붙습니다. DB 설정 오류, 연결·쿼리 오류, 제한 시간 초과는 표의 503 상태 응답으로 알립니다.

### 3-1. 범위에서 뺀 것

| 항목 | 결정 | 이유 |
|---|---|---|
| 티켓·예약·결제 | ❌ API 없음 | 범위 밖(예매 보류) |
| 공연·전시 정보 | ❌ API 없음 | 축제만 다룸 |
| 실시간 주차 빈자리(A27) | **채택 안 함** | A08 시설에서 주차장 위치만 제공 |
| 웹 크롤링 | **A42 '지금 핫한 축제'의 점수 출처**인 대한민국 구석구석에만 사용 | 네이버 데이터랩 검색어 트렌드와 함께 점수에 반영합니다. 구석구석은 약관·`robots.txt` 허용 범위에서 축제명·순위만 수집하며 원문은 저장하지 않음(7-1 A42). 축제 기본 정보·경로·실시간 정보는 계속 공식 API·공공데이터만 |
| SNS 후기 현장 요약 | ⏸ 2차(나중에) | 메인 기능 아님 |
| 정류장 눌러 버스 혼잡 보기, 자전거 추가 기능(따릉이 실시간 등) | ⏸ 나중에 | 서비스 범위 밖 |
| 물품보관함·약국 지도 표시 | ⏸ 보류 | 지도 목록 밖 |

### 3-2. API 필드 ↔ DB 컬럼 대응 (1차 필수 API)

이름은 가능한 한 같게 썼고, 다른 것은 아래 표가 기준입니다. ID 형식은 2절과 같습니다.

| API 필드 | DB 컬럼 | 비고 |
|---|---|---|
| `request_id` | `route_requests.request_id` (UNIQUE) | 멱등 키 |
| `route_request_id` | `route_requests.route_request_id` (PK) | `rr_…` |
| `festival_id` | `route_requests.festival_id` → `festivals.festival_id` | `fst_…` |
| `origin`·`destination`(사용자가 고른 곳) | `route_requests.origin_type`·`destination_type` + `origin_place_hash`·`destination_place_hash`(HMAC, 009) + Redis `route:label:{id}`(24시간) | **원문 저장 안 함**(DB에 라벨 칸 없음) |
| `travel_mode` · `route_preference` · `user_constraints` | `route_requests.travel_mode` · `route_preference` · `constraints` | |
| `route_status` | `route_requests.status` | |
| `route_candidates[]` (근거 제외) | `route_results.candidates` (JSONB) | 후보·구간·점수 |
| 후보별 `area_evidence` · `mode_evidence` | 후보마다 `route_results.candidates[]` 안에 저장. `route_results.evidence`(JSONB)에는 경로 전체에 붙는 `{notices, control_version}`(통제 공지·통제 버전)을 저장 | 선택 시 조회한 버스 혼잡은 60초 메모리 캐시를 사용해 A05 응답에만 붙임 |
| `validity_check` (캐시·대체 경로) | `route_results.validity_check` | 5-8 |
| `stop_reason` · `rollback_reason` | `recovery_attempts.stop_reason` · `rollback_reason` | 5-8 |
| A02·A03 축제 필드(`name`·`venue_name`·`lat`·`lng`·`overview`·`fee_text`·`homepage_url`·`image_url`·`thumbnail_url`·`image_copyright.type`) | `festivals.title`·`venue_name`·`latitude`·`longitude`·`summary`·`admission_fee_text`·`official_url`·`image_url`·`thumbnail_url`·`image_copyright_type`(003) | **이름 다름** — API 이름이 기준, DB는 위 컬럼 |
| A02·A03 공개 조건 | `category='festival' AND source_class_level2='EV01' AND review_status='approved' AND published_at IS NOT NULL` | 018에서 오래된 미분류 게시 행을 검토 대기로 전환하며 `class_unverified` 이력을 남깁니다. |
| A06 `run_id`·`run_status`·`answer` / 사용한 도구 | `assistant_runs`(04 문서 마이그레이션 002, 6-9) / 사용한 도구·근거는 `assistant_runs.used_tools`·`evidence`(025). `agent_runs.tool_calls`는 에이전트 내부 실행 기록 | |
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

### 3-3. 공통 오류 코드 (모든 API 공통)

공통 오류 본문은 2절의 형식을 따릅니다. 연결 풀을 쓰는 API에서 SQLAlchemy 풀 대기 시간 초과(DB-14)가 발생하면 다음과 같이 응답합니다. `request_id`는 응답 헤더 `X-Request-ID`와 같습니다.

```http
HTTP/1.1 503 Service Unavailable
Retry-After: 1
Content-Type: application/json

{"error":{"code":"DB_POOL_TIMEOUT","message":"요청이 많아 잠시 후 다시 시도해 주세요.","request_id":"req_01JD8Q3K2M","retryable":true}}
```

| 코드 | HTTP | 의미 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 입력 형식 오류(Pydantic) 또는 A24 게시 조건 미충족 |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 | 인증 없음·만료 / 권한 부족·타인 자원 |
| `RATE_LIMITED` | 429 | 요청 수 제한 초과 |
| `DB_POOL_TIMEOUT` | 503 | DB 연결 풀 대기 시간 초과(DB-14). `retryable=true`, `Retry-After: 1`(초) |
| `AUTH_CHECK_UNAVAILABLE` | 503 | 쓰기·관리자 인증 상태, 로그인 한도, 갱신 잠금 또는 로그아웃 차단을 확인할 수 없음. `retryable=true` |
| `FESTIVAL_NOT_FOUND` | 404 | 없는 축제 ID |
| `FESTIVAL_LOCATION_UNKNOWN` | 400 | 출발 또는 도착이 축제 장소인데 축제 좌표가 없음 |
| `PASSWORD_MISMATCH` | 403 | 본인 확인용 비밀번호가 틀림(A80 탈퇴·A82 비밀번호 변경). 로그인 실패(A33 `INVALID_CREDENTIALS` 401)와 구분 |
| `NICKNAME_TAKEN` | 409 | 닉네임이 이미 있음(대소문자 무시, A32 — DB `uq_profiles_nickname`) |
| `IDEMPOTENCY_CONFLICT` | 409 | 같은 `request_id`에 다른 본문 |
| `ROUTE_INVALID` | 400 | 목적지 해석 실패·지원하지 않는 수단 |
| `ROUTE_PROVIDER_UNVERIFIED` | 503 | 경로 공급원 미연동·미검증(현재 상태) |
| `ROUTE_TIMEOUT` | 504 | 경로 조회 제한 시간 초과 |
| `ROUTE_UPSTREAM_ERROR` | 502 | 외부 길찾기 API 오류(429·5xx 포함, 원본 코드는 로그에) |
| `ROUTE_QUOTA_EXCEEDED` | 503 | 길찾기 공급원 일일 한도 소진(1차·2차 모두) — 경로 확인 불가 + 공식 안내 |
| `ROUTE_QUEUE_TIMEOUT` | 504 | 내부 대기열에서 제한 시간 초과 |
| `ROUTE_OVERLOADED` | 503 | 과부하 보호로 거절(`route_status=rejected`, 경로 제공 성공 아님) |
| `ROUTE_REQUEST_NOT_FOUND` | 404 | 없는 `route_request_id` (A05) |
| `ROUTE_CANDIDATE_NOT_FOUND` | 404 | 완료된 귀가 요청 결과에 전달된 `candidate_id`가 없음(A05) |
| `MEET_AT_INVALID` | 400 | 동행 만남 시각이 축제 기간 밖이거나 과거 (A58) |
| `OWN_POST` / `APPLICATION_EXISTS` / `POST_CLOSED` / `CAPACITY_FULL` / `APPLICATION_NOT_PENDING` | 403 / 409 / 409 / 409 / 409 | 동행 신청·승인 (A60·A62) |
| `REPORT_ALREADY_SUBMITTED` | 409 | A76에서 동일 신고자·대상 유형·대상 ID의 KST 날짜당 신고 한도 초과 |
| `NOT_FRIENDS` | 403 | 친구가 아닌 사람과 채팅방 (A67·A68) |
| `ROOM_READ_ONLY` / `STORE_FAILED` | WS `error` | 종료된 방에 전송 / DB 저장 실패(ACK 없음) |
| `COURSE_OUT_OF_PERIOD` | 400 | 방문 코스 시작 시각이 축제 기간 밖 (A51) |
| `DUPLICATE_FESTIVAL` | 409 | 같은 이름·기간·장소 축제가 이미 있음 → 검토 대기열로 (A55) |
| `NOT_IMPLEMENTED` | 501 | 아직 구현하지 않은 후속 기능 (A17) |
| `QUEUE_ITEM_NOT_FOUND` / `ALREADY_REVIEWED` | 404 / 409 | 없는 검토 항목 / 이미 처리한 검토 항목 (A24·A54) |
| `ALREADY_FRIENDS` / `REQUEST_PENDING` / `BLOCKED` / `REQUEST_NOT_PENDING` | 409 | 친구 API(A44·A46): 이미 친구 / 대기 중 신청 있음 / 차단 관계 / 이미 처리된 신청 |
| `ROUTE_NO_RESULT` | 200 (A04·A05의 `error`, `route_status=unavailable`) | 공급원이 "경로 없음"으로 답함(TMAP `result.status` 11~14, 카카오 `NO_RESULTS` 등 — [기록 10-3](API_구현_검증기록.md#10-3-길찾기-오류-응답--내부-처리-1120-한태경-evidence오류응답_정리md))이거나 TMAP 후보가 모두 운행 종료로 제외됨(6-7절). `retryable=false` |
| `INCIDENT_NOT_FOUND` / `INCIDENT_CLOSED` | 404 / 409 | 없는 사건 / 이미 닫힌 사건에 결정 기록 (A19) |
| `DUPLICATE_PLAN` | 409 | 같은 사건에 실행 중인 조치가 있음 (A19) |
| `SIMULATION_RUNNING` | 409 | 이미 실행 중인 부하 시험 (A20) |
| `SIMULATION_NOT_FOUND` | 404 | 없는 `simulation_id` (A16·A21·A31) |
| `RUN_NOT_FOUND` | 404 | 없는 챗봇 작업 `run_id` (A06-1·A06-2) |
| `ROUTE_RESULT_EXPIRED` | 200 (A05의 `error`) | **메모리 모드** 60초 캐시 만료, `retryable=true`, “경로가 만료됐어요. 다시 조회해 주세요.” **DB 모드** TMAP 결과 정리 또는 복원 후 `ready` 요청의 결과 행 없음, `retryable=false`, “경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요.” (4-4) |
| `NOTICE_NOT_FOUND` | 404 | 없는 공식 공지 ID |
| `NOTICE_NOT_APPROVED` / `ALREADY_ENDED` | 409 | 수동 종료를 요청한 공지가 승인 대기·반려 상태이거나 이미 종료됨 |
| `NOTICE_STORE_UNAVAILABLE` | 503 | 공지 저장소에 연결할 수 없음. 재시도 가능 |
| `ROUTE_CONTROL_CHANGED` | 200 (A04·A05·A25 상태의 `error`) | 생성 뒤 통제 버전이 바뀐 경로. 기존 요청 ID를 반환하고 새 요청 ID로 조회를 안내 |
| `ROUTE_ACCESS_EXPIRED` | 200 (A04·A25 POST의 `error`) | DB 모드에서 접수 10분 이후 동일 요청 재전송. 기존 `route_request_id`를 반환, `retryable=false`(4-3절) |
| `TOOL_TIMEOUT` | — (도구 출력) | 도구 호출 제한 시간 초과 (6-5) |
| `ROUTE_SECONDARY_SYNC_ONLY` | 200 (A05의 `error`) | 2차(카카오맵) 결과는 저장할 수 없어 비동기로 전달 불가 → 새로 요청 (6-7절) |
| `ROUTE_CONTROL_UNVERIFIED` | 200 (경고) | 경로는 있으나 공식 통제 반영 여부 확인 불가 — 오류가 아니라 `notices`에 표시 |
| `AI_AGENT_FAILED` | 200/503 | 에이전트 실패. 기본 귀가 조회·축제 기능은 계속 제공 |
| `REGION_UNSUPPORTED` | 200 | 그 지역에 해당 데이터가 없음(`status=unsupported`) |
| `SOURCE_HTTP_ERROR` / `SOURCE_RESULT_ERROR` / `SOURCE_STALE` | 502 / 502 / 200 | 외부 데이터: HTTP 오류 / 본문 결과 코드 오류 / 관측 시각이 오래됨 |
| `ACTION_NOT_ALLOWED` / `EVIDENCE_REQUIRED` / `POLICY_LIMIT_EXCEEDED` | 403 / 400 / 409 | 복구 결정이 정책을 통과하지 못함 |
| `SIMULATION_DISABLED` | 403 | 운영 환경에서 부하·장애 주입 시도 |

**화면 상태와의 대응:** `queued`→'대기 중', `processing`→'조회 중', `ready`→'검증된 경로', `unavailable`·`timed_out`→'확인 불가(재조회·공식 안내)', `rejected`→'요청 거절(잠시 후 재시도)', `unsupported`→'이 지역은 미지원', `unverified`→'준비 중인 정보', `stale`→'○분 전 정보'. (기획서 5.12)

---

## 4. 핵심 서비스 흐름 API

사용자가 실제로 거치는 순서대로 놓았습니다. 한 축제의 `festival_id`(`fst_…`) 하나로 처음부터 끝까지 이어집니다.

1. **축제 검색 A02**(4-1) — 지역·기간·키워드로 축제 목록을 받고, 고른 축제의 `festival_id`를 다음 호출에 씁니다.
2. **축제 상세 A03**(4-2) — 같은 `festival_id`로 장소·좌표·기간·소개를 확인합니다. 귀가 출발지 기본값은 이 축제 좌표입니다.
3. **귀가 요청 A04**(4-3) — 같은 `festival_id`와 목적지로 `POST /api/v1/routes/return`을 부릅니다. 결과는 두 가지입니다.
   - **200(동기 완료):** 동기 대기 3초 안에 끝나면 결과가 본문에 바로 담깁니다. `ready`이면 경로 후보가 함께 오고, 후보 선택용 조회 토큰은 본문이 아니라 **`X-Route-Access-Token` 응답 헤더**로 옵니다. 경로 후보와 이 헤더는 **TMAP `ready` 결과에만** 붙습니다. 카카오맵(2차) 결과와 `unavailable` 결과에는 조회 토큰 헤더가 없으므로 A05를 부르지 않습니다(`unavailable`이면 경로 후보도 없음).
   - **202(접수, 처리 중):** 3초 안에 끝나지 않으면 `queued` 상태로 `route_request_id`·`status_url`·**본문의 `route_access_token`**·`retry_after_s`(초기값 2초)를 돌려주고 처리는 계속됩니다. DB 저장 모드(`ROUTE_STORE=db`)에서 같은 `request_id`를 다시 보내면 `processing` 상태의 202가 올 수 있습니다.
4. **귀가 상태 조회 A05**(4-4) — `GET /api/v1/routes/return/{route_request_id}`에 **`X-Route-Access-Token` 요청 헤더**를 붙여 부릅니다. 넣는 값은 200 `ready`이면 응답 헤더의 토큰, 202이면 본문의 `route_access_token`입니다. 202였다면 `retry_after_s` 간격(초기값 2초)으로 다시 조회하고(호출하는 쪽 상한 최대 5회, 8-4 ③), `ready`가 되면 경로를 표시합니다. 경로를 고른 뒤에는 `candidate_id`를 붙여 그 후보의 버스 혼잡을 확인합니다. 토큰이 없으면 401, 다른 요청의 토큰은 403입니다. 토큰 수명(접수 후 10분)과 만료 시 401은 DB 저장 모드의 규칙입니다.
5. **가는 길 A25**(4-5) — 출발과 도착만 바꾼 같은 처리(`/api/v1/routes/visit`)이지만 응답에 차이가 있습니다. 202의 본문 `route_access_token`으로 상태를 조회하는 것은 같고, 동기 200에는 후보 선택용 `X-Route-Access-Token` 헤더가 없으며, 상태 조회 GET은 `candidate_id`를 받지 않습니다(버스 혼잡 선택 흐름 없음).


### 4-1. 축제 검색: `GET /api/v1/festivals` (A02) — 필드 명세

수집 DB의 공개 조건은 `category='festival' AND source_class_level2='EV01' AND review_status='approved' AND published_at IS NOT NULL`입니다(018). `items`와 `total` 모두 이 범위에서 계산합니다.

원본 좌표가 대한민국 범위 밖이거나 유효하지 않으면 좌표를 NULL로 두고, 공개 조건을 충족하는 축제는 목록·상세에 유지하되 지도 마커에서 제외합니다. 카카오 주소 검색 결과는 저장할 수 없으므로 좌표를 보정하지 않습니다(관리자가 A56으로 직접 입력할 수는 있음). 좌표가 필요한 A04는 400 `FESTIVAL_LOCATION_UNKNOWN`, A10 실제 모드는 200 `unsupported`를 반환합니다.

| 필드 | 위치 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|---|
| `region` | query | string | 아니요 | `ALL` | 2-1절 지역 코드 | 시·도 |
| `date_from` / `date_to` | query | string(date) | 아니요 | null | `YYYY-MM-DD`, `date_from ≤ date_to`, 최대 366일 | 기간(겹치는 축제) |
| `q` | query | string | 아니요 | null | 1~50자 | 이름·장소 키워드 |
| `status` | query | string | 아니요 | null | `upcoming`·`ongoing`·`ended`·`cancelled` 중 하나 이상, **쉼표로 여러 값**(예: `ongoing,upcoming`). 모르는 값이 하나라도 있으면 422 | 진행 상태 |
| `bbox` | query | string | 아니요 | null | `minLng,minLat,maxLng,maxLat` | 지도 화면 범위 |
| `sort` | query | string | 아니요 | `start_date` | `start_date`·`-start_date`·`name`·`distance`(`bbox` 있을 때만). `-`는 내림차순 | 정렬 |
| `page` / `page_size` | query | int | 아니요 | 1 / 20 | page ≥ 1, page_size 1~100 | 페이지 |

응답(200): `{ "items": [ { "festival_id", "name", "region_code", "venue_name", "lat", "lng", "start_date", "end_date", "event_status", "thumbnail_url", "image_credit", "source", "last_synced_at" } ], "total": 37, "page": 1, "page_size": 20 }` — `thumbnail_url`은 TourAPI `firstimage2`(작은 크기), 없으면 null(화면 기본 이미지), `image_credit`은 출처 문구(아래 4-2 이미지 규칙) — 요청마다 외부 API를 부르지 않고 수집된 DB에서 답합니다. 오류: 422 `VALIDATION_ERROR`.

**A02 목록 응답 (200, FestivalPage·FestivalListItem)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `items` | 응답 | array<object> | 예 | 공개 축제 중 이 페이지의 목록 |
| `items[].festival_id` | 응답 | string | 예 | 축제 ID |
| `items[].name` | 응답 | string | 예 | 축제명 |
| `items[].region_code` | 응답 | string | 예 | 시·도 코드(2-1절, `ALL` 제외) |
| `items[].venue_name` | 응답 | string 또는 null | 예 | 축제 장소 |
| `items[].lat` | 응답 | number 또는 null | 예 | 위도 |
| `items[].lng` | 응답 | number 또는 null | 예 | 경도 |
| `items[].start_date` | 응답 | string(date) 또는 null | 예 | 시작일 |
| `items[].end_date` | 응답 | string(date) 또는 null | 예 | 종료일 |
| `items[].event_status` | 응답 | string | 예 | `upcoming`·`ongoing`·`ended`·`cancelled`·`needs_review` |
| `items[].thumbnail_url` | 응답 | string 또는 null | 예 | TourAPI `firstimage2`, null이면 화면 기본 이미지 |
| `items[].image_credit` | 응답 | string 또는 null | 예 | 이미지 출처 표시 문구(4-2절) |
| `items[].source` | 응답 | string | 예 | `tourapi` 또는 직접 등록 `admin` |
| `items[].last_synced_at` | 응답 | string | 예 | 마지막 수집 시각(ISO 8601). 수집 기록이 없으면 빈 문자열 `""` |
| `total` | 응답 | int | 예 | 페이지 자르기 전 필터와 공개 조건을 만족하는 전체 건수 |
| `page` | 응답 | int | 예 | 조회한 페이지 번호 |
| `page_size` | 응답 | int | 예 | 요청에 적용한 페이지 크기 |
| `is_mock` | 응답 | boolean | 예 | 모의 목록이면 `true`, 수집 DB 목록이면 `false` |

**A02·A03 서울시 보강 동작 규칙** — OA-15486에서 확정 일치한 TourAPI 축제의 빈 공식 홈페이지·요금을 보강합니다. `source`는 `tourapi`, A03 `source_ref`는 TourAPI contentid입니다. 불확실한 건은 A24 검토 대기로 두며 서울시 이미지 URL은 검토 근거로 보관합니다.

### 4-2. 축제 상세: `GET /api/v1/festivals/{festival_id}` (A03) — 필드 명세

A02와 같은 공개 조건을 적용합니다. 공개 범위에 없는 ID는 404 `FESTIVAL_NOT_FOUND`로 응답합니다.

**A03 요청 경로**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `festival_id` | path | string | 예 | `^fst_[0-9A-Za-z]{6,26}$`, 공개 축제 ID. 쿼리·본문 없음 |

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `festival_id` | string | 불가 | `fst_…` |
| `name` · `region_code` | string | 불가 | 이름·지역 |
| `venue_name` · `address` | string | null 가능 | 장소·주소(원본에 없을 수 있음, 실호출 전) |
| `lat` / `lng` | number | null 가능 | 원본 또는 관리자가 직접 입력·승인한 보정 좌표. 두 값이 null이면 지도 마커를 표시하지 않습니다. 좌표가 필요한 API의 응답: A04·A25는 출발 또는 도착에 축제 위치를 쓸 때 400 `FESTIVAL_LOCATION_UNKNOWN`, A09·A26·A28은 200 `unavailable`·`FESTIVAL_LOCATION_UNKNOWN`, A10은 실제 모드의 서울 축제면 200 `unsupported`·`missing_coordinates`(서울 밖은 `outside_seoul`, 모의 모드는 `unavailable`). A07(공지)은 좌표를 쓰지 않고, A29는 승인된 관광지 연결이 없으면 `unsupported`입니다(7-1-0). |
| `start_date` / `end_date` | string | null 가능(미확정 일정) | 기간 |
| `event_status` | string | 불가 | `upcoming`·`ongoing`·`ended`·`cancelled`·`needs_review` |
| `overview` · `fee_text` · `homepage_url` · `image_url` | string | null 가능 | 소개·입장료·홈페이지·대표 이미지(공급원에 있을 때만). 입장료 = `usetimefestival`, 소개 = `detailCommon2`의 `overview`, **대표 이미지 = `firstimage`**(모두 실호출 확인, [기록 10](API_구현_검증기록.md#10-실제-호출-근거-현재-확보분)절) |
| `thumbnail_url` | string | null 가능 | 목록·지도 카드용 작은 이미지 = `firstimage2` |
| `image_copyright` | object | 이미지 없으면 null | `{type: "Type1"·"Type3", credit: "한국관광공사", modify_allowed: bool}` — `cpyrhtDivCd`에서 계산(아래 규칙) |
| `source` / `source_ref` / `last_synced_at` | string | 불가 | 출처·원본 ID·마지막 수집 시각. 직접 등록은 `admin`·축제 ID·등록 시각. 수집 기록이 없으면 `last_synced_at`은 빈 문자열 `""` |

오류: 404 `FESTIVAL_NOT_FOUND`, 422 `VALIDATION_ERROR`(ID 형식).

**축제 대표 이미지 규칙 (2026-11-20 TourAPI 원본 대조)**

| 항목 | 내용 |
|---|---|
| 공급원 | TourAPI `searchFestival2`(목록)·`detailCommon2`(상세)의 `firstimage`(원본)·`firstimage2`(작은 크기)·`cpyrhtDivCd`(저작권 유형). 주소는 `https://tong.visitkorea.or.kr/cms/resource/…` |
| 저장 | 이미지 **파일은 복사하지 않고 주소만** `festivals.image_url`·`thumbnail_url`에 저장(DB 마이그레이션 003). 화면은 한국관광공사 서버에서 바로 불러옴 |
| 출처 표시 | 이미지가 보이는 모든 화면(목록 카드·상세·지도 팝업)에 `image_credit`("한국관광공사") 표시 |
| 변경 금지(Type3) | `Type3`(출처 표시 + 변경 금지)은 **자르기·필터·글자 얹기를 하지 않음**. 카드 비율이 달라도 잘리지 않게 전체를 보이게(`object-fit: contain`) 표시. **목록 카드는 `firstimage2`(작은 크기), 상세는 `firstimage`를 주소 그대로 쓰고 크기는 CSS로만 조절**(파일을 줄이거나 다시 저장하지 않음). `Type1`만 잘라 쓰기 허용(`modify_allowed: true`). 화면 표기는 **"출처: 한국관광공사"**. 관광공사 문의는 하지 않기로 하고 이 처리안으로 확정 |
| 없을 때 | `image_url`·`thumbnail_url`이 비면 null로 주고 화면이 **기본 이미지**를 보여 줌(다른 축제·다른 출처 이미지로 채우지 않음) |
| 추가 사진 | 사진 여러 장(`detailImage2`)은 1차에서 쓰지 않음 |

### 4-3. 귀가 요청 — 대표 API 상세 명세: `POST /api/v1/routes/return` (A04, AI 안심 귀가 조회)

수업 가이드의 **상세 명세 8칸**(호출 목적·요청 헤더·경로/쿼리·요청 본문·검증/권한·정상 응답·오류 응답·실행 규칙)으로 씁니다.

| # | 칸 | 명세 |
|---|---|---|
| 1 | **호출 목적** | 축제가 끝난 뒤 축제장(또는 사용자가 바꾼 출발 위치)에서 목적지까지 돌아가는 경로를 요청 (FR-R13 · 1차 시연 필수). 호출 주체: 귀가 화면(직접), Route Agent(도구 `request_return_route` 경유) |
| 2 | **요청 헤더** | `Content-Type: application/json`(필수) · `X-Request-ID: req_…`(선택, 없으면 서버 생성) · `Authorization`(선택, 로그인 사용자면) |
| 3 | **경로·쿼리** | 없음 |
| 4 | **요청 본문** | 아래 '요청 필드 명세'와 예시 |
| 5 | **검증·권한** | 형식은 8-1절 `ReturnRouteRequest`(422). 같은 `request_id`·본문이면 기존 요청으로 응답하고 본문이 다르면 409. 새 요청은 축제 존재(404) → 출발이 축제 장소면 축제 좌표 있음(400 `FESTIVAL_LOCATION_UNKNOWN`) → 목적지 해석(400 `ROUTE_INVALID`)을 검사. 인증 없음(anonymous 허용), 요청 수 제한(429) |
| 6 | **정상 응답** | `200` 제한 시간 안에 끝남(`ready` 또는 `unavailable`. TMAP `ready`일 때만 경로 후보와 `X-Route-Access-Token` 응답 헤더 제공) / `202` 아직 처리 중(`queued`·`processing`, 상태 조회 URL·본문의 `route_access_token`·`retry_after_s` 제공, 토큰 수명 10분은 DB 저장 모드) |
| 7 | **오류 응답** | 아래 '오류 응답 표' |
| 8 | **실행 규칙** | **동기 대기 3초**(넘으면 그때까지의 상태로 202 반환, 처리는 계속) · **전체 처리 제한 10초**(넘으면 `route_status=timed_out` — 202 뒤에는 A05로 확인, 3초 안에 판정되면 504) (모두 초기값) · 길찾기 어댑터 1회 호출 상한 TMAP 5초·카카오 3초(8-4절) · 1차 공급원 실패 때 **2차 공급원으로 1회** — **어떤 응답을 실패로 보고 넘길지는 [기록 10-3](API_구현_검증기록.md#10-3-길찾기-오류-응답--내부-처리-1120-한태경-evidence오류응답_정리md) 표가 유일한 기준**(시간 초과·429·5xx·403 키 오류·TMAP `result.status` 12~14 등). 단 카카오(2차)는 **동기 3초 안에 끝날 때만** 결과를 줄 수 있으므로, 1차가 3초 안에 실패하지 않으면(예: 5초 시간 초과) 202 뒤 `ROUTE_SECONDARY_SYNC_ONLY`로 끝냄(6-7절) · 우리 요청 잘못(400/404/409/422)은 재시도 없음 · 같은 `request_id`는 처음 만든 `route_request_id`를 돌려줌(멱등) · 8-3절 |

**동작 규칙** — A04/A25의 v2 키는 축제와 공통 공지의 통제 버전을 사용합니다. 버전이 달라진 기존 경로는 같은 요청 ID로 `unavailable`·`ROUTE_CONTROL_CHANGED`를 반환합니다. 활성 통제 공지 제목과 A07 경로를 `notices[]`에 표시하고 `control_unverified` 상태를 유지합니다.

**처리 순서:** ① 축제 존재·좌표 확인 → ② 목적지 확인(좌표 또는 카카오 장소 검색) → ③ 경로 키(`route_key`) 계산 → ④ 켜져 있는 복구 조치(동일 요청 병합 등) 적용 → ⑤ **길찾기 어댑터 호출: 1차 TMAP 대중교통 → 실패 시 2차 카카오맵 대중교통**(개발·시험은 모의) → ⑥ 결과 검증(출처·수단·시각·확인 가능한 통제) → ⑦ 경로 근거 붙이기 → ⑧ 추천 기준으로 점수 매겨 정렬 → ⑨ 기록(`route_requests`·`route_results`·지표)

**경로 근거(evidence) — 두 가지로 나눕니다 **

| 근거 | 무엇을 고르는 데 쓰나 | 데이터 | 지역 |
|---|---|---|---|
| `area_evidence` 지역 선택 근거 | **어느 역·지역으로 갈지** (예: 삼각지역이 붐비니 이태원역) | 서울 실시간 인구 혼잡 구역(OA-21778), 교통 돌발(경찰청 전국·TOPIS 서울) | 혼잡 = 서울만, 돌발 = 전국 |
| `mode_evidence` 교통수단 선택 근거 | **무엇을 탈지** (만석 버스 대신 지하철) | 서울 버스도착정보 15000314의 차내 혼잡. 선택한 귀가 경로의 버스 승차 정류장에 표시 | 서울만. 서울 밖과 카카오맵은 `unsupported`. 확인이 안 된 선택 결과는 `unknown`. 혼잡을 확인할 수 없어도 경로는 제공 |

- TMAP `stationID`(6자리)와 서울 `arsId`(5자리)는 공급원별 식별자입니다. **정규화한 승차 정류장 이름, 30m 이내 거리(8-4 ⑧), 노선 번호, 바로 다음 정류장으로 확인한 진행 방향**이 모두 맞는 후보가 정확히 하나일 때 연결합니다. 일치 후보가 없거나 둘 이상이면 `unknown`입니다.
- 버스 차내 혼잡은 **지역이 붐빈다는 근거로 쓰지 않습니다**(버스 승객은 지나가는 사람). 처음부터 다 보여 주지 않고, 사용자가 경로를 고른 뒤 그 경로의 버스에만 보여 줍니다.

**동작 규칙** — A04의 동기 `ready` 응답은 `X-Route-Access-Token` 헤더로 후보 선택용 토큰을 전달합니다(카카오맵 제외). 202 응답은 기존 `route_access_token` 본문 필드를 사용합니다. 선택 후 화면은 A05에 `candidate_id`와 조회 토큰을 보내며, 해당 후보의 `mode_evidence.bus_crowding`을 읽습니다.

**추천 기준과 점수 (기획서 FR-R01~R05 '고급 5유형'과 같은 이름, 비율 미정, Should)**

| `route_preference` 값 | 뜻 | 점수에 크게 반영하는 것 |
|---|---|---|
| `fastest` (기본) | **최단시간 경로** (FR-R01) | 소요 시간 |
| `less_crowded` | **혼잡 회피 경로** (FR-R02) | 혼잡(지역·차내) — 구간 단위 근거가 있을 때만, 지역 혼잡을 길 혼잡으로 단정하지 않음 |
| `accessible` | **교통약자 배려** (FR-R03) | 계단·승강기·통제 데이터가 확인된 범위만 — **없으면 `not_verifiable`** |
| `min_walk` | **최소 도보 경로** (FR-R04) — 노약자·보행 약자를 위해 **엘리베이터·에스컬레이터 등 보행 부담이 적은 동선과 도보 구간**을 안내. '최단 거리'가 아님 | 도보 거리·계단 회피(시설 데이터 확인 범위) |
| `fewest_transfers` | **최소 환승 경로** (FR-R05) | 환승 횟수 |

경로 유형 이름은 기획서와 같게 `less_crowded`·`min_walk`를 씁니다. '최단 거리'는 따로 두지 않습니다.

점수 = 시간·거리·비용·혼잡에 기준별 비율을 곱한 합(낮을수록 좋음). **비율은 실제 응답을 넣어 보고 정합니다**(지금은 미정). 점수와 쓴 비율 버전을 응답(`score`, `score_version`)에 남깁니다.

**요청 필드 명세**

| 필드 | 위치 | 타입 | 필수 | 빈값 | 제약 | 설명 |
|---|---|---|---|---|---|---|
| `request_id` | body | string | 예 | 불가 | 8~64자, UUID 권장 | 멱등 키 |
| `festival_id` | body | string | 예 | 불가 | `^fst_[0-9A-Za-z]{6,26}$` | 출발 축제 |
| `origin` | body | object | 아니요 | `{"type":"festival"}` | `{type:"festival"}`(축제 장소) 또는 `{type:"place", query 또는 lat+lng}` — **출발 위치를 사용자가 바꿀 수 있음**(S06, 09 마이그레이션 `origin_type`) | 출발지 |
| `destination` | body | object | 예 | 불가 | `query` 또는 `lat`+`lng` 중 **하나만** (`{type:"festival"}`은 출발이 사용자 장소일 때만) | 목적지 |
| `destination.query` | body | string | 조건 | 불가 | 1~100자 | 장소명·주소 |
| `destination.lat` / `lng` | body | number | 조건 | 불가 | 위도 33~39, 경도 124~132 | 좌표 |
| `travel_mode` | body | string | 아니요 | — | `transit`·`walk`·`car`·`taxi`, 기본 `transit` | 이동 수단(공급원 지원 범위 확인 후 축소 가능) |
| `route_preference` | body | string | 아니요 | — | 위 5개 값, 기본 `fastest` | 추천 기준 |
| `user_constraints` | body | object | 아니요 | `{}` | `with_child`·`wheelchair`: bool, `max_walk_m`: 0~5000 또는 null | 이동 조건 |
| `departure` | body | string | 아니요 | — | `now`만(예약 출발은 후속) | 출발 시각 |

**정상 응답 필드 명세 (200)** — 202는 아래 '처리 중 응답' 필드만 돌려줍니다

동기 200의 `ready` 응답에 경로 후보가 담겨 있으므로 화면에 바로 표시합니다. `status_url`과 `route_access_token` 본문 필드는 202에 포함합니다. 동기 완료 뒤 버스 혼잡을 조회할 때는 응답 헤더의 토큰과 `route_request_id`로 A05를 호출합니다.

아래 경로 상세 필드는 `ready` 기준입니다. DB 모드에서 조회 토큰 만료 후 같은 `request_id`와 본문을 보내면 기존 `route_request_id`, `route_status=unavailable`, `completed_valid_route=false`, `error`(`code`, `message`, `retryable`), `updated_at`, `is_mock`, `notices`를 반환합니다.

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `route_request_id` | string | 불가 | `rr_` + ULID |
| `route_status` | string | 불가 | `queued`·`processing`·`ready`·`unavailable`·`rejected`·`timed_out` (`ready`만 경로 제공 성공) |
| `direction` | string | 불가 | `return` |
| `origin` / `destination` | object | 불가 | 출발(축제 DB 좌표)·도착(표시 이름, 해석 방법) |
| `route_preference` | string | 불가 | 요청한 추천 기준 |
| `route_candidates[]` | array | 빈 배열 가능 | `ready`일 때만 채움. 각 후보: `candidate_id`, `summary`, `duration_min`, `distance_m`, `walk_m`, `transfers`, `fare_krw`, `legs[]`(구간마다 `mode`·`path`=**`[[위도, 경도], …]`**·`stops[]`), `service_running`(boolean 또는 null, 6-7절), `score`, `area_evidence`, `mode_evidence` — **공급원이 주지 않는 값은 `null`, 만들지 않음** |
| `provider` | string | 불가 | 실제로 답한 공급원 `tmap`·`kakao`·`mock_adapter` |
| `provider_tier` | string | 불가 | `primary`·`secondary`·`mock` |
| `queried_at` | string | 불가 | 공급원 조회 시각 |
| `verification_status` | string | 불가 | `verified_basic`·`constraint_unverified`·`control_unverified`·`failed` |
| `constraint_status` | object | `{}` | 조건별 `verified`·`not_verifiable`·`unverified`(통제 등 공급원 미확인) |
| `coverage` | object | 불가 | 2절 공통 형식 |
| `score_version` | string | null | 점수 비율 버전 |
| `is_mock` | boolean | 불가 | 모의 응답이면 true |
| `notices[]` | array | 빈 배열 | 활성 공식 교통통제 제목·A07 경로와 통제 반영 여부 안내 |
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
        "bus_crowding": { "status": "unverified", "reason": "버스 혼잡을 확인하지 않았어요." }
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
| 200 | `ROUTE_ACCESS_EXPIRED` (`error.code`) | DB 모드에서 접수 10분 이후 같은 `request_id`·본문 재전송. 기존 `route_request_id`와 `route_status=unavailable`을 반환하며 조회 토큰·후보·폴링 URL은 생략 | 아니요(새 `request_id`로 새로 접수) |
| 400 | `ROUTE_INVALID` | 목적지를 찾을 수 없음, 공급원이 지원하지 않는 수단 | 아니요(입력 수정) |
| 404 | `FESTIVAL_NOT_FOUND` | 없는 `festival_id` | 아니요 |
| 409 | `IDEMPOTENCY_CONFLICT` | 같은 `request_id`에 다른 본문 | 아니요 |
| 422 | `VALIDATION_ERROR` | 형식 오류(필드 명세 위반) | 아니요 |
| 400 | `FESTIVAL_LOCATION_UNKNOWN` | 출발(또는 가는 길 도착)이 축제 장소인데 축제 좌표가 없음(서버 판단) — 사용자가 직접 고른 장소면 해당 없음 | 아니요 |
| 429 | `RATE_LIMITED` | 요청 수 제한 초과 | `Retry-After` 뒤 |
| 502 | `ROUTE_UPSTREAM_ERROR` | 1차·2차 공급원 모두 오류 | 예(1회) |
| 503 | `ROUTE_QUOTA_EXCEEDED` | 공급원 일일 한도 소진 → '확인 불가 + 공식 안내' | 아니요(당일) |
| 503 | `DB_POOL_TIMEOUT` | DB 연결 풀 대기 시간 초과(DB-14) | `Retry-After: 1` 뒤 |
| 503 | `ROUTE_OVERLOADED` | 과부하 보호로 거절(`route_status=rejected`, **경로 제공 성공 아님**) | 예(잠시 뒤) |
| 503 | `ROUTE_PROVIDER_UNVERIFIED` | 공급원 미연동·미검증(지금 상태) | 아니요 |
| 504 | `ROUTE_TIMEOUT` | 제한 시간 초과(`route_status=timed_out`) | 예(같은 `request_id`로 1회) |

**규칙**
- DB 모드에서 같은 `request_id`·본문을 재전송해도 최초 접수 시각과 `route_request_id`를 유지합니다. 조회 권한이 만료되면 `ROUTE_ACCESS_EXPIRED`로 새 접수를 안내합니다. 경로를 다시 조회하려면 새 `request_id`를 보냅니다. A05는 만료된 토큰에 401을 반환합니다.
- `user_constraints`(아이 동반·휠체어 등)를 검증할 데이터가 없으면 `constraint_status`에 `not_verifiable`로 표시하고, "확실히 이용 가능"이라고 답하지 않습니다 (FR-R10, BFCL NLD-13·21).
- 혼잡 자료가 지역 단위뿐이면 "가장 덜 붐비는 경로"라고 판정하지 않습니다. `area_evidence`로 구역 혼잡만 보여 줍니다 (BFCL NLD-22).
- 목적지 원문은 DB에 저장하지 않습니다. DB에는 **서버 비밀키를 섞은 HMAC 해시**만(30일), 화면 표시 이름은 **Redis에 24시간**만 둡니다(04 문서 7-0 보존표·마이그레이션 004).
- 어떤 공급원이 답했는지(`provider`·`provider_tier`)를 항상 남깁니다. 2차 공급원으로 답했다고 해서 자동 복구로 세지 않습니다(복구 판정은 5-8절).

### 4-4. 귀가 상태 조회: `GET /api/v1/routes/return/{route_request_id}` (A05)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 202로 접수된 귀가 요청의 처리 상태·결과 확인(FR-R14), 사용자가 선택한 귀가 후보의 버스 혼잡 확인. 화면 폴링, Route Agent(`get_route_request_status`) |
| 2 | 요청 헤더 | `X-Request-ID`(선택) · `X-Route-Access-Token: rrt_…`(필수, 요청 때 받은 조회 토큰, DB 모드에서 접수 후 10분 유효) |
| 3 | 경로·쿼리 | `route_request_id`: string, 필수, `^rr_[0-9A-Za-z]{6,26}$` · `candidate_id`: 선택 쿼리, string, 최대 16자, `^c[1-9][0-9]*$`. 화면에서 경로를 선택한 뒤 전달합니다. |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 형식 오류 422 · 토큰 없음·만료 401 · 다른 요청의 토큰 403 · 없는 ID 404. `ROUTE_STORE=db`는 접수 후 10분에 만료한다. 기본 메모리 모드는 토큰 누락을 검사한다([기록 17-3](API_구현_검증기록.md#17-3-저장캐시-규칙--실제-코드-강사-1120-api-2)) |
| 6 | 정상 응답 | **200** — 요청 처리가 실패했어도 '조회'는 성공이므로 200. 실패는 `route_status`·`error`로 알림(수업 가이드 S29). 경로는 `ready`일 때만 `route_candidates`에 담음 |
| 7 | 오류 응답 | 401 `UNAUTHORIZED` / 403 `FORBIDDEN` / 404 `ROUTE_REQUEST_NOT_FOUND`·`ROUTE_CANDIDATE_NOT_FOUND`(`ready` 응답 내 후보 없음) / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회는 멱등이며 DB 모드는 조회 중 만료된 TMAP 본문을 정리할 수 있음. 폴링 간격 2초·최대 5회(초기값), 그 뒤엔 '확인 불가' 안내 |

**상태별 응답 예시 (모두 200)**

```json
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "queued", "completed_valid_route": false, "retry_after_s": 2 }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "processing", "completed_valid_route": false, "retry_after_s": 2 }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "ready", "completed_valid_route": true, "route_candidates": [ "…4-3절과 같은 모양…" ], "provider": "tmap", "queried_at": "…" }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false, "error": { "code": "ROUTE_UPSTREAM_ERROR", "message": "길찾기 공급원 오류예요.", "retryable": true }, "notices": ["지금은 경로를 확인할 수 없어요. 공식 안내를 확인해 주세요."] }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false, "error": { "code": "ROUTE_RESULT_EXPIRED", "message": "경로가 만료됐어요. 다시 조회해 주세요.", "retryable": true } }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false, "error": { "code": "ROUTE_RESULT_EXPIRED", "message": "경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요.", "retryable": false } }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "timed_out", "completed_valid_route": false, "error": { "code": "ROUTE_TIMEOUT", "message": "경로 조회 시간이 초과됐어요.", "retryable": true } }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "rejected", "completed_valid_route": false, "error": { "code": "ROUTE_OVERLOADED", "message": "요청이 많아 잠시 뒤 다시 시도해 주세요.", "retryable": true } }
```

- `completed_valid_route`는 **검증된 경로가 실제로 담겼을 때만 true**입니다. 대기열 접수(`queued`)는 성공이 아닙니다 (BFCL NLD-15·17).

**응답 필드 명세 (A05, 200)** — `route_status`에 따라 채워지는 필드가 다릅니다

| 필드 | 타입 | 빈값 | 언제 채우나 | 설명 | DB |
|---|---|---|---|---|---|
| `route_request_id` | string | 불가 | 항상 | `rr_` + ULID | `route_requests.route_request_id` |
| `route_status` | string | 불가 | 항상 | `queued`·`processing`·`ready`·`unavailable`·`rejected`·`timed_out` (DB 내부값 `created`는 응답에 안 나옴) | `route_requests.status` |
| `completed_valid_route` | boolean | 불가 | 항상 | 검증된 경로가 `route_candidates`에 실제로 담겼을 때만 true | 계산값(`route_results` 있음 + 검증 통과) |
| `retry_after_s` | int | — | `queued`·`processing` | 다음 조회까지 기다릴 초(초기값 2초) | 없음(설정값) |
| `direction`·`festival_id`·`travel_mode`·`route_preference` | string | 불가 | `ready` | 요청 값 그대로 | `route_requests` |
| `route_candidates[]` | array | 빈 배열 가능 | `ready` | 4-3절 정상 응답 필드와 같은 모양 | `route_results.candidates` (카카오는 저장 안 함 → 6-7절 규칙) |
| `provider`·`provider_tier`·`queried_at` | string | 불가 | `ready` | 실제로 답한 공급원·순위·조회 시각 | `route_results` |
| `verification_status`·`constraint_status` | string·object | 불가 | `ready` | 4-3절과 같음 | `route_results.validation_status` · `route_results.evidence` |
| `error` | object | — | `unavailable`·`rejected`·`timed_out` | `{code, message, retryable}` — `ROUTE_UPSTREAM_ERROR`·`ROUTE_QUOTA_EXCEEDED`·`ROUTE_OVERLOADED`·`ROUTE_TIMEOUT`·`ROUTE_SECONDARY_SYNC_ONLY`·`ROUTE_PROVIDER_UNVERIFIED`·`ROUTE_RESULT_EXPIRED`·`ROUTE_NO_RESULT` | `route_requests.error_code` |
| `notices[]` | array | 빈 배열 | 항상 가능 | 확인 못 한 것·대체 안내 | 계산값 |
| `is_mock` | boolean | 불가 | 항상 | 모의 응답이면 true | `route_results.is_mock` |
| `updated_at` | string | 불가 | 항상 | 상태가 마지막으로 바뀐 시각 | 계산값 `completed_at` → `started_at` → `submitted_at` 중 처음 값 |

**동작 규칙** — `candidate_id`가 있고 상태가 `ready`일 때 선택한 후보의 차내 혼잡을 응답에 붙입니다. 기존 경로 토큰 검사를 통과한 요청에 적용합니다. `BUS_CROWD_PROVIDER=mock`이 기본이며 `real`은 `DATA_GO_KR_SERVICE_KEY`로 조회합니다. 외부 조회는 버스 구간당 전체 3초 이내에 끝내며, 결과를 서버 메모리에서 60초 재사용합니다.

| 선택한 후보의 필드 | 타입 | 설명 |
|---|---|---|
| `mode_evidence.bus_crowding.status` | string | `available`은 유효한 관측이 있는 경우. 검증 정보 부족·중복·공급원 실패는 `unknown`, 카카오맵·버스 구간 없음·서울 범위 밖은 `unsupported` |
| `mode_evidence.bus_crowding.source`·`is_mock` | string·boolean | 공급원 구분 `mock` 또는 `seoul_bus_15000314`와 모의 여부. 구간 정보가 있는 응답에 포함 |
| `mode_evidence.bus_crowding.legs[]` | array | 버스 구간별 0부터 시작하는 `leg_index`, `status`, 유효한 혼잡 값이 있으면 `arrivals[]`. 도착 순서 `arrival_order`는 1 또는 2이며 `crowding`은 `여유`·`보통`·`혼잡` |

- 화면과 Route Agent는 `completed_valid_route=true`일 때만 경로를 안내합니다.
- **`ROUTE_RESULT_EXPIRED` — 현재 동작(코드 기준):** TMAP 경로 결과는 서버 메모리에 **60초**만 둡니다. 60초가 지나 A05로 조회하면 `route_status=unavailable`, `error.code=ROUTE_RESULT_EXPIRED`, **`retryable=true`**("경로가 만료됐어요. 다시 조회해 주세요.")입니다(`real_routes.py`, 시험 `test_P11_expiry_removes_shared_tmap_body_for_all_ids`).
- **DB 모드(011·012)** — 유효 토큰으로 조회하면 24시간이 지난 TMAP 후보와 근거를 정리하고 `purged_at`을 기록합니다. 정리된 결과와 012 백업 복원 후 `route_requests.status=ready`이지만 `route_results` 행이 없는 요청은 모두 `route_status=unavailable`, `completed_valid_route=false`, `ROUTE_RESULT_EXPIRED`(`retryable=false`)로 답합니다. 메시지는 “경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요.”입니다. 정상 흐름에서는 조회 토큰이 먼저 만료됩니다. 새 경로는 새 `request_id`로 요청합니다.

### 4-5. 축제 가는 길: `POST /api/v1/routes/visit` (A25)

귀가 API와 **같은 처리·검증·기록**을 쓰고 출발과 도착만 바꿉니다. `route_requests.direction='visit'`으로 기록합니다.

| 항목 | 귀가 (`/api/v1/routes/return`) | 가는 길 (`/api/v1/routes/visit`) |
|---|---|---|
| 출발 | **기본 축제장**(축제 DB 좌표), 사용자가 바꿀 수 있음 `origin` | 사용자가 입력한 장소 `origin: {query \| lat,lng}` |
| 도착 | 사용자가 입력한 목적지 `destination` | **기본 축제장**, 사용자가 바꿀 수 있음 `destination` |
| 상태 조회 | `GET /api/v1/routes/return/{id}` | `GET /api/v1/routes/visit/{id}` |
| 1차 시연 | **필수(대표)** | 최종 |
| 부하 시험 대상 | 예 | 아니요 (대표 시연은 귀가만) |

**요청·응답 상세** — 접수 `POST /api/v1/routes/visit`과 상태 조회 `GET /api/v1/routes/visit/{route_request_id}`는 A04·A05와 8칸이 같고 아래만 다릅니다.

| 항목 | A04 귀가와 다른 점 |
|---|---|
| 요청 본문 | **`origin`(필수)**: 사용자 출발지(`{query}` 또는 `{lat, lng}`, 8-1절 `VisitRouteRequest`). **`destination`(선택)**: 기본은 축제 장소 `{type:"festival"}`, 입구·주차장 등으로 바꿀 수 있음(S06). 출발·도착이 둘 다 축제 장소일 수는 없음(DB CHECK, T43g) |
| 처리 | 같은 어댑터(TMAP → 카카오)·검증·기록. `route_requests.direction='visit'` |
| 출발 시각 | `now`만 (축제 시작 시각 맞춤 출발은 후속) |
| 복구·부하 | **부하 시험 대상 아님**(대표 시연은 귀가만). 단 같은 작업 풀을 쓰므로 귀가 부하 때 같이 느려질 수 있고, 그 지표는 `direction`으로 나눠 봄 |
| 상태 조회 | `GET /api/v1/routes/visit/{id}` — A05와 같은 응답(4-4절). 202 본문의 `route_access_token`을 `X-Route-Access-Token` 요청 헤더로 보내는 규칙도 같음. 다만 동기 200에는 후보 선택용 `X-Route-Access-Token` 응답 헤더가 없고, GET은 `candidate_id`를 받지 않음(버스 혼잡 선택 흐름 없음) |
| 오류 | A04와 같음. 출발지를 못 찾으면 400 `ROUTE_INVALID` |

---

## 5. 장애 대응 API

운영자가 실제로 보는 순서대로 놓았습니다. 먼저 **지표(A16)** 로 이상을 확인하고(5-1, 후속 예측 A17은 5-2), **사건 목록·상세(A14·A15)** 에서 감지된 사건과 근거를 봅니다(5-3·5-4). 이어 정책이 허용하는 **조치 목록(allowlist와 A18)** 을 확인하고(5-5·5-6), 에이전트가 고른 **복구 결정(A19)** 을 정책 코드가 검사해 실행하며(5-7), 조치 뒤 **재검증·종료 기준**으로 회복을 판정합니다(5-8). 이 흐름을 일부러 일으키는 시험 도구는 뒤에 모았습니다: 복구 시험 설계(5-9), 부하 주입 A20(5-10), 부하 시험 상태 A31(5-11), 부하 중단 A21(5-12), 혼잡 공급원 장애 모의 A22(5-13).


### 5-1. 경로 조회 지표: `GET /api/v1/admin/route-metrics` (A16)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 귀가 조회의 시간창별 지표. 운영 화면 그래프, Diagnosis(`get_route_metrics`)의 원인 구분 근거 (FR-O01, H01) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 또는 service>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | 아래 표 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 401 / 403 / 형식 422 / `incident_id`·`simulation_id`가 없는 ID면 404 |
| 6 | 정상 응답 | 200 `{window, from, to, filter, summary, series[], evidence_refs[]}` — 데이터가 없으면 `series:[]`, `summary`의 숫자는 null |
| 7 | 오류 응답 | 401 / 403 / 404 `INCIDENT_NOT_FOUND`·`SIMULATION_NOT_FOUND` / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회만(멱등). DB `route_query_metrics`(10초 단위 행)를 `window` 단위로 묶음. **p95는 행끼리 평균 낼 수 없어** 묶을 때는 각 창 p95의 최댓값을 쓰고 `p95_aggregation:"max_of_windows"`로 표시. 최대 범위 24시간(초기값) |

| 쿼리 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `incident_id` | string | 없음 | 주면 그 사건의 `detected_at` 앞 5분 ~ `closed_at`(없으면 지금) 구간 |
| `simulation_id` | string | 없음 | 주면 그 시험 전체 구간 |
| `phase` | string | 없음 | `live`·`baseline`·`fault`·`after_action` |
| `window` | string | `5m` | `10s`·`1m`·`5m`·`15m` |
| `from`·`to` | string(datetime) | 최근 15분 | `incident_id`·`simulation_id`가 있으면 무시 |

| `series[]`·`summary` 필드 | 타입 | DB `route_query_metrics` |
|---|---|---|
| `window_at`(series만)·`phase` | string | `window_at`·`phase` |
| `offered_requests`·`accepted_count`·`valid_completed_count` | int | 같은 이름 |
| `valid_route_rate` | number(0~1) | 계산 `valid_completed_count ÷ offered_requests` (**접수·HTTP 200은 성공에 넣지 않음**) |
| `rejections`·`timeouts`·`errors`, `error_rate` | int, number | 같은 이름, 계산 `(rejections+timeouts+errors) ÷ offered_requests` |
| `unique_route_keys`·`duplicate_ratio`·`backend_execution_count`·`shared_request_count`·`cache_hits` | int·number | 같은 이름 (중복·병합 판단 근거) |
| `queue_depth_max`·`inflight_max` | int | 같은 이름 |
| `p50_ms`·`p95_ms`·`upstream_p95_ms`·`internal_p95_ms` | number | 같은 이름 (외부·내부 지연 분리) |
| `is_mock` | boolean | 같은 이름 |
| `metric_id`(series만) | string | `rqm_` + `metric_id` — 복구 결정의 근거 ID로 씀 |

### 5-2. 지연 위험 예측: `GET /api/v1/admin/route-metrics/risk` (A17) — **후속(FR-H19), 1차 구현 안 함**

| 항목 | 명세 |
|---|---|
| 권한 | operator·service |
| 쿼리 | `window`: `5m`·`15m`(기본)·`1h` / `horizon`: `5m`(기본)·`15m` |
| 지금 동작 | 구현 전에는 **501 `NOT_IMPLEMENTED`**("예측 기능은 아직 없어요"). 도구 `predict_route_delay_risk`도 이 응답을 그대로 안내(BFCL NLD-03) |
| 구현 시 응답(계획) | `{risk_level: low·medium·high, method: "trend", horizon, signals[] {metric, value, threshold}, evidence_refs[] (rqm_…)}` — 추세 규칙(예: 대기열 4배 증가 → high)이며 학습 모델 아님 |

**A17 요청·후속 구현 시 응답**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `window` | query | string | 아니요 | `5m`·`15m`(기본)·`1h`, 추세를 볼 시간창 |
| `horizon` | query | string | 아니요 | `5m`(기본)·`15m`, 예측 범위 |
| `risk_level` | 응답 | string | 예 | `low`·`medium`·`high` |
| `method` | 응답 | string | 예 | `trend` |
| `horizon` | 응답 | string | 예 | 예측에 적용한 시간 범위 |
| `signals` | 응답 | array<object> | 예 | 추세 규칙에 사용한 신호 |
| `signals[].metric` | 응답 | string | 예 | 지표 이름 |
| `signals[].value` | 응답 | number | 예 | 측정한 지표 값 |
| `signals[].threshold` | 응답 | number | 예 | 추세 규칙의 판단 기준값 |
| `evidence_refs` | 응답 | array<string> | 예 | 근거 지표 ID(`rqm_…`) |

### 5-3. 사건 목록: `GET /api/v1/admin/incidents` (A14)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 운영 화면의 사건 목록(필터·페이지). 사건 하나는 A15로 상세 조회 (FR-O02) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 이상>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | 아래 필드 명세 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 401 / operator·admin이 아니면 403(service도 목록은 불가 — 에이전트는 사건 ID로 A15만) / 형식 422 |
| 6 | 정상 응답 | 200 `{items[], total, page, page_size}` (0건이면 빈 배열) |
| 7 | 오류 응답 | 401 `UNAUTHORIZED` / 403 `FORBIDDEN` / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회만(멱등). 기본 최근 7일, 최대 조회 범위 31일(초기값). 정렬 기본 `-detected_at` |

| 쿼리 | 타입 | 기본값 | 제약 |
|---|---|---|---|
| `failure_domain` | string | 없음 | `internal_route`·`route_upstream`·`agent`·`crowd_upstream`·`ingestion` |
| `status` | string | 없음 | `open`·`diagnosing`·`recovering`·`validating`·`closed` |
| `from`·`to` | string(datetime) | 최근 7일 | `from ≤ to`, 범위 ≤ 31일 |
| `simulation_id` | string | 없음 | `^sim_…` |
| `test_mode` | boolean | 없음 | 장애 주입 시험만/운영만 |
| `sort` | string | `-detected_at` | `detected_at`·`-detected_at` |
| `page`·`page_size` | int | 1·20 | page ≥ 1, page_size 1~100 |

| 응답 `items[]` 필드 | 타입 | 빈값 | DB |
|---|---|---|---|
| `incident_id`·`failure_domain`·`status`·`detection_rule` | string | 불가 | `incident_logs` |
| `detected_at`·`closed_at` | string | closed_at null | `incident_logs` |
| `simulation_id`·`comparison_arm` | string | 시험 아니면 null | `incident_logs.simulation_id` → `load_simulations` |
| `test_mode` | boolean | 불가 | `incident_logs.injected_test` |
| `final_mode`·`mttr_s` | string·int | 종료 전 null | `incident_outcomes` |

```json
{ "items": [ { "incident_id": "inc_01JD8Q3K2X", "failure_domain": "internal_route", "status": "closed", "detection_rule": "p95_ms > 3000 for 30s",
               "detected_at": "…", "closed_at": "…", "simulation_id": "sim_01JD8P…", "comparison_arm": "A1", "test_mode": true,
               "final_mode": "normal_recovered", "mttr_s": 95 } ],
  "total": 1, "page": 1, "page_size": 20 }
```

### 5-4. 사건 상세: `GET /api/v1/admin/incidents/{incident_id}` 응답 모양 (A15)

**A15 요청 경로**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `incident_id` | path | string | 예 | `^inc_[0-9A-Za-z]{6,26}$`, 조회할 사건 ID. 쿼리·본문 없음 |

```json
{
  "incident_id": "inc_01JD8Q3K2X",
  "failure_domain": "internal_route",
  "status": "closed",
  "detected_at": "…", "closed_at": "…",
  "simulation_id": "sim_…", "comparison_arm": "A1", "responder_type": "agent", "test_mode": true,
  "offered_load": { "offered_requests": 120, "concurrency": 120, "unique_route_keys": 12 },
  "detection_rule": "p95_ms > 3000 for 30s",
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
| `metrics_baseline`·`metrics_before`·`metrics_after` | object | after는 재측정 전 null | 5-9의 세 구간, **같은 모양**(`p50_ms`·`p95_ms`·`error_rate`·`valid_route_rate`·`valid_completed`·`rejections`) | `route_query_metrics`·`incident_logs.before_metrics`·`recovery_attempts.after_metrics` |
| `diagnosis` | object | null 가능 | 사실·가설·확인 불가·영향 기능·근거 | `incident_diagnostics` |
| `recovery_plans[]`·`recovery_attempts[]` | array | 빈 배열 | 결정·실행 기록 | `recovery_plans`·`recovery_attempts` |
| `status_history[]` | array | 빈 배열 | 상태 변경 이력 | `incident_events` |
| `final_mode` | string | 재측정 전 null | 5종 | `incident_outcomes.final_mode` |
| `agent_runs[]` | array | 빈 배열 | 에이전트 실행 기록 | `agent_runs` |

### 5-5. 허용 조치 allowlist (1차 시연 후보)

| action | 하는 일 | 적용 조건(정책 코드가 검사) | 원복 조건 |
|---|---|---|---|
| `singleflight_enable` | 같은 `route_key`로 진행 중인 조회 결과를 공유 | [기록 17-3](API_구현_검증기록.md#17-3-저장캐시-규칙--실제-코드-강사-1120-api-2)절의 v2 키 일치 및 동일 키 중복률 근거 | 같은 부하에서 유효 경로 완료율이 오르지 않거나 거절·시간초과 증가 |
| `bounded_queue_adjust` | 내부 대기열 길이·대기 제한 조정(상한 안에서) | 내부 대기열 증가가 주원인이고 외부 지연이 정상 | 거절률이 기준 이상 증가 |
| `valid_cache_serve` | 조건이 같은 **유효** 캐시 경로 제공 | 캐시 `valid_until` 안 + 통제 버전 일치 + `verified_at` 있음. **목적지가 다른 요청에 비슷한 캐시를 주지 않음** | 통제 버전 변경·TTL 만료 |
| `fallback_provider_switch` | 길찾기 1차(TMAP)를 잠시 건너뛰고 2차(카카오맵)로 바로 보냄 | `failure_domain=route_upstream` + 1차 오류 근거 + **2차 공급원 키·응답 확인 완료** + 2차 일일 한도 여유 | 1차 정상 응답 회복, 또는 2차 한도 80% 도달(8-3절 규칙) |
| `safe_degrade` | 경로 대신 '확인 불가 + 공식 안내' 제공, 축제 기능 유지 | 다른 조치가 없거나 효과 없음 | 정상 지표 연속 회복 |
| `rollback` | 켜 둔 조치를 끄고 원래 정책으로 복귀 | 효과 미달·부작용 근거 | — |

이 목록에 없는 조치(새 공급원 전환, 무제한 재시도, 복구 정책 끄기 등)는 `ACTION_NOT_ALLOWED`입니다. `fallback_provider_switch`는 **2차 공급원(카카오맵)을 실제 호출로 확인한 뒤에만** 켤 수 있습니다(근거: [기록 10-3](API_구현_검증기록.md#10-3-길찾기-오류-응답--내부-처리-1120-한태경-evidence오류응답_정리md). 단 카카오 결과는 A04 동기 응답 안에서만 전달되므로(6-7절) 이 조치가 켜진 동안 202로 넘어간 요청은 `ROUTE_SECONDARY_SYNC_ONLY`가 될 수 있고, 그 요청은 복구 성공으로 세지 않음). 켜는 동안 버스 혼잡 근거는 `unsupported`가 되고 경로는 캐시하지 않습니다. **목적지가 모두 다른 요청(고유 키)에서는 병합 효과가 없으므로** Recovery는 `singleflight_enable`을 기각하고 다른 조치나 보류를 고릅니다 (BFCL NLD-24).

### 5-6. 허용 조치 조회: `GET /api/v1/admin/incidents/{incident_id}/allowed-actions` (A18)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 이 사건에서 **지금** 허용되는 복구 조치·상한·켜져 있는 조치를 보여 줌. Recovery(`list_allowed_actions`)가 결정 전에 반드시 부름 (FR-H04/H05) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 또는 service>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | `incident_id`: string, 필수, `^inc_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 401 / 403 / 422 / 404 / 사건이 `closed`면 409 `INCIDENT_CLOSED` |
| 6 | 정상 응답 | 200 — 위 6-6 ⑥의 `data`와 같은 모양 |
| 7 | 오류 응답 | 401 / 403 `FORBIDDEN` / 404 `INCIDENT_NOT_FOUND` / 409 `INCIDENT_CLOSED` / 422 |
| 8 | 실행 규칙 | 조회만(멱등). 판정은 5-5 allowlist와 **같은 코드 상수 하나**(정책 코드 `policy_gate`가 쓰는 것과 동일)로 계산 — 문서·API·실행이 다른 목록을 쓰지 않게 함. 조회 결과는 참고용이고 A19에서 다시 검사 |

| 응답 필드 | 타입 | 빈값 | 설명 | 출처 |
|---|---|---|---|---|
| `incident_id`·`failure_domain` | string | 불가 | | `incident_logs` |
| `policy_version` | string | 불가 | allowlist·상한 설정 버전(복구 시험 기록에 같이 남김) | 설정 |
| `evaluated_at` | string | 불가 | 판정 시각 | 계산 |
| `active_actions[]` | array | 빈 배열 | `{action, attempt_id, enabled_at, expires_at}` 지금 켜진 조치 | `recovery_attempts`(`action_disabled_at IS NULL`), Redis `policy:route:active` |
| `allowed[]` | array | 빈 배열 | `{action, preconditions, limits, rollback_if}` 지금 쓸 수 있는 조치 | 5-5 규칙 + 지표 |
| `not_allowed[]` | array | 빈 배열 | `{action, reason}` 지금 못 쓰는 조치와 이유(에이전트가 기각 이유로 씀) | 같음 |
| `limits` | object | 불가 | `max_active_actions`(1, 초기값)·`max_attempts_per_incident`(3, 초기값 — 5-8: 조치 → 다른 조치 1회 → `safe_degrade`)·`attempts_used` | 설정·`recovery_attempts` 수 |

### 5-7. 복구 결정 기록: `POST /api/v1/admin/incidents/{incident_id}/recovery-plans` (A19)

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
| `action` | string | `select`면 예 | null 가능 | 5-5 allowlist 값. `rollback`에서 생략하면 **서버가 지금 켜진 조치로 채움** | `recovery_plans.action` |
| `reasons` | array<string> | 예 | 불가 | 1개 이상, 각 ≤300자 | `recovery_plans.reasons` |
| `rejected_actions` | array<object> | 아니요 | `[]` | `{action, reason}` | `recovery_plans.rejected_actions` |
| `stop_condition` | object | 아니요 | — | `{max_minutes, rollback_if}`. `select`에서 생략하면 **서버 기본값**(5분, '유효 경로 제공률이 오르지 않거나 거절 증가 시 원복')을 채워 저장 | `recovery_plans.stop_condition` |
| `evidence_refs` | array<string> | 예 | 불가 | 1개 이상, `diag_`·지표 ID | `recovery_plans.evidence_refs` |

**A19 실행 예약 응답 (202)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `plan_id` | 응답 | string | 예 | 기록한 복구 계획 ID |
| `incident_id` | 응답 | string | 예 | 복구 대상 사건 ID |
| `decided_by` | 응답 | string | 예 | `rule_policy`·`recovery_agent` |
| `policy_verdict` | 응답 | string | 예 | 실행 예약 시 `allowed` |
| `execution` | 응답 | string | 예 | `scheduled_by_policy_gate`, 정책 코드가 실행을 예약한 상태 |
| `attempt_id` | 응답 | string | 예 | A15에서 실행 결과를 확인할 복구 시도 ID |

**정상 응답 예시 (202)**

```json
{ "plan_id": "rp_01JD9A…", "incident_id": "inc_01JD8Q3K2X", "decided_by": "recovery_agent",
  "policy_verdict": "allowed", "execution": "scheduled_by_policy_gate", "attempt_id": "ra_01JD9B…" }
```

**거절 예시 (403)**

```json
{ "error": { "code": "ACTION_NOT_ALLOWED", "message": "허용 목록에 없는 조치예요.", "request_id": "req_…", "retryable": false } }
```

### 5-8. 조치 뒤 재검증·종료 기준

조치를 켠 뒤 **같은 부하로 재측정**하고, 결과에 따라 아래처럼 끝냅니다. 각 판정은 사건 기록에 남깁니다.

| 재측정 결과 | 판정(`validation_result`) | 다음 행동 | 기록 |
|---|---|---|---|
| 귀가 조회 p95 3초 이하를 5분 유지 | `improved` | 사건 종료 `final_mode=normal_recovered` | `recovery_attempts`, `incident_outcomes` |
| 캐시·대체 경로로 제공했고 **유효성 검사 통과**(조건·시각·`valid_until`·통제 버전 일치) | `improved` | `final_mode=valid_cache` 또는 `alternate_source` | `route_results.validity_check` |
| 지표 변화 없음 | `no_effect` | 조치 원복(`rollback`) → 다른 허용 조치 1회 더 → 그래도 없으면 `safe_degrade` | `rollback_reason`, `incident_events` |
| 나빠짐(거절·시간 초과 증가) | `worse` | **즉시 원복** → `safe_degrade` | 같음 |
| 정해진 시간(`stop_condition.max_minutes`) 안에 판정 못 함 | `no_effect` (`stop_reason=time_limit`) | 원복 후 `final_mode=unresolved`, 운영자 확인 | 같음 |
| 허용 조치가 없음 | — (`stop_reason=no_allowed_action`) | `defer` + `safe_degrade`('경로 확인 불가 + 공식 안내') | `recovery_plans.decision='defer'`, `recovery_attempts.stop_reason` |

- **캐시·대체 경로 유효성 검사 규칙:** 복구 정책의 캐시·대체 경로는 [기록 17-3](API_구현_검증기록.md#17-3-저장캐시-규칙--실제-코드-강사-1120-api-2)절의 v2 `route_key`가 일치할 때만 씁니다. **목적지가 다른 요청에 비슷한 캐시를 주지 않습니다.** 검사 결과(통과/실패와 이유)를 `route_results.validity_check`에 남깁니다.
- 초기 복구 SLO는 5-9·8-4절을 따릅니다. 유효 경로 제공률은 조치 전후 비교와 시험 성공 집계에 기록합니다.

### 5-9. 복구 시험 설계: 감지부터 경로 제공 회복까지

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

**장애 감지·복구 초기 SLO** — 귀가 조회 p95가 3초를 초과한 상태가 30초 이어지면 장애로 감지합니다. p95가 3초 이하로 5분 유지되면 복구로 판정합니다. 숫자 확정은 8-4절 규칙을 따릅니다.

**구간마다 남기는 지표:** p50·p95 지연, 오류율(시간 초과·거절·공급원 오류 포함), **유효한 경로 제공률 = 검증된 경로가 담긴 응답 수 ÷ 보낸 요청 수**(대기열 접수·HTTP 200은 성공에 넣지 않음), 감지까지 걸린 시간, 조치 후 회복까지 걸린 시간(MTTR).

### 5-10. 부하 주입: `POST /api/v1/admin/simulations/route-load` (A20)

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
| `comparison_arm` | string | 예 | `B0`·`B1`·`A1` | 대응 방식(5-9) |
| `concurrency` | int | 예 | 1~200(초기값) | 동시 요청 |
| `offered_rps` | number | 아니요 | 0 초과 ~100 | 초당 요청 |
| `duration_s` | int | 예 | 5~300(초기값) | 구간별 지속 시간 |
| `unique_route_keys` | int | 예 | 1~1000 | 서로 다른 경로 키 수 |
| `fault` | object | 아니요 | `{ "type": "internal_delay", "delay_ms": 1~5000 }` | 장애 주입(없으면 평소 구간만) |
| `cache_state` | string | 아니요 | `cold`·`warm` | 캐시 준비 상태 |
| `repeat_group` / `run_index` | string / int | 아니요 | ≤40자 / 1~20 | 반복 묶음·몇 번째 |
| `upstream` | string | 아니요 | `mock_adapter`만 | **외부 공급원 부하 금지** |
| `seed` | int | 아니요 | — | 재현 |

응답(202): `simulation_id`·`test_mode`·`comparison_arm`·`status`·`stop_url`·`status_url`. 결과는 **A31 `GET /api/v1/admin/simulations/{simulation_id}`**(조회 성공이면 시험이 실패했어도 200, 실패는 `status`·`error`로)로 확인합니다. 요청 헤더에 `Idempotency-Key`(필수)를 받아 같은 키면 처음 만든 `simulation_id`를 돌려줍니다.

**A20 접수 응답 (202)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `simulation_id` | 응답 | string | 예 | 등록한 시험 ID |
| `test_mode` | 응답 | boolean | 예 | `true`, 시험 환경 요청 |
| `comparison_arm` | 응답 | string | 예 | `B0`·`B1`·`A1` 중 선택한 대응 방식 |
| `status` | 응답 | string | 예 | 접수 시 `running` |
| `stop_url` | 응답 | string | 예 | A21 시험 중단 경로 |
| `status_url` | 응답 | string | 예 | A31 시험 상태 조회 경로 |

- 부하 생성기는 **팀 서버 안의 경로 처리 구간과 시험용 어댑터**에만 요청을 보냅니다. 외부 공급원은 부르지 않습니다.
- 장애 기준을 넘으면 관측 코드가 `incident_id`를 만들고 시뮬레이션 기록에 연결합니다. **시뮬레이션 1회에 사건이 여러 건 생길 수 있습니다**(감지 → 원복 → 재감지). 시뮬레이션이 사건을 직접 만들지 않습니다 — 감지 로직도 시험 대상이기 때문입니다.
- B0/B1/A1을 비교할 때는 `scenario`·`concurrency`·`offered_rps`·`duration_s`·`unique_route_keys`·`seed`·`cache_state`를 **똑같이** 두고, 같은 `repeat_group`으로 여러 번(`run_index`) 돌립니다 (FR-H23).
- 끝나면 결과 JSON·보고서 위치를 `load_simulations.result_ref`·`report_ref`에 남깁니다.

| 상태 코드 | 조건 | 응답 코드 |
|---|---|---|
| 422 | 상한 초과·잘못된 시나리오(형식 검사) | `VALIDATION_ERROR` |
| 401 / 403 | 인증 실패 / operator 아님 | `UNAUTHORIZED` / `FORBIDDEN` |
| 403 | 운영 환경(`APP_ENV=prod`)에서 호출 | `SIMULATION_DISABLED` |
| 409 | 이미 실행 중인 시뮬레이션 있음 | `SIMULATION_RUNNING` |

### 5-11. 부하 시험 상태: `GET /api/v1/admin/simulations/{simulation_id}` (A31)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 목적 | A20으로 시작한 부하 시험의 진행·결과 확인. 사건이 안 생긴 시험(평소 구간만)도 여기서 봄 |
| 2 | 헤더 | `Authorization: Bearer <operator 이상>` |
| 3 | 경로 | `simulation_id`: 필수, `^sim_[0-9A-Za-z]{6,26}$` |
| 5 | 검증·권한 | 401 / 403 / 404 `SIMULATION_NOT_FOUND` / 422 |
| 6 | 정상 | **200** — 시험이 실패해도 조회는 200, 실패는 `status`·`error`로 |
| 8 | 실행 규칙 | 조회만. 구간 지표는 A16과 같은 계산(같은 함수) |

| 응답 필드 | 타입 | 빈값 | DB |
|---|---|---|---|
| `simulation_id`·`status`(`running`·`stopped`·`finished`·`failed`) | string | 불가 | `load_simulations` |
| `scenario` | string | 불가 | `duplicate_keys`·`unique_keys`·`mixed`, `load_simulations.scenario` |
| `comparison_arm` | string | 불가 | `B0`·`B1`·`A1`, `load_simulations.comparison_arm` |
| `concurrency` | int | 불가 | 동시 요청 수 |
| `offered_rps` | number | null 가능 | 초당 요청 수 |
| `duration_s` | int | 불가 | 구간별 지속 시간(초) |
| `unique_route_keys` | int | 불가 | 서로 다른 경로 키 수 |
| `cache_state` | string | 불가 | `cold`·`warm` |
| `fault` | object | null 가능 | A20의 `{type, delay_ms}` |
| `seed` | int | null 가능 | 재현용 시드 |
| `repeat_group` | string | null 가능 | 반복 시험 묶음 |
| `run_index` | int | 불가 | 묶음 안 시험 순번 |
| `upstream` | string | 불가 | `mock_adapter` |
| `limits_version`·`code_version` | string | 불가 | 결과 JSON·`code_version` (8-4) |
| `phases[]` | array | 빈 배열 | `{phase, offered_requests, valid_route_rate, error_rate, p50_ms, p95_ms}` — `route_query_metrics` 구간별 |
| `incidents[]` | array | 빈 배열 | `{incident_id, detected_at, final_mode}` — `incident_logs`·`incident_outcomes` |
| `started_at`·`ended_at` | string | ended null 가능 | |
| `result_ref`·`report_ref` | string | null | 결과 JSON·보고서 위치(GitHub) |
| `error` | object | null | `failed`일 때 `{code, message}` |

### 5-12. 부하 시험 중단: `POST /api/v1/admin/simulations/{simulation_id}/stop` (A21)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 실행 중인 부하 시험을 즉시 멈춤 — 시연 중 문제가 생겼을 때 운영자가 누르는 정지 버튼 (FR-O03) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 이상>`(필수, service 불가 — 에이전트는 시험을 멈추거나 시작하지 않음) · `X-Request-ID` |
| 3 | 경로·쿼리 | `simulation_id`: string, 필수, `^sim_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 선택 `{ "reason": "시연 중 화면 멈춤" }` (≤200자) |
| 5 | 검증·권한 | 401 / 403 / 422 / 404 `SIMULATION_NOT_FOUND` / 운영 환경 403 `SIMULATION_DISABLED` |
| 6 | 정상 응답 | **200** `{simulation_id, status, stop_requested_at, stopped_at, affected_incidents[]}` — `status`는 `stopping`(정리 중) 또는 `stopped`. 이미 `stopped`·`finished`·`failed`면 **같은 200으로 현재 상태**를 돌려줌(여러 번 눌러도 안전 = 멱등) |
| 7 | 오류 응답 | 401 / 403 `FORBIDDEN`·`SIMULATION_DISABLED` / 404 `SIMULATION_NOT_FOUND` / 422 |
| 8 | 실행 규칙 | ① 부하 생성기에 중지 신호 → 2초 안(초기값) 새 요청 중단 ② `load_simulations.status='stopped'`, `ended_at`, `offered_requests`(지금까지 보낸 수) 기록 ③ 이 시험에서 생긴 **열린 사건**은 켜진 조치를 정책 코드가 원복(`rollback_reason='simulation_stopped'`)하고 `final_mode='unresolved'`로 닫음 — 중단된 시험을 복구 성공으로 세지 않음 ④ 결과는 A31로 확인 |

**A21 중단 요청·응답 (200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `simulation_id` | path | string | 예 | `^sim_[0-9A-Za-z]{6,26}$`, 중단할 시험 ID |
| `reason` | body | string | 아니요 | 중단 사유, 200자 이하 |
| `simulation_id` | 응답 | string | 예 | 대상 시험 ID |
| `status` | 응답 | string | 예 | `stopping`·`stopped`. 이미 끝난 시험은 현재 `stopped`·`finished`·`failed` 상태 |
| `stop_requested_at` | 응답 | string(date-time) 또는 null | 예 | 중단 요청 기록 시각 |
| `stopped_at` | 응답 | string(date-time) 또는 null | 예 | 중단 완료 시각, 정리 중에는 null |
| `affected_incidents` | 응답 | array<object> | 예 | 시험 중단으로 닫은 열린 사건 |
| `affected_incidents[].incident_id` | 응답 | string | 예 | 닫은 사건 ID |
| `affected_incidents[].action_rolled_back` | 응답 | string 또는 null | 예 | 원복한 조치(5-5절), 켜진 조치가 없으면 null |
| `affected_incidents[].final_mode` | 응답 | string | 예 | `unresolved`, 중단으로 닫은 사건의 최종 모드 |

```json
{ "simulation_id": "sim_01JD8P…", "status": "stopping", "stop_requested_at": "2026-11-20T14:06:00+09:00", "stopped_at": null,
  "affected_incidents": [ { "incident_id": "inc_01JD8Q3K2X", "action_rolled_back": "singleflight_enable", "final_mode": "unresolved" } ] }
```

### 5-13. 혼잡 공급원 장애 모의: `POST /api/v1/admin/simulations/crowd` (A22, 보조)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 목적 | 서울 혼잡 API(A10) 장애를 **모의 어댑터로** 재현해, 혼잡이 없어도 축제·귀가 기능이 유지되는지 시험(FR-H20) |
| 2 | 헤더 | `Authorization: Bearer <operator 이상>` · `Idempotency-Key`(필수) |
| 4 | 본문 | `{mode: "http_500"·"stale"·"body_error", duration_s: 5~300}` |
| 5 | 검증·권한 | 401 / 403 / 운영 환경 403 `SIMULATION_DISABLED` / 이미 켜져 있으면 409 `SIMULATION_RUNNING` / 422 |
| 6 | 정상 | 202 `{fault_id, mode, ends_at}` — 별도 상태 조회 API는 두지 않음. 모의 장애는 `ends_at`까지 켜져 있다가 Redis TTL로 자동 해제되고, 켜져 있는 동안 다시 요청하면 409 `SIMULATION_RUNNING`. 결과는 A10 응답이 모의 장애 응답으로 바뀌는지와, 감지되면 생기는 `failure_domain=crowd_upstream` 사건(A15 사건 상세)으로 확인. `Idempotency-Key`는 `duration_s` 동안 보관하고, 같은 키·같은 본문은 같은 202를, 같은 키·다른 본문은 409를 돌려줌(A04와 같은 규칙) |
| 8 | 실행 규칙 | 실제 서울시 API에는 아무것도 안 함 — A10 어댑터가 Redis `fault:crowd`(TTL = `duration_s`)를 보고 모의 응답을 냄. 감지되면 `failure_domain=crowd_upstream` 사건으로 기록. **귀가 부하 시험(A20)과 별개**이고 대표 시연 아님 |

**A22 요청·202 응답 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `Idempotency-Key` | header | string | 예 | 시험 모의 요청의 중복 방지 키 |
| `mode` | body | string | 예 | `http_500`·`stale`·`body_error` |
| `duration_s` | body | int | 예 | 5~300초 |
| `fault_id` | 응답 | string | 예 | 등록한 혼잡 공급원 장애 모의 ID |
| `mode` | 응답 | string | 예 | 요청에서 선택한 장애 모의 유형 |
| `ends_at` | 응답 | string(date-time) | 예 | 장애 모의 종료 시각 |

---

## 6. AI Tool (에이전트가 부르는 함수)

이 절에는 에이전트가 부르는 도구의 정의(6-1~6-6), 도구 호출 흐름(6-7), 도구별 입력 스키마와 실행 조건(6-8), 그리고 이 도구들을 실행하는 챗봇 질문 API A06(6-9)을 모았습니다.

에이전트 도구는 모두 **내부 API를 감싼 얇은 함수**입니다. 아래 13개 도구의 계약은 BFCL 30문항 채점에 사용합니다([기록 4-7](API_구현_검증기록.md#4-7-bfcl-30문항과의-대조-강사-일일-피드백-5)절). 평가가 시작되면 이름·인자를 바꾸지 않습니다.

### 6-1. 도구 목록 (BFCL 기준 13개)

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

### 6-2. 추가 후보 도구 (BFCL 30문항 밖)

서비스 범위의 데이터를 에이전트가 쓰려면 아래 도구가 필요합니다. **BFCL 30문항에는 넣지 않았습니다**(평가 기준을 바꾸지 않기 위해). 평가 문항을 늘릴 때 함께 넣습니다.

| Tool 이름 | 호출 주체 | 감싸는 API | 쓰는 곳 |
|---|---|---|---|
| `request_visit_route` | Route | `POST /api/v1/routes/visit` | 축제 가는 길 |
| `get_weather` | Festival·Route | `GET /api/v1/festivals/{id}/weather` | 날씨 안내 |
| `get_transit_arrivals` | Route | `GET /api/v1/festivals/{id}/transit` | 주변 지하철·버스 도착 |

| `get_traffic_incidents` | Route | `GET /api/v1/festivals/{id}/traffic-incidents` | 교통 돌발 |

**도구로 만들지 않는 것 (에이전트가 절대 부를 수 없음)**
- 장애·부하 주입(`POST /api/v1/admin/simulations/*`): 운영자가 관리자 화면에서만 실행합니다. 챗봇 대화로 요청해도 도구가 없으므로 호출이 일어나지 않습니다 (BFCL NLD-27의 `run_simulation` 금지).
- 복구 정책 끄기·allowlist 수정·권한 변경: 코드 설정이며 API·도구가 없습니다 (BFCL NLD-30).
- 조치의 **실제 실행**: `propose_recovery_action`은 제안을 기록할 뿐입니다. 실행은 정책 코드(`policy_gate`)가 합니다.

### 6-3. 대표 Tool 명세: `request_return_route`

| 항목 | 명세 |
|---|---|
| **Tool 개요** | 선택한 축제장에서 목적지까지 귀가 경로를 요청 |
| **호출 주체** | Route Agent |
| **입력** | `{"festival_id":"fst_000123","destination":{"query":"서울역"},"travel_mode":"transit","route_preference":"fastest","user_constraints":{"with_child":true}}` (멱등 키 `request_id`는 도구 래퍼가 새 UUID로 자동 생성하고, 같은 도구 호출을 재시도할 때만 같은 값을 다시 씀) |
| **출력** | 6-5절 공통 형식: `{"ok":true,"data":{"route_request_id":"rr_…","route_status":"ready","completed_valid_route":true,"route_candidates":[…],"provider":"…","queried_at":"…","verification_status":"…","is_mock":false},"request_id":"req_…"}` / 실패 `{"ok":false,"error":{"code":"ROUTE_TIMEOUT","message":"…","retryable":true},"request_id":"req_…"}` |
| **실패** | `FESTIVAL_NOT_FOUND` / `FESTIVAL_LOCATION_UNKNOWN` / `ROUTE_INVALID` / `ROUTE_TIMEOUT` / `ROUTE_OVERLOADED` / `ROUTE_PROVIDER_UNVERIFIED` |
| **호출 전 조건** | `festival_id`와 목적지가 **모두 확정**돼야 호출. 목적지를 모르면 호출하지 않고 사용자에게 묻습니다 (BFCL NLD-19·20) |
| **재시도** | 도구 래퍼가 `ROUTE_TIMEOUT`에 한해 1회, 같은 `request_id`로만 재시도(새 요청 생성 금지) |

### 6-4. 대표 Tool 명세: `propose_recovery_action`

| 항목 | 명세 |
|---|---|
| **Tool 개요** | Recovery Agent가 진단을 보고 허용된 조치 하나를 선택·기각·보류·원복한 결정을 기록 |
| **호출 주체** | Recovery Agent |
| **입력** | `{"incident_id":"inc_01JD8Q3K2X","decision":"select","action":"singleflight_enable","reasons":["unique_route_keys=12/120, duplicate_ratio=0.9"],"rejected_actions":[{"action":"bounded_queue_adjust","reason":"중복 작업이 주원인"}],"stop_condition":{"max_minutes":5,"rollback_if":"valid_completed_rate가 오르지 않거나 rejections 증가"},"evidence_refs":["diag_01JD8Q3K2Y"]}` |
| **출력** | 6-5절 공통 형식: `{"ok":true,"data":{"plan_id":"rp_…","policy_verdict":"allowed","execution":"scheduled_by_policy_gate"},"request_id":"req_…"}` / 거절 `{"ok":false,"error":{"code":"ACTION_NOT_ALLOWED","message":"…","retryable":false},"request_id":"req_…"}` |
| **실패** | `ACTION_NOT_ALLOWED`(allowlist 밖) / `EVIDENCE_REQUIRED`(근거 ID 없음) / `INCIDENT_CLOSED` / `POLICY_LIMIT_EXCEEDED` |
| **decision 값** | `select`(선택) / `reject`(기각만 기록) / `defer`(근거 부족으로 보류 — 조치 없음, 안전 정책 유지) / `rollback`(이전에 켠 조치 원복 제안) |

### 6-5. 도구 공통 출력 형식과 실패 뒤 처리 (수업 가이드 S24·S25)

모든 도구는 성공·실패를 **같은 모양**으로 돌려줍니다. 에이전트는 `ok`와 `retryable`만 보고 다음 행동을 정합니다. LLM이 만든 인자도 사용자 입력처럼 다뤄 도구 안에서 8-1절 검증을 한 번 더 합니다.

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
| `FESTIVAL_NOT_FOUND` | false | 재시도 없이 축제 재선택을 안내하고 `clarification_needed`로 종료 |
| `INCIDENT_NOT_FOUND` | false | 재시도 없이 사건 검색 단계로 되돌아감 |
| `FORBIDDEN`·`ACTION_NOT_ALLOWED` | false | 멈추고 이유를 안내. 다른 방법으로 우회하지 않음 |
| `EVIDENCE_REQUIRED` | false | Diagnosis 단계로 되돌려 근거를 다시 모음 |
| `REGION_UNSUPPORTED` | false | 실패가 아님 — '이 지역은 미지원'으로 그대로 안내 |
| `FESTIVAL_LOCATION_UNKNOWN` | false | 재시도 없이 '축제 위치를 확인할 수 없어 경로를 찾을 수 없음'으로 안내하고 출발지·도착지를 직접 고르게 함 |
| `ROUTE_OVERLOADED` | true | `Retry-After` 뒤 **같은 `request_id`로 1회**. 그래도 실패면 '지금은 경로 조회가 많아 확인할 수 없음 + 잠시 후 다시'로 종료 |
| `INCIDENT_CLOSED` | false | 재시도 없이 멈추고 '이미 닫힌 사건'으로 안내. 새 조치를 제안하지 않음 |
| `POLICY_LIMIT_EXCEEDED` | false | 재시도 없이 멈추고 상한(동시에 켠 조치 수 등)을 안내. 이미 켠 조치가 끝난 뒤 사람이 다시 요청 |
| `SIMULATION_NOT_FOUND` | false | 재시도 없이 `simulation_id`를 확인해 달라고 안내(사건 ID만 있으면 그 ID로 다시 조회) |
| `DB_POOL_TIMEOUT` | true | `Retry-After`(1초) 뒤 1회. 그래도 실패면 '잠시 후 다시'로 종료 (DB 연결 대기 초과) |

**Festival Agent 기준.** 단일 Festival Agent 상태 전이 그래프 설계서 8~8-1절과 도구 래퍼·그래프를 기준으로 합니다. HTTP/본문 값은 API 응답이고, `outcome`은 Agent 종료 상태입니다.

| 사례 | API 응답·차이 | Festival Agent 처리 |
|---|---|---|
| 없는 축제 ID | A03·A10 HTTP 404, `FESTIVAL_NOT_FOUND`, `retryable=false` | 축제 재선택 안내 후 `clarification_needed`. 복합 조회에서 앞 단계 답변이 있으면 재선택 안내와 함께 `partial` |
| 일시 오류·시간 초과 | HTTP 오류나 전송 시간 초과에서 도구가 `ok:false`와 `retryable:true`를 반환할 수 있음 | 같은 단계 최대 1회 재시도. 전체 4회·기본 30초 예산 안에서 수행하며, 최종 실패 시 `unavailable` 또는 앞 단계 답변을 담은 `partial` |
| 혼잡 미지원 | A10 HTTP 200, `status:"unsupported"`. 서울 밖·좌표 누락·승인 매핑 없음·반경 내 구역 없음은 A10의 `unsupported_reason` 참조 | 같은 도구 추가 호출 없이 미지원 안내. 단독은 `unsupported`, 앞 단계 답변이 있는 복합 조회는 `partial`. Agent 설계서 8-1절의 좌표 누락 예시와 달리 현 A10은 좌표 누락도 `unsupported`로 반환 |
| 혼잡 관측이 오래됨 | A10 HTTP 200, `status:"stale"`, `observed_at` 유지. 실제 모드에는 A10의 45분 기준을 적용 | 같은 도구 추가 호출 없이 관측 시각과 오래된 정보라는 경고를 제시하고 `answered`. 출처·시각·지원 범위 검증 실패 시 확인 불가 처리 |
| 혼잡 자료를 얻지 못함 | A10 HTTP 200, `status:"unavailable"`. 본문의 `error.retryable`은 공급원 오류 정보이며 래퍼의 `ok`는 `true` | 본문 상태를 처리해 같은 도구 추가 호출 없이 확인 불가 안내. 단독은 `unavailable`, 앞 단계 답변이 있는 복합 조회는 `partial` |

**도구 실행 전 서버가 확인하는 4가지(S26):** ① 이 에이전트에 허용된 도구인가(에이전트별 허용 목록) ② 요청한 사용자의 권한(사용자가 못 하는 일은 에이전트도 못 함) ③ 대상이 그 사용자가 볼 수 있는 자원인가(`save_favorite`는 세션 사용자 본인만) ④ 복구 조치는 allowlist·근거 ID·상한을 정책 코드(`policy_gate`)가 검사.

**API의 `X-Request-ID`와 도구 출력의 추적 ID(`request_id`, `req_…`)는 같은 값**으로 이어, 로그에서 요청 하나를 끝까지 추적합니다. 경로 요청의 멱등 키(UUID)와는 다른 값입니다.

### 6-6. 도구 description과 JSON Schema (1차 필수 도구)

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

**JSON Schema와 출력 예시 — 필수 도구 6개 **

아래 6개는 BFCL 정답 이름·인자와 같습니다([기록 4-7](API_구현_검증기록.md#4-7-bfcl-30문항과의-대조-강사-일일-피드백-5)). 성공·실패 출력은 모두 6-5절 공통 형식이고, `data`는 감싸는 API의 응답 본문입니다. 도구 래퍼는 LLM이 만든 인자를 이 스키마로 한 번 더 검사하고, 어긋나면 API를 부르지 않고 `VALIDATION_ERROR`(retryable=false)를 돌려줍니다.

- **ID 형식(`fst_…`·`rr_…`·`inc_…`·`sim_…`)은 도구 스키마에 `pattern`으로 넣지 않습니다.** BFCL 평가는 가상 ID(`F01`·`RR02`·`INC-010`)를 쓰므로([기록 4-7](API_구현_검증기록.md#4-7-bfcl-30문항과의-대조-강사-일일-피드백-5)) 스키마에 넣으면 정답 호출이 막힙니다. 형식 검사는 감싸는 API의 Pydantic 검증(422 → 도구 출력 `VALIDATION_ERROR`)이 합니다.

**① `search_festivals`** — 감싸는 API: A02 `GET /api/v1/festivals`

```json
{
  "name": "search_festivals",
  "description": "지역·기간·키워드로 축제 목록을 찾는다. 상대 날짜(\"이번 주말\")는 대화의 기준 날짜로 바꿔서 넣는다. 축제를 정하기 전에 쓴다.",
  "parameters": {
    "type": "object",
    "properties": {
      "region": { "type": "string", "enum": ["ALL","SEOUL","BUSAN","DAEGU","INCHEON","GWANGJU","DAEJEON","ULSAN","SEJONG","GYEONGGI","GANGWON","CHUNGBUK","CHUNGNAM","JEONBUK","JEONNAM","GYEONGBUK","GYEONGNAM","JEJU"], "default": "ALL" },
      "date_from": { "type": "string", "format": "date", "description": "YYYY-MM-DD. 이 기간과 겹치는 축제" },
      "date_to": { "type": "string", "format": "date", "description": "YYYY-MM-DD. date_from 이상, 최대 366일" },
      "q": { "type": "string", "minLength": 1, "maxLength": 50, "description": "축제 이름·장소 키워드" },
      "status": { "type": "string", "enum": ["upcoming", "ongoing", "ended", "cancelled"] },
      "page_size": { "type": "integer", "minimum": 1, "maximum": 20, "default": 10 }
    },
    "required": [],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA1…", "is_mock": false,
  "data": { "items": [ { "festival_id": "fst_01JD7Z…", "name": "광화문 겨울 축제", "region_code": "SEOUL", "venue_name": "광화문광장",
                         "lat": 37.5759, "lng": 126.9768, "start_date": "2026-11-21", "end_date": "2026-11-22", "event_status": "upcoming",
                         "thumbnail_url": null, "source": "tourapi", "last_synced_at": "2026-11-20T06:00:00+09:00" } ],
            "total": 1, "page": 1, "page_size": 10 } }
{ "ok": false, "request_id": "req_01JDA1…", "error": { "code": "VALIDATION_ERROR", "message": "date_to가 date_from보다 빨라요.", "retryable": false } }
```

- 결과가 0건이어도 `ok:true`, `items:[]`입니다(실패 아님). 에이전트는 조건을 넓히거나 사용자에게 묻습니다.
- 실패 코드: `VALIDATION_ERROR` / `TOOL_TIMEOUT`(retryable) / `RATE_LIMITED`(retryable).

**② `get_festival`** — 감싸는 API: A03 `GET /api/v1/festivals/{festival_id}`

```json
{
  "name": "get_festival",
  "description": "축제 하나의 장소·좌표·일정·출처를 확인한다. 귀가 출발점을 확인하거나 사용자가 고른 축제를 자세히 볼 때 쓴다. 어떤 축제인지 모르면 쓰지 말고 묻는다.",
  "parameters": {
    "type": "object",
    "properties": {
      "festival_id": { "type": "string", "description": "축제 ID (search_festivals 결과의 festival_id 그대로)" }
    },
    "required": ["festival_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA2…", "is_mock": false,
  "data": { "festival_id": "fst_01JD7Z…", "name": "광화문 겨울 축제", "region_code": "SEOUL", "venue_name": "광화문광장", "address": null,
            "lat": 37.5759, "lng": 126.9768, "start_date": "2026-11-21", "end_date": "2026-11-22", "event_status": "upcoming",
            "overview": null, "fee_text": "무료", "homepage_url": null, "image_url": null,
            "source": "tourapi", "source_ref": "3035607", "last_synced_at": "2026-11-20T06:00:00+09:00" } }
{ "ok": false, "request_id": "req_01JDA2…", "error": { "code": "FESTIVAL_NOT_FOUND", "message": "축제를 찾을 수 없어요.", "retryable": false } }
```

- `lat`/`lng`가 `null`이면 귀가 경로를 요청하지 않고 "출발 위치를 확인할 수 없어요"로 답합니다(A04가 400 `FESTIVAL_LOCATION_UNKNOWN`).
- 실패 코드: `FESTIVAL_NOT_FOUND`(재시도 없이 재선택 안내 후 종료) / `VALIDATION_ERROR` / `TOOL_TIMEOUT`.

**③ `get_route_request_status`** — 감싸는 API: A05 `GET /api/v1/routes/return/{route_request_id}`

```json
{
  "name": "get_route_request_status",
  "description": "이미 요청한 귀가 경로의 처리 상태를 확인한다. queued·processing은 성공이 아니다. ready이고 completed_valid_route가 true일 때만 경로를 안내한다.",
  "parameters": {
    "type": "object",
    "properties": {
      "route_request_id": { "type": "string", "description": "경로 요청 ID (request_return_route 결과의 route_request_id 그대로)" }
    },
    "required": ["route_request_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA3…", "is_mock": true,
  "data": { "route_request_id": "rr_01JD8Q3K2M", "route_status": "processing", "completed_valid_route": false, "retry_after_s": 2 } }
{ "ok": true, "request_id": "req_01JDA3…", "is_mock": true,
  "data": { "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false,
            "error": { "code": "ROUTE_UPSTREAM_ERROR", "message": "길찾기 공급원 오류예요.", "retryable": true },
            "notices": ["지금은 경로를 확인할 수 없어요. 공식 안내를 확인해 주세요."] } }
{ "ok": false, "request_id": "req_01JDA3…", "error": { "code": "ROUTE_REQUEST_NOT_FOUND", "message": "경로 요청을 찾을 수 없어요.", "retryable": false } }
```

- **조회 성공 = `ok:true`**입니다. 경로 처리가 실패해도(`unavailable`·`timed_out`·`rejected`) 도구는 성공이고, 실패 이유는 `data.error`에 있습니다(A05가 200인 것과 같음).
- 요청 토큰(`X-Route-Access-Token`)은 **도구 인자로 받지 않습니다.** 래퍼가 같은 대화(`run_id`)에서 `request_return_route`가 받은 토큰을 서버 쪽 실행 상태에서 꺼내 붙입니다. 다른 대화의 `route_request_id`면 토큰이 없어 `FORBIDDEN`입니다(타인 요청 조회 차단, PLAN-TC-01).
- 폴링 상한: 2초 간격·최대 5회(8-4 ③ 제한값). 넘으면 "확인 불가"로 답합니다.
- 실패 코드: `ROUTE_REQUEST_NOT_FOUND` / `FORBIDDEN` / `UNAUTHORIZED`(DB 모드의 토큰 만료 → 새 `request_id`로 `request_return_route` 다시 호출) / `TOOL_TIMEOUT`.

**④ `get_incident`** — 감싸는 API: A15 `GET /api/v1/admin/incidents/{incident_id}` (service 권한, 운영자 맥락)

```json
{
  "name": "get_incident",
  "description": "(운영자 맥락) 사건 하나의 감지 근거·상태·지표 요약을 본다. 진단의 첫 단계에서 쓴다. 사건 ID가 없으면 쓰지 않는다.",
  "parameters": {
    "type": "object",
    "properties": {
      "incident_id": { "type": "string", "description": "사건 ID (대화·운영 맥락에 주어진 incident_id 그대로)" }
    },
    "required": ["incident_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA4…", "is_mock": true,
  "data": { "incident_id": "inc_01JD8Q3K2X", "failure_domain": "internal_route", "status": "diagnosing",
            "detected_at": "2026-11-20T14:02:10+09:00", "closed_at": null, "detection_rule": "p95_ms > 3000 for 30s",
            "simulation_id": "sim_01JD8P…", "comparison_arm": "A1", "responder_type": "agent", "test_mode": true,
            "offered_load": { "offered_requests": 120, "concurrency": 120, "unique_route_keys": 12 },
            "metrics_before": { "p50_ms": 1800, "p95_ms": 4500, "error_rate": 0.18, "valid_route_rate": 0.62, "valid_completed": 74, "rejections": 9 },
            "diagnosis": null, "recovery_plans": [], "recovery_attempts": [], "status_history": [ { "from": "open", "to": "diagnosing", "at": "…", "actor": "service" } ],
            "metrics_after": null, "final_mode": null, "agent_runs": [] } }
{ "ok": false, "request_id": "req_01JDA4…", "error": { "code": "INCIDENT_NOT_FOUND", "message": "사건을 찾을 수 없어요.", "retryable": false } }
```

- 숫자는 모양을 보이기 위한 가상 값입니다. 필드 뜻은 5-4절 표와 같습니다.
- 실패 코드: `INCIDENT_NOT_FOUND` / `FORBIDDEN`(운영자 맥락이 아닌 대화에서 호출 — 서버가 막음, BFCL NLD-27) / `TOOL_TIMEOUT`.

**⑤ `get_route_metrics`** — 감싸는 API: A16 `GET /api/v1/admin/route-metrics` (service 권한)

```json
{
  "name": "get_route_metrics",
  "description": "(운영자 맥락) 귀가 조회 지표(요청량·p95·대기열·거절·중복률·내부/외부 지연)를 본다. 원인을 구분할 때 쓴다. 사건 또는 부하 시험 ID를 알면 함께 넣는다.",
  "parameters": {
    "type": "object",
    "properties": {
      "incident_id": { "type": "string", "description": "사건 ID (대화·운영 맥락에 주어진 incident_id 그대로)" },
      "simulation_id": { "type": "string", "description": "부하 시험 ID (있을 때만)" },
      "window": { "type": "string", "enum": ["10s", "1m", "5m", "15m"], "default": "5m" }
    },
    "required": [],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA5…", "is_mock": true,
  "data": { "window": "1m", "from": "2026-11-20T14:00:00+09:00", "to": "2026-11-20T14:05:00+09:00",
            "filter": { "incident_id": "inc_01JD8Q3K2X", "simulation_id": "sim_01JD8P…", "phase": null },
            "summary": { "offered_requests": 600, "valid_completed_count": 372, "valid_route_rate": 0.62, "rejections": 41, "timeouts": 63,
                         "unique_route_keys": 12, "duplicate_ratio": 0.98, "backend_execution_count": 600, "shared_request_count": 0, "cache_hits": 0,
                         "queue_depth_max": 20, "p95_ms": 4500, "p95_aggregation": "max_of_windows", "upstream_p95_ms": 420, "internal_p95_ms": 4100 },
            "series": [ "…시간창마다 같은 모양(5-1절)…" ],
            "evidence_refs": ["rqm_10231", "rqm_10235"] } }
{ "ok": false, "request_id": "req_01JDA5…", "error": { "code": "INCIDENT_NOT_FOUND", "message": "사건을 찾을 수 없어요.", "retryable": false } }
```

- `upstream_p95_ms`(외부)와 `internal_p95_ms`(내부)를 나눠 주므로 Diagnosis는 "내부 지연인지 외부 지연인지"를 숫자로 구분합니다(BFCL NLD-23~25).
- `evidence_refs`의 `rqm_…`는 지표 행 ID(`route_query_metrics.metric_id`)라서 `propose_recovery_action`의 근거로 그대로 씁니다.
- 실패 코드: `INCIDENT_NOT_FOUND` / `SIMULATION_NOT_FOUND` / `VALIDATION_ERROR` / `FORBIDDEN` / `TOOL_TIMEOUT`.

**⑥ `list_allowed_actions`** — 감싸는 API: A18 `GET /api/v1/admin/incidents/{incident_id}/allowed-actions` (service 권한)

```json
{
  "name": "list_allowed_actions",
  "description": "(운영자 맥락) 이 사건에서 지금 허용된 복구 조치와 상한을 본다. 복구 결정 전에 반드시 쓴다. 여기 없는 조치는 제안하지 않는다.",
  "parameters": {
    "type": "object",
    "properties": {
      "incident_id": { "type": "string", "description": "사건 ID (대화·운영 맥락에 주어진 incident_id 그대로)" }
    },
    "required": ["incident_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA6…", "is_mock": true,
  "data": { "incident_id": "inc_01JD8Q3K2X", "failure_domain": "internal_route", "policy_version": "policy-0.3",
            "evaluated_at": "2026-11-20T14:03:00+09:00",
            "active_actions": [],
            "allowed": [ { "action": "singleflight_enable", "preconditions": { "duplicate_ratio_min": 0.5 }, "limits": { "max_minutes": 5 },
                           "rollback_if": "같은 부하에서 유효 경로 제공률이 오르지 않거나 거절·시간 초과 증가" },
                         { "action": "bounded_queue_adjust", "preconditions": { "upstream_p95_normal": true }, "limits": { "max_minutes": 5, "queue_max": 50 },
                           "rollback_if": "거절률 증가" },
                         { "action": "safe_degrade", "preconditions": {}, "limits": { "max_minutes": 10 }, "rollback_if": "정상 지표 연속 회복" } ],
            "not_allowed": [ { "action": "fallback_provider_switch", "reason": "failure_domain이 route_upstream이 아님" },
                             { "action": "valid_cache_serve", "reason": "유효 캐시 없음" },
                             { "action": "rollback", "reason": "켜진 조치 없음" } ],
            "limits": { "max_active_actions": 1, "max_attempts_per_incident": 3, "attempts_used": 0 } } }
{ "ok": false, "request_id": "req_01JDA6…", "error": { "code": "INCIDENT_CLOSED", "message": "이미 닫힌 사건이에요.", "retryable": false } }
```

- `allowed`가 비어 있으면 Recovery는 `propose_recovery_action(decision="defer")`로 보류를 기록합니다(5-8 '허용 조치가 없음').
- 이 결과는 **조회 시점의 판단**입니다. 실제 실행 전에 정책 코드(`policy_gate`)가 A19에서 같은 규칙으로 다시 검사합니다(그 사이 상태가 바뀔 수 있음).
- 실패 코드: `INCIDENT_NOT_FOUND` / `INCIDENT_CLOSED` / `FORBIDDEN` / `TOOL_TIMEOUT`.


**JSON Schema와 출력 예시 — 최종 범위 도구 5개 **

성공·실패 출력은 6개와 같은 공통 형식이고, `data`는 감싸는 API(7-1절)의 응답 본문입니다. 외부 데이터가 '미지원·확인 불가'인 것은 **도구 실패가 아니라 `ok:true` + `data.status`** 로 옵니다(에이전트는 그대로 안내).

**⑦ `get_official_notices`** — A07

```json
{
  "name": "get_official_notices",
  "description": "축제의 공식 운영 공지와 교통 통제(무정차·우회·도로 통제)를 본다. 귀가 경로에 영향이 있는지 확인할 때 쓴다. 공지가 없으면 '확인할 수 있는 공지가 없다'고 답한다.",
  "parameters": {
    "type": "object",
    "properties": {
      "festival_id": { "type": "string", "description": "축제 ID" },
      "type": { "type": "string", "enum": ["operation", "traffic_control", "no_stop", "bus_detour", "road_closure"] }
    },
    "required": ["festival_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA7…", "is_mock": true,
  "data": { "festival_id": "fst_01JD7Z…", "status": "ok", "source": "seoul_topis", "observed_at": "…",
            "items": [ { "notice_id": "ntc_…", "type": "traffic_control", "title": "세종대로 일부 통제", "content": "…",
                         "effective_from": "2026-11-21T18:00:00+09:00", "effective_to": "2026-11-21T23:00:00+09:00", "control_version": "cv3" } ] } }
{ "ok": false, "request_id": "req_01JDA7…", "error": { "code": "FESTIVAL_NOT_FOUND", "message": "축제를 찾을 수 없어요.", "retryable": false } }
```

**⑧ `get_facilities`** — A08 (도구는 BFCL에 맞춰 **한 종류씩**, 래퍼가 `categories=[category]`로 보냄)

```json
{
  "name": "get_facilities",
  "description": "축제장 주변 시설(화장실·주차장·병원·응급실·지하철역·버스 정류장·자전거·택시 승강장·음식점·관광지) 위치를 한 종류씩 본다. 결과의 status가 unsupported·unverified면 그 이유를 그대로 안내한다.",
  "parameters": {
    "type": "object",
    "properties": {
      "festival_id": { "type": "string", "description": "축제 ID" },
      "category": { "type": "string", "enum": ["toilet","parking","locker","hospital","emergency","pharmacy","subway_station","bus_stop","bike_zone","taxi_stand","food","attraction"] }
    },
    "required": ["festival_id", "category"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA8…", "is_mock": true,
  "data": { "festival_id": "fst_01JD7Z…", "categories_status": { "parking": "ok" },
            "items": [ { "facility_id": "fac_…", "category": "parking", "name": "세종로 공영주차장", "lat": 37.5733, "lng": 126.9769,
                         "distance_m": 310, "address": "…", "source": "parking_standard", "ref_code": "…", "extra": { "type": "공영", "spaces": 1060 } } ] } }
{ "ok": true, "request_id": "req_01JDA8…", "is_mock": false,
  "data": { "festival_id": "fst_01JD7Z…", "categories_status": { "locker": "unsupported" }, "items": [] } }
```

**⑨ `get_crowd`** — A10 (서울만)

```json
{
  "name": "get_crowd",
  "description": "축제에 연결이 승인된 서울시 공식 구역의 주변 지역 혼잡을 본다. 집계 구역과 자료 시각을 밝히고 행사장 안 혼잡과 다를 수 있다고 안내한다. status가 unsupported면 이 축제 주변 지역의 혼잡 정보가 미지원이라고 답한다.",
  "parameters": {
    "type": "object",
    "properties": {
      "festival_id": { "type": "string", "description": "축제 ID" }
    },
    "required": ["festival_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDA9…", "is_mock": false,
  "data": { "festival_id": "fst_01JD7Z…", "status": "ok", "coverage": { "scope": "seoul_only", "region_code": "SEOUL", "supported": true },
            "areas": [ { "area_code": "POI009", "area_name": "광화문·덕수궁", "relation_type": "contains", "congest_level": "보통", "congest_color": "yellow",
                         "population_min": 48000, "population_max": 50000, "observed_at": "2026-11-16T15:40:00+09:00",
                         "forecast": [ { "time": "2026-11-16T17:00:00+09:00", "congest_level": "약간 붐빔", "population_min": 46000, "population_max": 48000 } ] } ] } }
{ "ok": true, "request_id": "req_01JDA9…", "is_mock": false,
  "data": { "festival_id": "fst_01JDBU…", "status": "unsupported", "coverage": { "scope": "seoul_only", "region_code": "BUSAN", "supported": false }, "areas": [] } }
```

**⑩ `save_favorite`** — A12 (로그인 세션이 있을 때만)

```json
{
  "name": "save_favorite",
  "description": "사용자가 원할 때 축제를 관심 목록에 저장한다. 로그인한 사용자 본인 것만 저장한다. 사용자 ID는 받지 않는다.",
  "parameters": {
    "type": "object",
    "properties": {
      "festival_id": { "type": "string", "description": "축제 ID" }
    },
    "required": ["festival_id"],
    "additionalProperties": false
  }
}
```

```json
{ "ok": true, "request_id": "req_01JDAA…", "is_mock": false, "data": { "festival_id": "fst_01JD7Z…", "saved_at": "2026-11-20T15:10:00+09:00" } }
{ "ok": false, "request_id": "req_01JDAA…", "error": { "code": "UNAUTHORIZED", "message": "로그인이 필요해요.", "retryable": false } }
```

- 래퍼는 A06 요청에 로그인 토큰이 있을 때만 이 도구를 에이전트에게 줍니다. 비로그인 대화에서는 도구 목록에 없어서 "로그인하면 저장할 수 있어요"로 답합니다.

**⑪ `predict_route_delay_risk`** — A17 (후속, 1차는 구현 전)

```json
{
  "name": "predict_route_delay_risk",
  "description": "(운영자 맥락) 귀가 조회 지연 위험을 추세로 예측한다. 아직 구현 전이면 NOT_IMPLEMENTED가 오고, 그때는 관측 추세만 설명하고 '예측 기능은 아직 없다'고 답한다.",
  "parameters": {
    "type": "object",
    "properties": {
      "window": { "type": "string", "enum": ["5m", "15m", "1h"], "default": "15m" },
      "horizon": { "type": "string", "enum": ["5m", "15m"], "default": "5m" }
    },
    "required": [],
    "additionalProperties": false
  }
}
```

```json
{ "ok": false, "request_id": "req_01JDAB…", "error": { "code": "NOT_IMPLEMENTED", "message": "예측 기능은 아직 없어요.", "retryable": false } }
```

13개 도구 모두 JSON Schema가 있습니다(6-2절 추가 후보 5개는 BFCL 밖이라 문항을 늘릴 때 같이 씀). 구현할 때는 FastAPI·Pydantic 모델에서 생성한 스키마와 이 문서를 대조합니다.

### 6-7. Tool 호출 흐름

**정상 귀가 요청 (BFCL NLD-04·11·16·18 형태)**

```
사용자 → POST /api/v1/assistant/query → 202 + run_id (작업 등록, 6-9) → 워커가 실행
  → Supervisor: 의도 = 귀가, 필요한 값 확인(festival_id, 목적지)
      ├─ 축제가 정해지지 않았으면 search_festivals → (첫 결과 선택 등)
      ├─ 장소를 모르면 get_festival
  → Route: request_return_route
      ├─ ready → 코드 검증(출처·시각·조건) + 경로 근거(혼잡 구역·교통 돌발) → Supervisor가 답변 통합
      └─ queued/processing → get_route_request_status(폴링 상한 있음) → ready/unavailable
  → 답변: 경로 + provider + queried_at + 확인 못 한 조건 + 미지원 데이터 표시
```

**길찾기 공급원 전환 (어댑터 안, 코드가 처리)**

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
- **지도 표시:** TMAP 경로를 카카오 지도 위에 그림(①). 카카오 공식 답변은 타사 지도 위 표시 허용, SK는 회신 없음. 경로 아래 **경로 정보: TMAP** 표기.
 - SK가 금지 회신하면 TMAP 경로를 소요 시간·환승·정류장 목록으로 표시합니다.
- **막차:** TMAP 응답의 `service`(1 운행 중 / 0 운행 종료)로 `service_running`을 정합니다. **구간마다 대표 노선 `service`와 대체 노선 `lane[].service` 중 하나라도 1이면 그 구간은 운행 중**으로 보고, 응답 `legs[].line`에 확인된 운행 중 노선 이름(lane 포함, 예: '수도권1호선(급행)')을 보여 줍니다. 모두 0인 구간이 있으면 `notices`에 '운행이 끝난 구간이 있어요'를 넣습니다. **그런 구간이 있는 후보는 유효 경로로 세지 않습니다** — 남은 후보가 없으면 `route_status=unavailable`, `ROUTE_NO_RESULT`('지금은 대중교통으로 갈 수 없어요'), `completed_valid_route=false`. 운행 정보가 없는 공급원(카카오)은 `service_running: null`로 두고 '막차 확인 불가'를 표시합니다.
 - **운행 종료 처리:** TMAP 후보가 모두 운행 종료로 제외되면 카카오로 전환하지 않고 HTTP 200, `unavailable`, `ROUTE_NO_RESULT`, `retryable=false`로 반환합니다. TMAP 운행 정보가 누락되거나 해석할 수 없으면 종료가 확인된 구간이 없는 후보를 유지하고 `service_running=null`로 표시합니다. 대체 노선 키·노선명의 원본 필드는 [SPEC P13](../../backend/Doc/route-providers/SPEC.md#p13-tmap-후보-판정)에 확인 필요로 기록했습니다.
- **TMAP 약관 — 받은 데이터는 저장 후 24시간 넘게 쓸 수 없음:** 경로 캐시는 서버 메모리에서만 60초 유지합니다(`valid_until`). DB 모드는 조회 후 기본 23시간 이상 된 TMAP 요약을 시간당 작업으로 정리해 정상 실행 시 본문을 최대 24시간 보관합니다. 7일 논리 백업(SK 회신 없이 적용하는 확정 기준)은 013까지 적용 후 [백업 실행기](db/backup_long_term.sh)로 만들며, 공급원 원본·후보 상세를 담을 수 있는 `route_results`의 데이터 전체를 제외합니다. `route_requests`에는 결과의 조회 시각·공급원·본문 삭제 시각과 요청 상태·오류 코드를 보존합니다([기록 17-3](API_구현_검증기록.md#17-3-저장캐시-규칙--실제-코드-강사-1120-api-2)절, DB 설계서 7-0 ④). Redis 장소 라벨 연결은 후속 작업입니다. 원본 JSON 근거 파일도 24시간 안에 필드만 확인하고 지우며, 제출용 근거는 합성 예시와 메타데이터로 남깁니다.
- **카카오맵 결과는 A04의 동기 응답(3초 안)에서만 전달합니다.** 카카오 개발자 답변상 임시 캐싱도 허용되지 않아, 이미 202로 접수한 요청의 결과를 나중에 A05로 돌려줄 수 없습니다. 그래서 202 이후 1차(TMAP)가 실패하면 A05는 `route_status=unavailable`, 오류 `ROUTE_SECONDARY_SYNC_ONLY`('다시 조회해 주세요')로 답하고 사용자가 새로 요청하면 2차를 동기로 부릅니다. **이 문제가 풀리기 전에는 2차 공급원을 쓴 비동기 복구를 '복구 완료'로 세지 않습니다**.
- **카카오맵 응답은 저장·캐시하지 않습니다** — **카카오 공식 답변(데브톡 6/29): 다른 회사 지도 위 표시는 가능, 단 실시간 호출만·저장 불가.** 011 DB 모드에서는 `route_requests`의 상태와 오류 코드만 기록하고 `route_results` 행은 만들지 않습니다(DB 설계서 6-1). 카카오 장소 검색 결과(이름·좌표)도 같은 규칙 — 목적지 라벨 `route:label`에는 **사용자가 입력한 문자열만** 넣습니다.
- TMAP 1차는 정류장 ID·좌표와 출발·도착 도보 구간, 출발 시각(`searchDttm`)을 제공합니다. Free 하루 10건(오류 포함)을 유지하고, 한도 도달 시 카카오 2차(하루 1,000건)를 사용합니다. 부하 시험은 모의 응답을 사용합니다.


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

### 6-8. 도구 호출 정의 (입력 스키마·실행 조건)

| 도구 | 입력 스키마 | 실행 조건 / 호출하지 않는 경우 |
|---|---|---|
| `search_festivals` | `region?: RegionCode="ALL", date_from?: date, date_to?: date, q?: str, status?: enum, page_size?: int≤20` | 날짜가 "이번 주말"처럼 상대 표현이면 **대화의 기준 날짜**로 바꾼 뒤 호출. 기준 날짜가 없으면 묻기 |
| `get_festival` | `festival_id: str` | 대화에 선택된 축제가 있을 때. "그 축제"를 무엇으로 볼지 모르면 묻기 (BFCL NLD-20) |
| `request_return_route` | `festival_id: str, destination: {query \| lat,lng}, travel_mode?: enum="transit", route_preference?: enum="fastest", user_constraints?: obj` | 축제·목적지 모두 확정 시. 목적지 없으면 묻기 (BFCL NLD-19) |
| `get_route_request_status` | `route_request_id: str` | 이전 요청 ID가 대화 맥락에 있을 때. 폴링은 최대 5회·간격 2초(초기값) |
| `get_official_notices` | `festival_id: str, type?: enum[operation, traffic_control, no_stop, bus_detour, road_closure]` | 공지 공급원 연동 후. 없으면 "확인할 수 있는 공지 자료가 없음" 안내 |
| `get_facilities` | `festival_id: str, category: FacilityCategory` | 시설 공급원 연동 후 (BFCL NLD-08). 서비스 API(A08)는 여러 종류를 한 번에 받지만, 도구는 BFCL에 맞춰 한 종류씩 |
| `get_crowd` | `festival_id: str` | 서울 지원 장소 매핑이 있을 때만 값. 없으면 `unsupported` 결과를 그대로 안내 (BFCL NLD-07·28) |
| `save_favorite` | `festival_id: str` | **로그인 세션이 있을 때만**. 사용자 ID는 입력으로 받지 않고 세션에서 가져옴 |
| `get_incident` | `incident_id: str` | 운영자 맥락 + 사건 ID 있을 때 |
| `get_route_metrics` | `incident_id?: str, simulation_id?: str, window?: enum[10s,1m,5m,15m]="5m"` | 진단 시작 시 필수 |
| `predict_route_delay_risk` | `window: str="15m", horizon: str="5m"` | 후속 구현. 구현 전에는 관측 추세만 설명하고 "예측 기능 미구현"으로 답 (BFCL NLD-03) |
| `list_allowed_actions` | `incident_id: str` | Recovery 판단 전 필수 |
| `propose_recovery_action` | `incident_id: str, decision: enum[select,reject,defer,rollback], action?: str, reasons: list[str], rejected_actions?: list, stop_condition?: obj, evidence_refs: list[str]≥1` | `list_allowed_actions` 결과 안의 action만. 근거 ID 없으면 호출 불가 |

**호출하지 않는 것이 정답인 요청** — 도구가 없거나 정책상 막힘 (BFCL 기준): 정보 부족 되묻기(NLD-19·20), 접근성 보장 확인(NLD-21), 지역 혼잡만으로 가장 한산한 경로 판정(NLD-22), 대기열 접수를 성공으로 집계(NLD-17), 일반 사용자의 장애 주입 요청(NLD-27), 행사장 내부 실시간 인원(NLD-28), 오래된 경로를 안전하다고 표시(NLD-29), 문서 속 지시로 정책 끄기(NLD-30, 프롬프트 인젝션).

BFCL 30문항의 채점에는 API 설계서 최신판을 적용합니다([기록 4-7](API_구현_검증기록.md#4-7-bfcl-30문항과의-대조-강사-일일-피드백-5)절).

### 6-9. 챗봇 질문: `POST /api/v1/assistant/query` (A06) — 비동기 작업

**왜 비동기인가:** 멀티에이전트를 HTTP 요청 안에서 기다리지 않고, API는 작업만 등록하고 202 + 작업 ID를 바로 돌려줍니다(타임아웃·새로고침 유실·서버 막힘 방지, 수업 자료 「API 서버 + 백그라운드 워커로 멀티에이전트 운영하기」). 그래서 **접수(A06) → 상태·결과 조회(A06-1) → 진행 이벤트(A06-2)** 세 개로 나눴습니다. 워커 구현 방식(Celery 또는 직접 만든 worker)과 관계없이 이 API 계약은 같습니다.

**동작 규칙** — 기본 모의 응답과 `ASSISTANT_PROVIDER=db`의 202 접수·상태 조회·SSE를 연결했습니다. PostgreSQL 워커는 30초 시도 제한과 5초 뒤 1회 재시도, 전체 65초 제한, 70초 초과 작업 정리를 적용합니다. 익명 대화 이어가기에는 `X-Run-Access-Token`이 필요하고, 익명 재제출은 최초 세션 쿠키 또는 그 작업의 토큰으로 확인합니다. `context.route_request_id`를 보내면 `X-Route-Access-Token`도 필요합니다. SSE는 진행 신호를 중계하며 구독 중 성공한 작업의 저장 답변을 `token`으로 전달합니다. 현재 Festival Agent 실행 진입점이 없어 모의 답변을 사용합니다. DB 모드의 새 귀가 질문은 귀가 화면으로 안내하며, 검증된 기존 귀가 요청을 전달할 수 있습니다.

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 사용자의 자연어 질문(축제 찾기·귀가 안내)을 받아 Supervisor → Festival/Route 에이전트 실행을 **작업으로 등록** (FR-C01~C09). 호출 주체: 챗봇 화면 |
| 2 | 요청 헤더 | `Content-Type: application/json`(필수) · `X-Request-ID`(선택) · `Authorization: Bearer`(로그인) · `X-Run-Access-Token`(익명 대화 이어가기) · `X-Route-Access-Token`(경로 문맥 제공 시) |
| 3 | 경로·쿼리 | 없음 |
| 4 | 요청 본문 | 아래 필드 명세 |
| 5 | 검증·권한 | 형식 422 → 요청 수 제한 429 → 같은 `request_id`면 처음 만든 `run_id`, 본문이 다르면 409 `IDEMPOTENCY_CONFLICT` → `conversation_id`가 있으면 그 대화의 주인인지(로그인: JWT `sub`, 비로그인: `X-Run-Access-Token`) 확인, 아니면 403. **질문 안의 "나는 관리자"는 권한이 아님**(2-4절) — 운영 도구(`get_incident` 등)는 이 API로 실행된 에이전트에게 주지 않음 |
| 6 | 정상 응답 | **202** `{run_id, run_status:"queued", status_url, events_url, run_access_token, retry_after_s}` — 답변은 아직 없음 |
| 7 | 오류 응답 | 401 `UNAUTHORIZED`(무효 Access 또는 만료된 경로 조회 토큰) / 403 `FORBIDDEN`(남의 대화) / 409 `IDEMPOTENCY_CONFLICT` / 422 `VALIDATION_ERROR` / 429 `RATE_LIMITED` / 503 `AI_AGENT_FAILED`(작업 등록 자체 실패 — 큐·DB 장애. 이때도 A02~A05는 독립 동작) |
| 8 | 실행 규칙 | API는 **작업 기록(DB) + 큐 등록만** 하고 바로 응답(수 ms~수십 ms). 큐에는 `run_id`만 넣고 질문 원문은 넣지 않음(워커가 DB에서 읽음). 워커는 작업을 **선점(claim)** 한 뒤 실행(같은 작업 두 번 실행 방지). 실행 제한은 **시도 1회당 30초**(넘으면 그 시도 실패), 재시도 1회(5초 뒤)를 포함해 **최대 65초** — 넘으면 `failed`·`AI_AGENT_FAILED`. LLM 429·5xx·시간 초과만 **같은 `run_id`로 1회** 재시도(`retrying`, 5초 뒤), 나머지는 재시도 없음. 워커가 실행 중에 죽어 `running`이 70초를 넘으면 정리 작업이 `failed`로 바꿈. 숫자는 모두 8-4절 기준표 |

**요청 필드 명세**

| 필드 | 타입 | 필수 | 빈값 | 제약 | 설명 |
|---|---|---|---|---|---|
| `request_id` | string | 예 | 불가 | 8~64자, UUID 권장 | 멱등 키(같은 질문 두 번 전송 방지) |
| `message` | string | 예 | 불가 | 1~500자 | 사용자 질문 |
| `conversation_id` | string | 아니요 | null | `^cv_[0-9A-Za-z]{6,26}$` | 이어지는 대화면 이전 `conversation_id`. 없으면 서버가 새로 만듦 |
| `context.festival_id` | string | 아니요 | null | `^fst_…` | 화면에서 이미 고른 축제 |
| `context.route_request_id` | string | 아니요 | null | `^rr_…` | 화면에서 이미 요청한 경로(본인 것만, 토큰 확인) |
| `reference_date` | string(date) | 아니요 | 서버 KST 오늘 | `YYYY-MM-DD` | "이번 주말" 같은 상대 날짜의 기준일(BFCL 평가에서는 고정값) |

**작업 상태(`run_status`)** — 수업 자료의 작업 상태 머신을 따릅니다. 경로 상태(`route_status`)와 이름이 섞이지 않게 따로 둡니다.

| 값 | 뜻 | 다음 |
|---|---|---|
| `queued` | 접수됨, 워커 대기 | `running` |
| `running` | 워커가 선점해 실행 중 | `succeeded`·`retrying`·`failed` |
| `retrying` | LLM 일시 오류로 잠시 뒤 다시 실행(1회) | `running` |
| `succeeded` | 답변 완성 | 끝 |
| `failed` | 재시도 소진·시간 초과·복구 불가 오류 | 끝 (같은 질문은 **새 `request_id`로 새 작업**) |

**재시도와 새 작업의 차이:** 재시도는 같은 `run_id` 안에서 서버가 하는 것이고(사용자에게 새 ID 없음), 새 작업은 사용자가 다시 질문해 새 `request_id` → 새 `run_id`가 생기는 것입니다. 같은 `request_id`로 다시 보내면 새 작업이 아니라 **기존 작업 상태**를 돌려줍니다.

**A06 POST 접수 응답 (202)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `run_id` | 응답 | string | 예 | 등록한 챗봇 작업 ID |
| `conversation_id` | 응답 | string | 예 | 대화 ID, 새 대화면 서버가 생성 |
| `run_status` | 응답 | string | 예 | 현재 모의 접수 응답은 `queued`, 작업 상태 값은 위 표 |
| `status_url` | 응답 | string | 예 | A06-1 상태 조회 경로 |
| `events_url` | 응답 | string | 예 | A06-2 이벤트 구독 경로 |
| `run_access_token` | 응답 | string | 예 | 비로그인 작업 조회에 쓰는 토큰 |
| `retry_after_s` | 응답 | int | 예 | 다시 조회하기 전 대기 시간(초), 모의 응답 1 |
| `is_mock` | 응답 | boolean | 모의 응답 예 | 현재 모의 응답은 `true` |

**정상 응답 예시 (202)**

```json
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "queued",
  "status_url": "/api/v1/assistant/runs/run_01JDB0…", "events_url": "/api/v1/assistant/runs/run_01JDB0…/events",
  "run_access_token": "rat_…(10분)", "retry_after_s": 1 }
```

#### A06-1. `GET /api/v1/assistant/runs/{run_id}` — 상태·결과 조회

- 헤더: 로그인이면 `Authorization`, 비로그인이면 `X-Run-Access-Token`(202에서 받은 것). 토큰 없음·만료 401, 남의 작업 403, 없는 ID 404 `RUN_NOT_FOUND`.
- **200** — 작업이 실패해도 조회는 성공이므로 200, 실패는 `run_status`·`error`로 알림(A05와 같은 규칙). 새로고침해도 `run_id`만 있으면 다시 볼 수 있습니다.

| 필드 | 타입 | 빈값 | 언제 | 설명 |
|---|---|---|---|---|
| `run_id`·`conversation_id`·`run_status` | string | 불가 | 항상 | |
| `answer` | string | null | `succeeded` | 최종 답변 |
| `used_tools[]` | array | 빈 배열 | 항상 | `{tool, ok, error_code}` — 부른 도구와 결과 코드(인자 원문은 안 보여 줌) |
| `evidence[]` | array | 빈 배열 | `succeeded` | `{type, ref, provider, queried_at}` 예: `{type:"route", ref:"rr_…", provider:"tmap"}` |
| `run_kind` | string | 불가 | 항상 | `chat`(A06) · `visit_course`(A51) |
| `result` | object | null | `visit_course`이고 `succeeded` | A51 코스 결과(7-3, `assistant_runs.result`) |
| `route_request_id` | string | null | 경로를 요청했으면 | 화면은 경로 내용을 **A05로** 받아 지도에 그림 |
| `route_access_token` | string | null | 경로를 요청했고 아직 유효(10분) | A05의 `X-Route-Access-Token`으로 씀. 이 작업을 볼 권한(로그인 본인 또는 `X-Run-Access-Token`)이 있을 때만 줌. 만료 뒤에는 null → 화면이 귀가 조회를 새로 요청 |
| `error` | object | null | `failed` | `{code, message, retryable}` — `AI_AGENT_FAILED`·`TOOL_TIMEOUT` 등 |
| `queued_at`·`started_at`·`ended_at` | string | null 가능 | | |
| `is_mock` | boolean | 불가 | 항상 | 모의 LLM·모의 도구면 true |

- **경로 내용 보존 규칙(6-7절, 04 문서 7-0)과의 관계:** `answer`는 30일 저장되므로 **어떤 공급원이든(TMAP 24시간 제한·카카오 저장 금지)** 경로 구간·정류장 내용을 `answer`에 쓰지 않습니다. **에이전트 입출력 기록 파일(`agent_runs.input_ref`·`output_ref`, 30일)도 같음** — Route 도구 결과는 `route_request_id`·`provider`·`route_status`만 남기고 `route_candidates`는 넣지 않습니다(04 문서 7-0 ②). `answer`는 "경로를 찾았어요 — 귀가 화면에서 확인하세요" 수준의 요약으로 두고, 경로는 `route_request_id`로 A05에서 받습니다. 같은 이유로 Route 도구 결과를 대화 상태(체크포인트, 7일)에 넣을 때도 `route_candidates`는 빼고 `route_request_id`·`provider`·`route_status`만 넣습니다.

**A06-1 모의 응답 3가지 (화면 연결용: 진행 중·완료·실패)** — `is_mock: true`

```json
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "running", "answer": null, "used_tools": [ { "tool": "search_festivals", "ok": true, "error_code": null } ], "evidence": [], "route_request_id": null, "error": null, "queued_at": "…", "started_at": "…", "ended_at": null, "is_mock": true }
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "succeeded", "answer": "광화문에서 서울역까지 경로를 찾았어요. 귀가 화면에서 확인하세요.", "used_tools": [ { "tool": "get_festival", "ok": true, "error_code": null }, { "tool": "request_return_route", "ok": true, "error_code": null } ], "evidence": [ { "type": "route", "ref": "rr_01JD8Q3K2M", "provider": "mock_adapter", "queried_at": "…" } ], "route_request_id": "rr_01JD8Q3K2M", "error": null, "queued_at": "…", "started_at": "…", "ended_at": "…", "is_mock": true }
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "failed", "answer": null, "used_tools": [ { "tool": "request_return_route", "ok": false, "error_code": "TOOL_TIMEOUT" } ], "evidence": [], "route_request_id": null, "error": { "code": "AI_AGENT_FAILED", "message": "답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요.", "retryable": true }, "queued_at": "…", "started_at": "…", "ended_at": "…", "is_mock": true }
```

- 화면은 `running`을 성공처럼 보여 주지 않고, `failed`면 `error.message`와 "다시 묻기"(새 `request_id` = 새 작업)를 보여 줍니다. 같은 `run_id`를 다시 **조회**하는 것과 실패한 일을 **새로 실행**하는 것은 다릅니다(6-9 '재시도와 새 작업의 차이').
- 남의 작업 조회는 403입니다. '없거나 조회가 허용되지 않는 작업'을 404로 묶는 방식도 있지만, `run_id`가 추측하기 어려운 ULID이고 토큰 만료 안내(401)와 구분하려고 403을 유지합니다.

#### A06-2. `GET /api/v1/assistant/runs/{run_id}/events` — 진행 이벤트(SSE)

**동작 규칙** — 로그인 스트림은 Access JWT 만료 시각을 따릅니다. 진행·답변·종료 이벤트 전 WebSocket과 같은 세션 검사로 로그아웃 또는 비활성 여부를 확인하고, 인증이 무효화됐으면 연결을 닫습니다.

- `text/event-stream`. 워커가 노드가 끝날 때마다 발행한 이벤트를 API가 중계합니다(에이전트 사고 과정 가시화).
- 이벤트 4종: `{"type":"step","node":"supervisor"}` · `{"type":"token","text":"…"}`(선택) · `{"type":"done"}` · `{"type":"failed","code":"AI_AGENT_FAILED"}`. `done`·`failed` 뒤 연결을 닫습니다.
- 이벤트는 저장되지 않으므로(구독 전 이벤트 없음) 화면은 **먼저 A06-1로 현재 상태를 그린 뒤** 구독합니다. 브라우저 `EventSource`는 헤더를 못 붙이므로 fetch 기반 SSE로 `X-Run-Access-Token`을 보냅니다.
- 구현 순서: ① 폴링(A06-1, 2초)으로 먼저 완성 → ② SSE로 교체.

**A06-2 SSE 이벤트별 데이터 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `type` | 응답 | string | `step` 예 | 값은 `step` |
| `node` | 응답 | string | `step` 예 | 완료한 에이전트 노드 이름(예: `supervisor`) |
| `type` | 응답 | string | `token` 예 | 값은 `token` |
| `text` | 응답 | string | `token` 예 | 전달할 텍스트 조각, `token` 이벤트 사용 자체는 선택 |
| `type` | 응답 | string | `done` 예 | 값은 `done`, 추가 필드 없음 |
| `type` | 응답 | string | `failed` 예 | 값은 `failed` |
| `code` | 응답 | string | `failed` 예 | 작업 실패 코드(예: `AI_AGENT_FAILED`) |

**DB:** 작업 상태·결과의 기준은 DB입니다. `agent_runs`(에이전트 1회 실행 기록)와 별도로 **작업 1건 = 1행**인 `assistant_runs`(`run_id`·`request_id` UNIQUE·`conversation_id`·`user_id`/`run_token_hash`·`run_status`·`attempt`·`message`·`answer`·`error_code`·`route_request_id`·시각)를 둡니다(04 문서 마이그레이션 002: 같은 `request_id` 거부, 두 워커 선점 시 1명만, 70초 넘은 `running` 정리, 본인 작업만 조회).

---

## 7. 추가 기능 API

> A01 상태 확인은 3-0절, 인증 A32~A35는 2-5절, 핵심 흐름(A02·A03·A04·A05·A25)은 4절, 장애 대응(A14~A22·A31)은 5절, 챗봇 A06은 6-9절에 있고 나머지는 모두 이 절에 있습니다. 7-1은 외부 정보·관리 API, 7-2는 추천·친구·동행·채팅·알림·마이페이지, 7-3은 방문 코스·공지·축제 관리입니다.


### 7-1. 외부 정보·관리 API 상세 명세

1차 필수가 아닌 API도 **구현하기로 정한 범위 전체**를 여기서 정합니다(수업 가이드 "구현하기로 확정한 API 전체의 명세"). 원본 필드 이름은 `Docs/Step 2/evidence/`(README·원본) 기준입니다.

#### 7-1-0. 외부 데이터 조회 API 공통 규칙 (A07~A10, A26·A28~A30)

같은 모양을 반복하지 않도록 공통 8칸을 한 번만 적습니다. API별 표에는 **다른 점만** 적습니다.

| # | 칸 | 공통 명세 |
|---|---|---|
| 1 | 호출 목적 | 축제 화면·지도·에이전트 도구가 축제 주변 정보를 봄 |
| 2 | 요청 헤더 | `X-Request-ID`(선택). 인증 없음(공개) |
| 3 | 경로·쿼리 | `festival_id`: 필수, `^fst_[0-9A-Za-z]{6,26}$`. 쿼리는 API별 표 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 형식 422 → 축제 없음 404 `FESTIVAL_NOT_FOUND` → 축제 좌표가 필요한 API인데 없으면 **200 + `status:"unavailable"`, `FESTIVAL_LOCATION_UNKNOWN`**(화면 전체를 오류로 만들지 않음. 단 A10은 `status:"unsupported"`·`unsupported_reason:"missing_coordinates"`, 경로 API A04·A25는 400) → 그 지역에 공급원이 없으면 **200 + `status:"unsupported"`** (2-2·2-3절) |
| 6 | 정상 응답 | **200** `{festival_id, status, coverage, source, observed_at, is_mock, items[] 또는 data}`. `status`: `ok`·`stale`·`unavailable`·`unsupported`·`unverified` (2-3절) |
| 7 | 오류 응답 | 404 `FESTIVAL_NOT_FOUND` · 422 `VALIDATION_ERROR` · 429 `RATE_LIMITED`. **외부 공급원 오류는 HTTP 오류로 돌려주지 않고** 200 + `status:"unavailable"` + `error{code:SOURCE_HTTP_ERROR·SOURCE_RESULT_ERROR, retryable}` |
| 8 | 실행 규칙 | 실시간 값은 Redis `ext:*` 캐시 먼저(8-4 ④), 없으면 공급원 1회 호출(시간 제한 3초, 일시 오류 1회 재시도 — 8-4). **HTTP 200이라도 본문 결과 코드를 확인**(서울 `RESULT.CODE`, 경찰청 `resultCode`, TAGO `resultCode` 99, 지하철 `status`). XML 공급원(경찰청·응급실·TOPIS)은 어댑터가 JSON으로 바꿈. 관측 시각이 갱신 주기 ×2보다 오래면 `stale`. 정적 데이터(시설 위치)는 수집된 DB에서만 답함 |

#### A07. 공식 공지·교통 통제 `GET /api/v1/festivals/{festival_id}/notices`

| 항목 | 명세 |
|---|---|
| 쿼리 | `type`: 선택, `operation`·`traffic_control`·`no_stop`·`bus_detour`·`road_closure` / `active_only`: bool, 기본 true(지금 효력 있는 것만) |
| 출처 | 운영자가 등록·승인한 공지 + 서울 TOPIS 통제(10번, 서울만) |
| 동작 규칙 | 기본 모의는 예시 공지와 메모리 등록 공지를 함께 조회합니다. `AUTH_PROVIDER=db` 또는 `NOTICES_PROVIDER=real`은 DB에서 승인된 해당 축제·공통 공지를 조회합니다. 시작 시각은 포함하고 종료 시각은 제외합니다. |
| 규칙 | `approval_status='approved'`만 보여 줌(미승인은 경로 차단에도 안 씀). 축제 공지가 없어도 `status:"ok"`, `items:[]` — "확인할 수 있는 공지 자료가 없어요" |

**A07 쿼리 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `type` | query | string | 아니요 | `operation`·`traffic_control`·`no_stop`·`bus_detour`·`road_closure`, 생략하면 유형 필터 없음 |
| `active_only` | query | boolean | 아니요 | 기본 `true`, 지금 효력 있는 공지로 제한 |

| 응답 `items[]` | 타입 | 빈값 | 출처 | DB `official_notices` |
|---|---|---|---|---|
| `notice_id`·`type`·`title` | string | 불가 | 운영자·TOPIS(`acc_type`→`type`) | 같은 이름 |
| `content` | string | null | 운영자·TOPIS `acc_info` | `content` |
| `effective_from`·`effective_to` | string | null | TOPIS `occr_date`+`occr_time` / `exp_clr_date`+`exp_clr_time`(자릿수 혼재 → 어댑터가 정규화) | 같은 이름 |
| `source`·`source_url`·`published_at` | string | null 가능 | | `source_id`·`source_url`·`published_at` |
| `control_version` | string | null | 경로 캐시 무효화 기준 | `control_version` |

#### A08. 지도 주변 시설 `GET /api/v1/festivals/{festival_id}/facilities`

| 항목 | 명세 |
|---|---|
| 쿼리 | `categories`: 선택, 쉼표 구분, 기본 1차 10종 전부(`toilet,parking,hospital,emergency,subway_station,bus_stop,bike_zone,taxi_stand,food,attraction`). `locker`·`pharmacy`는 허용값이지만 항상 `unsupported` / `radius_m`: 100~3000, 기본 1000 / `limit_per_category`: 1~50, 기본 20 |
| 규칙 | 축제 좌표 필요. 거리순 정렬. **카테고리마다 상태를 따로** `categories_status`로 줌(한 공급원이 실패해도 나머지는 보여 줌). 카카오 로컬(`food`·`attraction`)은 **저장 조건 미확인이라 DB에 넣지 않고 요청 때 중계**만 함([기록 11](API_구현_검증기록.md#11-미확인-항목확인-계획)절) |

**A08 쿼리 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `categories` | query | string | 아니요 | 쉼표 구분, 기본 `toilet,parking,hospital,emergency,subway_station,bus_stop,bike_zone,taxi_stand,food,attraction`. `locker`·`pharmacy`는 `unsupported` |
| `radius_m` | query | int | 아니요 | 100~3000m, 기본 1000 |
| `limit_per_category` | query | int | 아니요 | 분류당 1~50건, 기본 20 |

| 카테고리 | 공급원 | 위치 필드 | 추가로 보여 주는 값 | 상태 |
|---|---|---|---|---|
| `toilet` | 행정안전부 공중화장실 15155058 | 응답 위경도 필드 이름 **확인 필요**(주소 `LCTN_ROAD_NM_ADDR`는 확인) | 개방 시간 `OPN_HR`, 관리 기관 `MNG_INST_NM` | 위경도 확인 전 `unverified` |
| `parking` | 전국주차장정보표준데이터 | `latitude`·`longitude`(비어 있으면 제외) | 공영/민영 `prkplceSe`, 면수 `prkcmprt`, 관리번호 `prkplceNo` | ok |
| `hospital`·`emergency` | 국립중앙의료원 `getEgytLcinfoInqire`(XML) | `latitude`·`longitude` | 기관 `dutyName`, 구분 `dutyDivName`, 기관 ID `hpid` | ok |
| `subway_station` | 카카오 로컬 `SW8`(중계) | `x`·`y` | 역 이름 | 카카오 저장 조건 확인 전 중계만 |
| `bus_stop` | 서울 밖 TAGO 정류소(`nodeid`·`citycode`) / 서울은 **서울시 버스정류소 위치정보 파일(OA-15067)을 DB에 적재**(1순위 — 좌표 WGS84 경위도라 변환 없음, `NODE_ID` 9자리 → `source_item_id`, `ARS_ID` 5자리(앞 0 유지, 문자로 저장), 공공누리 1유형), 실시간 보완은 서울 정류소정보조회 `getStaionsByPosList`(1,000건/일, 2순위) | TAGO `gpslati`·`gpslong` | 정류소 ID(A26 연결용) | 서울 `unverified` |
| `bike_zone` | 행안부 전국 공영자전거 대여소 15126639 | `lat`·`lot` | 대여소 이름 | ok (실시간 대수는 제외 — 3-1) |
| `taxi_stand` | 전국택시승강장표준데이터 15139230 | **위경도 없음** → 주소 `lctnRoadNmAddr`를 좌표로 바꿔 적재 | 정차면수 `taxExclsScplcCnt`, 상세 위치 `dtlPstn` | 변환 방법 확정 전 `unverified`([기록 11](API_구현_검증기록.md#11-미확인-항목확인-계획)절) |
| `food`·`attraction` | 카카오 로컬 `FD6`·`AT4`(문서 기준)(중계) | `x`·`y` | 장소 이름·분류 | 중계만 |

| 응답 필드 | 타입 | 설명 | DB |
|---|---|---|---|
| `categories_status` | object | 카테고리별 `ok`·`unverified`·`unsupported`·`unavailable` | — |
| `items[]` | array | `{facility_id, category, name, lat, lng, distance_m, address, source, ref_code, extra}` | `facilities`(카카오 중계분은 DB 없음, `facility_id`=`kakao:<id>`) |

#### A09. 날씨 `GET /api/v1/festivals/{festival_id}/weather`

| 항목 | 명세 |
|---|---|
| 쿼리 | 없음 |
| 규칙 | 축제 좌표 → **기상청 격자(nx, ny)로 변환**(변환식은 기상청 참고문서). `base_time`은 1시간 전 정시. 캐시 10분 |
| 동작 규칙 | 기본 모의. `WEATHER_PROVIDER=real`은 초단기실황·단기예보를 조회합니다. |

| 응답 필드 | 타입 | 원본(기상청) | 설명 |
|---|---|---|---|
| `observed_at` | string | `baseDate`+`baseTime` | 발표 시각 |
| `temperature_c` | number | `T1H` | 기온 |
| `precipitation_mm` | number | `RN1` | 1시간 강수량 |
| `precipitation_type` | string | `PTY` 0~7 | `none`·`rain`·`rain_snow`·`snow`·`drizzle`·`drizzle_snow`·`snow_flurry`(코드 0·1·2·3·5·6·7) |
| `grid` | object | `nx`·`ny` | 변환 결과 |
| `forecast` | object | `baseDate`·`baseTime`, `fcstDate`·`fcstTime`, `TMP`·`PCP`·`PTY` | 모의 `{status:"unverified"}`. 실제 성공은 `status`(`ok`·`stale`), 발표 시각 `issued_at`, `items[]`(`forecast_at`, `temperature_c`, `precipitation_mm`, `precipitation_type`). 예보 조회 실패는 `{status:"unavailable",error}`. |

#### A10. 혼잡 구역 `GET /api/v1/festivals/{festival_id}/crowd` (서울만)

| 항목 | 현재 동작 |
|---|---|
| 쿼리 | 없음 |
| 실제/모의 | 기본 `mock`은 저장된 모의 자료와 `X-Mock`을 사용합니다. `CROWD_PROVIDER=real`은 `is_mock:false`를 반환하며 승인된 매핑만 서울시 `citydata_ppltn`에 요청합니다. |
| 반경 | 승인된 공식 구역 경계까지 최단거리를 잽니다. 구역 안과 경계 위는 0m입니다. 1km 이내에서 가까운 순으로 최대 3곳을 선택합니다. 거리가 같으면(좌표가 여러 구역 안에 있으면) 경계에서 더 깊이 들어간 구역을 먼저 두고, 그래도 같으면 구역 코드순입니다. 첫 번째 구역이 대표 혼잡입니다. |
| 미지원 | 서울 밖·좌표 없음·승인 매핑 없음·반경 내 승인 구역 없음은 각각 `outside_seoul`·`missing_coordinates`·`no_approved_mapping`·`no_nearby_areas`를 `unsupported_reason`에 넣고 `status:"unsupported"`를 반환합니다. |
| 구역 실패 | 일부가 실패하면 `nearby_areas`에 실패 상태와 오류를 남기고 관측값이 있는 구역을 제공합니다. 모두 실패하면 200 `unavailable`입니다. 오류가 같으면 해당 오류를, 다르면 `SOURCE_RESULT_ERROR`를 반환합니다. HTTP 200 본문 오류, 요청 구역 불일치, 형식 오류, 공급원 대체 평균도 조회 실패로 처리합니다. Agent 종료 상태는 6-5절을 따릅니다. |
| 호출 제한 | 기본값은 구역별 3초 제한, 60초 메모리 캐시, KST 일일 예산 `CROWD_SEOUL_DAILY_LIMIT` 1,000회, 기준 시각에서 45분 초과 시 `stale`입니다. 같은 구역의 요청은 병합하고 실패는 캐시하지 않습니다. 운영값은 확인이 필요합니다. |

기존 `areas[0]`과 최상위 `observed_at`은 조회에 성공한 가장 가까운 구역 값입니다. 성공 구역이 없으면 `areas:[]`, `observed_at:null`입니다. 최상위 `status`는 지원 여부 및 전체 조회 결과를 반영하고, 성공 시에는 `areas[0]`의 `ok` 또는 `stale`을 따릅니다.

| 실제 모드 추가 필드 | 타입 | 설명 |
|---|---|---|
| `nearby_areas` | array | 거리순으로 선택한 최대 3곳. 각 항목은 `area_code`, `area_name`, `distance_m`(m, 소수점 한 자리), `status`(`ok`·`stale`·`unavailable`), `data`(아래 기존 구역 모양 또는 `null`), `is_estimate`, `error`를 가집니다. 실패 시 `data`·`is_estimate`는 `null`입니다. |
| `is_estimate` | bool 또는 null | `areas[0]` 및 각 구역에서 관측값을 제공하면 `false`, 제공할 자료가 없으면 `null`입니다. |
| `unsupported_reason` | string 또는 null | 실제 모드 미지원 사유입니다. |
| `source_url` | string | 서울특별시의 OA-21778 데이터셋 주소입니다. |

| 기존 `areas[]` 및 `nearby_areas[].data` | 타입 | 원본 또는 변환 |
|---|---|---|
| `area_code`·`area_name` | string | 서울시 공식 구역 코드·이름 |
| `relation_type` | string | 거리 0m는 `contains`, 0m 초과는 `adjacent` |
| `congest_level`·`congest_color` | string | `AREA_CONGEST_LVL`의 여유·보통·약간 붐빔·붐빔을 각각 `green`·`yellow`·`orange`·`red`로 표시 |
| `congest_message` | string | `AREA_CONGEST_MSG` |
| `population_min`·`population_max` | int | `AREA_PPLTN_MIN`·`AREA_PPLTN_MAX` |
| `observed_at` | string | `PPLTN_TIME`을 KST ISO 8601로 변환한 기준 시각 |
| `forecast` | array | 실제 모드는 빈 배열. 모의 응답의 기존 예보는 유지합니다. |

**서울 혼잡 시연 대상**은 서울빛초롱축제(`fst_01M835B57450M888RBNEFVRWWA`)입니다. 주변 구역은 광화문·덕수궁 POI009, 시의회 앞 POI130, 명동 관광특구 POI003입니다. 숭례문 파수의식은 TourAPI EV03 행사로 범위에서 제외합니다.

`notices`는 관측값을 **주변 지역 혼잡(서울시 실시간 도시데이터)**으로 안내하고 구역 이름·축제에서의 거리·기준 시각·출처와 **“행사장 안 혼잡과 다를 수 있어요”**를 제공합니다. 공급원의 4주 대체 평균은 응답과 캐시에서 제외합니다. 성별·연령 비율도 응답과 저장에서 제외합니다. 실연동 승인 절차는 [서울 혼잡 매핑 명세](../../backend/Doc/seoul-crowd/SPEC.md)에 있습니다.

#### A11~A13. 관심 축제 (로그인 필요)

`AUTH_PROVIDER=db`에서 로그인 계정의 RLS 세션으로 저장·조회·해제합니다. 승인·게시된 축제만 저장하고 목록·전체 건수에 포함합니다. `start_date` 정렬에서 날짜가 없는 축제는 뒤에 표시합니다. 기본은 모의 모드입니다.

| # | 칸 | A11 `GET /api/v1/me/favorites` | A12 `PUT /api/v1/me/favorites/{festival_id}` | A13 `DELETE /api/v1/me/favorites/{festival_id}` |
|---|---|---|---|---|
| 1 | 목적 | 내 관심 축제 목록 | 관심 저장 | 관심 해제 |
| 2 | 헤더 | `Authorization: Bearer`(필수) | 같음 | 같음 |
| 3 | 경로·쿼리 | `page`·`page_size`(1~100, 기본 20), `sort`: `-saved_at`(기본)·`start_date` | `festival_id` 필수 | `festival_id` 필수 |
| 4 | 본문 | 없음 | 없음 | 없음 |
| 5 | 검증·권한 | 토큰 없음·만료 401. **사용자 ID는 토큰 `sub`에서만** 가져오고 경로·본문으로 받지 않음(타인 목록 조회 불가). DB는 RLS로 본인 행만 | 401 / 형식 422 / 축제 없음·비공개 404 | 401 / 422 |
| 6 | 정상 | 200 `{items[], total, page, page_size}` | **201** 새로 저장 / **200** 이미 있음(같은 응답) `{festival_id, saved_at}` | **204** (없던 것을 지워도 204 — 멱등) |
| 7 | 오류 | 401 `UNAUTHORIZED` / 422 | 401 / 404 `FESTIVAL_NOT_FOUND` / 422 | 401 / 422 |
| 8 | 실행 규칙 | 숨김 처리된 축제(`published_at` NULL)는 목록에서 빼고 `total`에도 안 셈 | `favorites` PK(user_id, festival_id)로 중복 방지. 도구 `save_favorite`도 이 API만 부름(세션 사용자 본인만) | 행 삭제 |

| A11 `items[]` | 타입 | DB |
|---|---|---|
| `festival_id`·`name`·`region_code`·`event_status` | string | `festivals`의 ID·제목·지역·상태 |
| `start_date`·`end_date` | string(date) 또는 null | `festivals` |
| `thumbnail_url` | string 또는 null | `festivals.thumbnail_url` |
| `saved_at` | string | `favorites.created_at` |

**A11 쿼리 필드 (FavoritesQuery)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `page` | query | int | 아니요 | 1 이상, 기본 1 |
| `page_size` | query | int | 아니요 | 1~100, 기본 20 |
| `sort` | query | string | 아니요 | `-saved_at`(기본)·`start_date` |

**A12 저장·A13 해제 경로, A12 응답 (FavoriteSave, 201·200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `festival_id` | path | string | A12·A13 예 | `^fst_[0-9A-Za-z]{6,26}$`, 저장·해제할 축제 ID |
| `festival_id` | 응답 | string | A12 예 | 저장된 축제 ID |
| `saved_at` | 응답 | string(date-time) | A12 예 | 최초 저장 시각, DB `favorites.created_at`에 대응 |
| `is_mock` | 응답 | boolean | A12 예 | 모의 `true`, DB `false` |

#### A23. 축제 수집 작업 이력 `GET /api/v1/admin/ingestion-jobs`

**동작 규칙** — `api.jobs.scheduler`가 매일 06:00 KST 회차에 KST 기준 올해 1월 1일부터 기존 DB 수집 경로를 실행합니다. 같은 06:00 회차에 `SEOUL_CULTURE_ENABLED=true`면 서울시 문화행사 축제 보강 수집도 실행합니다. 수집 상태와 집계는 `ingestion_jobs`에 기록하며 서울시 날짜 오류는 `DATE_INVALID`로 확인합니다. [예약 실행 예시](../../backend/Doc/jobs/IMP-PLAN.md)

| 항목 | 명세 |
|---|---|
| 권한 | admin만(401/403) |
| 쿼리 | `source_id`, `status`(`running`·`success`·`partial`·`failed`), `from`·`to`(기본 최근 7일), `page`·`page_size` |
| 응답 `items[]` | `{job_id, source_id, status, started_at, ended_at, scanned, inserted, updated, rejected, error}` — DB `ingestion_jobs` 그대로. `error`는 페이지별 오류 요약(키 값 없음) |
| 규칙 | 이 API는 조회 전용입니다. 수집은 정기 작업의 06:00 KST 회차에서 실행합니다. |

**A23 요청·이력 목록 응답 (200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `source_id` | query | string | 아니요 | `data_sources.source_id` 공급원 필터 |
| `status` | query | string | 아니요 | `running`·`success`·`partial`·`failed` |
| `from` | query | string(date-time) | 아니요 | 검색 시작 시각, 생략 시 최근 7일 범위 |
| `to` | query | string(date-time) | 아니요 | 검색 종료 시각, 생략 시 최근 7일 범위 |
| `page` | query | int | 아니요 | 요청할 페이지 번호 |
| `page_size` | query | int | 아니요 | 페이지당 결과 수 |
| `items` | 응답 | array<object> | 예 | `ingestion_jobs` 이력 목록 |
| `items[].job_id` | 응답 | string | 예 | 수집 작업 ID |
| `items[].source_id` | 응답 | string | 예 | 공급원 ID |
| `items[].status` | 응답 | string | 예 | `running`·`success`·`partial`·`failed` |
| `items[].started_at` | 응답 | string(date-time) | 예 | 시작 시각 |
| `items[].ended_at` | 응답 | string(date-time) 또는 null | 예 | 종료 시각 |
| `items[].scanned` | 응답 | int | 예 | 읽어 본 건수 |
| `items[].inserted` | 응답 | int | 예 | 추가 건수 |
| `items[].updated` | 응답 | int | 예 | 갱신 건수 |
| `items[].rejected` | 응답 | int | 예 | 제외 건수 |
| `items[].error` | 응답 | JSON 또는 null | 예 | 페이지별 오류 요약, 키 값 제외. 수집 코드에서 제외한 항목의 기록은 배열로 저장 |

#### A24. 축제 검토 대기열 `GET`·`POST /api/v1/admin/festivals/review-queue`

| 항목 | GET (목록) | POST (처리) |
|---|---|---|
| 권한 | operator·admin | operator·admin |
| 입력 | `approval_status`·`reason`·`page`·`page_size` | `{queue_id, decision, value?, note}` |
| 응답 | 200 `{items, total, page, page_size}` | 200 `{queue_id, approval_status, applied}` |
| 오류 | 401 / 403 / 422 | 401 / 403 / 404 `QUEUE_ITEM_NOT_FOUND` / 409 `ALREADY_REVIEWED` / 422 `VALIDATION_ERROR` |
| 처리 규칙 | 생성 시각과 대기열 ID 내림차순 | 승인 시 `value` 또는 `proposed_value`를 적용한 뒤 EV01 축제 및 좌표 조건을 확인하고, 아직 게시되지 않았다면 `published_at`을 설정합니다. 거절은 축제를 그대로 두고, 숨김은 `review_status='hidden'`으로 바꾸고 게시 시각을 비웁니다. 모두 처리자·시각과 `festival_change_history` 한 줄을 기록합니다. |
| 동작 규칙 | `AUTH_PROVIDER=db`에서 역할 확인 후 `noldaga_service`로 조회합니다. | 축제 행과 대기열 행을 잠가 같은 건의 결정을 한 번 반영합니다. 기본 모의 모드는 메모리 예시와 `X-Mock: true`를 사용하며, 시연용 운영자 인증은 서버 설정 `MOCK_ADMIN_REVIEW_TOKEN`으로 활성화합니다. |

**서울시 보강 동작 규칙** — 미확인 축제는 `class_unverified`, 중복이 불확실한 축제는 `duplicate`, 관리자 수정과 충돌하는 보강값은 `conflict`로 검토합니다.

**A24 GET 목록 요청·응답 (200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `approval_status` | query | string | 아니요 | `pending`(기본)·`approved`·`rejected` |
| `reason` | query | string | 아니요 | `duplicate`·`conflict`·`missing_location`·`date_unclear`·`not_festival_class`·`class_unverified`·`missing_from_source`·`coords_out_of_range` |
| `page` / `page_size` | query | int | 아니요 | 1부터, 기본값 1·20. 페이지 크기 최대 100 |
| `items` | 응답 | array<object> | 예 | 검토 대기열 항목 |
| `items[].queue_id` | 응답 | int (64비트) | 예 | `festival_review_queue.queue_id` |
| `items[].festival_id` | 응답 | string | 예 | 검토 대상 축제 ID |
| `items[].festival_name` | 응답 | string | 예 | `festivals.title` |
| `items[].reason` | 응답 | string | 예 | 위 `reason` 필터와 같은 값 |
| `items[].proposed_value` | 응답 | object 또는 null | 예 | 수집·정규화에서 제안한 변경 값 |
| `items[].approval_status` | 응답 | string | 예 | `pending`·`approved`·`rejected` |
| `items[].created_at` | 응답 | string(date-time) | 예 | 검토 항목 생성 시각 |
| `total` | 응답 | int | 예 | 필터 적용 후 전체 건수 |
| `page` / `page_size` | 응답 | int | 예 | 요청에 적용한 페이지 번호와 크기 |

**A24 POST 처리 요청·응답 (200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `queue_id` | body | int (64비트) | 예 | 처리할 대기열 ID |
| `decision` | body | string | 예 | `approve`·`reject`·`hide` |
| `value` | body | object | 아니요 | 승인 시 적용할 축제 필드. 생략하면 `proposed_value`를 사용합니다. |
| `note` | body | string | 예 | 공백을 제거한 뒤 1~200자의 결정 사유. `reason`도 같은 필드명으로 받습니다. |
| `queue_id` | 응답 | int (64비트) | 예 | 처리한 대기열 ID |
| `approval_status` | 응답 | string | 예 | 승인 `approved`, 거절·숨김 `rejected` |
| `applied` | 응답 | boolean | 예 | 축제 행에 변경 사항을 실제 반영했는지 표시 |

승인에 필요한 좌표는 위도 33~39, 경도 124~132입니다. 주소와 위경도 모두 없는 축제는 4-1절의 공개 조건을 따릅니다. 담당자는 분류·좌표 등 확인한 축제 필드를 `value`로 보완할 수 있습니다. 서버는 ID·검토 상태·게시 시각을 직접 관리합니다.

#### A26. 주변 대중교통 실시간 도착 `GET /api/v1/festivals/{festival_id}/transit`

| 항목 | 명세 |
|---|---|
| 쿼리 | `mode`: `all`(기본)·`subway`·`bus` / `radius_m`: 100~1000, 기본 500 / `limit`: 정류장·역 최대 10 |
| 공급원 | 지하철: 서울 지하철 실시간(서울만) / 버스: **서울 = 서울시 버스도착정보 15000314, 서울 밖 = TAGO** |
| 동작 규칙 | 기본 모의. `TRANSIT_PROVIDER=real`은 적재한 역·정류장을 기준으로 조회합니다. |
| 규칙 | 주변 역·정류장 목록은 A08 위치 데이터에서 찾고, 도착 정보만 실시간으로 부름. 지하철 `barvlDt`가 0이어도 도착 전일 수 있어 **`arvlMsg2` 문구를 함께** 줌. 서울 버스 `itemCount`는 0으로 와서 **건수로 쓰지 않음**. TAGO `resultCode` 99는 일시 오류로 재시도. 캐시 30초 |

**A26 쿼리 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `mode` | query | string | 아니요 | `all`(기본)·`subway`·`bus` |
| `radius_m` | query | int | 아니요 | 100~1000m, 기본 500 |
| `limit` | query | int | 아니요 | 정류장·역 최대 10곳 |

| 응답 `stations[]` | 타입 | 원본 | 설명 |
|---|---|---|---|
| `type`·`station_id`·`name`·`lat`·`lng`·`distance_m` | — | A08 위치 | 역·정류장 |
| `status` | string | — | 역·정류장마다 `ok`·`unsupported`(서울 밖 지하철)·`unavailable` |
| `arrivals[].line` | string | 지하철 `subwayId`·`trainLineNm` / 서울 버스 `rtNm` / TAGO `routeno` | 노선 |
| `arrivals[].direction` | string | 지하철 `updnLine` | 상·하행 |
| `arrivals[].eta_s` | int | 지하철 `barvlDt` / TAGO `arrtime` / 서울 버스는 `arrmsg1` 문구에서 계산(못 하면 null) | 도착까지 초 |
| `arrivals[].message` | string | 지하철 `arvlMsg2` / 서울 버스 `arrmsg1` | 공급원 문구 그대로 |
| `arrivals[].remaining_stops` | int | TAGO `arrprevstationcnt` | 남은 정류장 |
| `arrivals[].crowding` | string | 서울 버스 `reride_Num1`(`rerdie_Div1`=4일 때: 3 `여유`·4 `보통`·5 `혼잡`) | **서울 버스만**, 교통수단 선택 근거. 짝을 확인할 수 없으면 `unverified`, 서울 버스 이외에는 null |
| `observed_at` | string | 지하철 `recptnDt` / 수신 시각 | |

- 수도권 노선(인천·경기 역) 포함 여부는 미확인(부평 미호출) → 서울 역만 `ok`로 표시.
- 서울 버스 정류장 **위치**: TAGO는 서울 0건이라 쓰지 않고, **1순위 서울시 버스정류소 위치정보 파일(OA-15067)을 `facilities`(`category=bus_stop`)에 적재**, 2순위 서울 정류소정보조회 `getStaionsByPosList`(좌표 근접, 이미 승인, 1,000건/일)로 정했습니다. **파일 형식**: WGS84 경위도(변환 불필요), `NODE_ID` 9자리·`ARS_ID` 5자리(앞자리 0 유지), 서울 버스도착 API `arsId`·`stId`와 번호가 같음 → '파일로 가까운 정류장 찾기 → 같은 `ARS_ID`로 실시간 도착 조회'가 성립. 적재 전에는 서울 버스 도착을 `unverified`로 — 적재는 수집 구현 때.

#### A27. 실시간 주차 빈자리 — 채택 안 함

주차 정보는 A08 시설의 `parking`에서 주차장 위치만 제공합니다.

#### A28. 주변 교통 돌발 `GET /api/v1/festivals/{festival_id}/traffic-incidents`

| 항목 | 명세 |
|---|---|
| 쿼리 | `radius_m`: 500~10000, 기본 2000 / `type`: 선택 `accident`·`construction`·`event`·`control` |
| 공급원 | 경찰청 교통돌발(UTIC, 전국, XML) + 서울 TOPIS(서울 보강, XML) |
| 동작 규칙 | 기본 모의. `TRAFFIC_INCIDENT_PROVIDER=real`은 서울 TOPIS(일반 키)와 전국 경찰청을 조회합니다. **전국은 UTIC**(허용 IP: 학원망)를 씁니다. UTIC 응답이 공급원 호출 1회 제한(3초)보다 느려 요청 중에 부르지 않고, `UTIC_ENABLED=true`이면 API 시작 시 백그라운드 작업이 60초마다(`UTIC_REFRESH_S`, 호출 제한 `UTIC_TIMEOUT_S` 20초) 미리 받아 두며, A28은 120초 안의 마지막 성공본만 씁니다. 보관본이 없거나 오래되면 TOPIS만 보여 주고 "전국 교통 돌발을 확인할 수 없어…" 안내를 붙입니다. 워커 프로세스마다 따로 받습니다(공통 Redis 도입 뒤 한 곳으로). 공공데이터포털 경찰청 오퍼레이션(`POLICE_INCIDENT_API_URL`)은 승인된 주소가 없어 쓰지 않습니다. [info2](../../backend/Doc/info2/SPEC.md) · [utic](../../backend/Doc/utic/SPEC.md) |
| 규칙 | 경찰청은 지역 필터 없이 **전국 전체가 와서 서버가 반경으로 거름**. 날짜가 "2026년 11월 19일 16시 22분" 문자열이라 어댑터가 ISO 시각으로 바꿈. TOPIS 좌표 `grs80tm_x/y`는 GRS80 TM → 위경도 변환. 두 공급원에 같은 사건이 있으면 거리 100m 이내이고 발생 시간이 겹치면 하나로 합침(8-4 ⑧). 캐시 1분. 경로 근거(`area_evidence.traffic_incidents`)도 이 데이터를 씀 |

**A28 쿼리 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `radius_m` | query | int | 아니요 | 500~10000m, 기본 2000 |
| `type` | query | string | 아니요 | `accident`·`construction`·`event`·`control` |

| 응답 `items[]` | 타입 | 원본 | 설명 |
|---|---|---|---|
| `type` | string | 경찰청 `incidenteTypeCd`(1 사고 `accident`·2 공사 `construction`·3 행사 `event`·5 통제 `control`) / TOPIS `acc_type` | TOPIS `A02`(고장 차량)는 `accident`로 변환 |
| `title` | string | 경찰청 `incidentTitle` / TOPIS `acc_info` | |
| `lat`·`lng`·`distance_m` | number | 경찰청 `locationDataY`·`locationDataX` / TOPIS 변환값 | |
| `start_at`·`end_at` | string | 경찰청 `startDate`·`endDate` / TOPIS `occr_*`·`exp_clr_*` | null 가능 |
| `source` | string | `police_incident`·`seoul_topis` | |

#### A29. 방문 집중 예측 `GET /api/v1/festivals/{festival_id}/visit-forecast`

| 항목 | 명세 |
|---|---|
| 쿼리 | `days`: 1~30, 기본 7 |
| 공급원 | 한국관광공사 관광지 집중률 예측 15128555 + 지역별 관광 수요 강도 15151868 |
| 동작 규칙 | 기본 모의. `VISIT_FORECAST_PROVIDER=real`은 `approved:true`인 축제↔관광지 연결에서만 조회하고, **축제 장소 이름 안에 관광지 이름이 들어 있어야** 씁니다(장소가 바뀌면 자동으로 끊김). 기본 매핑 파일, 메모리 일일 캐시, 선택적 `VISIT_FORECAST_STORE=db` 적재를 지원합니다. **승인 연결**: 서울빛초롱축제·청계천의 빛 → 관광공사 관광지 집중률 `청계광장`(areaCd 11, signguCd 11140 중구). 근거: 실호출 목록에 청계광장 존재, 축제 장소 "청계천(청계광장 ~ 삼일교)"·주소 중구 태평로1가. [info2 명세](../../backend/Doc/info2/SPEC.md) |
| 규칙 | **실시간 혼잡이 아니라 상대값(0~100) 예측**이므로 다른 이름·색으로 표시. 축제 장소와 이름이 맞는 관광지(`tAtsNm`)가 있을 때만 `forecast`를 주고, 없으면 `forecast.status:"unsupported"`("이 축제 장소의 예측 자료가 없어요"). 관광 수요 강도는 **시군구 코드와 지표 코드를 함께 넣어야** 값이 옴(문서엔 선택값). 하루 1회 수집해 `realtime_snapshots`(`visit_forecast`·`region_demand`)에 저장 |

**A29 쿼리 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `days` | query | int | 아니요 | 1~30일, 기본 7 |

| 응답 필드 | 타입 | 원본 | 설명 |
|---|---|---|---|
| `forecast.attraction` | string | `tAtsNm` | 연결된 관광지 이름 |
| `forecast.days[]` | array | `baseYmd`·`cnctrRate` | `{date, rate}` rate는 0~100 상대값 |
| `region_demand` | object | `tarSjrnDsIxCd`·`tarSjrnDsIxNm`·`tarSjrnDsIxVal`·`baseYm`·`signguNm` | `{indicator, value, base_month, area_name}` 월 1회 갱신(지난달까지) |

#### A42. 지금 핫한 축제 `GET /api/v1/festivals/trending`

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 축제 탭에 네이버 검색 관심 증가율과 구석구석 인기순으로 계산한 점수 상위 축제를 보여 줌. A39 인기는 서비스 내부 조회·관심 수를 사용 |
| 2 | 요청 헤더 | `X-Request-ID`(선택). 인증 없음 |
| 3 | 경로·쿼리 | `region` 선택(2-1절 코드, 기본 `ALL`) / `limit` 1~20(기본 10) |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 공개. 쿼리 형식 위반 시 422 |
| 6 | 정상 응답 | 200 `{items[], crawled_at, source, status, partial_sources}`. 한 출처의 점수만 반영되면 `partial_sources: true`와 '일부 출처만 반영' 안내 |
| 7 | 오류 응답 | 422 `VALIDATION_ERROR` / 429 `RATE_LIMITED`. 공급원 수집 실패·한도 초과는 HTTP 200의 `status`로 표시 |
| 8 | 실행 규칙 | `festival_trends`(004·017)의 회차별 수집값으로 공개·대상 기간을 충족한 `matched` 축제의 점수를 계산. 지역 필터 적용 후 점수순으로 `limit`개 반환 |

**A42 쿼리 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `region` | query | string | 아니요 | 시·도 코드(2-1절), 기본 `ALL` |
| `limit` | query | int | 아니요 | 1~20, 기본 10 |

**수집·점수·정렬**

| 항목 | 내용 |
|---|---|
| 대상 | 게시된 축제 중 진행 중이거나 오늘부터 30일 이내에 시작하는 축제(KST) |
| 네이버 `trend_naver_datalab` ↔ `naver_datalab` | NAVER API HUB 검색어 트렌드 `POST /search-trend/v1/search`(8-4). 한도 월 50,000건 |
| 검색어 묶음 | 정식 축제 이름 사용. 일반어 단독 사용은 제외하고 비슷한 이름에는 지역명 추가. 요청당 최대 5개 묶음(축제 최대 4개와 공통 기준점 '축제' 1개). 모든 요청에 같은 기준점 묶음을 포함해 상대값 척도를 맞춤 |
| 네이버 점수 | 수집일 전날까지의 최근 7일 일별 상대값 평균 ÷ 직전 7일 평균(KST)을 `trend_ratio`로 저장. 같은 회차의 유효한 증가율 최댓값으로 나눠 0~1로 정규화. 최댓값이 0이거나 유효한 증가율이 없으면 네이버 점수는 결측 처리. 회차 최댓값은 지역·건수 필터 적용 전에 산정 |
| 신호 없음 | 최근 7일 평균이 같은 요청의 기준점 최근 7일 평균 × `TREND_MIN_RELATIVE`(0.01)보다 작거나 직전 7일 평균·기준점 평균이 0이면 `signal: no_signal`, `trend_ratio: null`로 기록하고 네이버 점수를 결측 처리 |
| 구석구석 `trend_visitkorea` ↔ `visitkorea` | 한국관광공사 대한민국 구석구석 축제 목록 인기순. 약관과 `robots.txt` 허용 확인 뒤 축제명·순위(`source_rank`)만 크롤링. 요청 간격 1초 이상, 목록 소수 페이지만, 서비스명을 넣은 User-Agent, 일시 실패 시 재시도 1회(8-4 ②) |
| 구석구석 점수 | 1 − (`source_rank` − 1) / (같은 회차 구석구석 순위 개수). 순위 개수는 매칭·지역·건수 필터 적용 전 수집 목록 기준 |
| 연결 | 데이터랩 묶음은 해당 DB 축제에 직접 연결. 구석구석은 정규화한 이름과 기간으로 연결(`name_norm+period`, LLM 없음). 공백·괄호·“제n회” 정리 후 후보가 1개면 `matched`, 여럿이면 `ambiguous`, 없으면 `unmatched`. `match_rule`을 기록하고 `matched`만 표시 |
| 최종 점수·정렬 | 두 점수가 있으면 0.6 × 네이버 점수 + 0.4 × 구석구석 점수(`TREND_SCORE_WEIGHTS`, 8-4). 한쪽 점수가 없으면(`no_signal`, 수집 실패·한도 초과·오래됨 등) 있는 쪽 점수를 그대로 쓰고 `partial_sources: true`와 '일부 출처만 반영'을 표시. 두 점수 모두 없는 축제는 현재 목록에서 제외. 점수 내림차순, 동점이면 `festival_id` 오름차순. 시작 전 축제에는 '곧 시작' 표시 가능 |
| 갱신·실패 | `TREND_CRAWL_SCHEDULE`에 따라 6시간마다 수집. 회차 기준 시각(`crawled_at`)을 공유하고 출처별 작업을 A23 `ingestion_jobs`에 기록. 수집 실패·한도 초과 또는 마지막 성공 12시간 초과(`TREND_STALE_H`)인 출처는 현재 점수에서 제외. 응답의 지역·건수 필터 적용 전에 두 출처 모두 현재 회차에서 사용할 점수가 없으면 마지막 성공 목록과 기준 시각을 `status: stale`로 반환. 성공 목록이 없으면 `status: unavailable`, `items: []` |
| 보존 | `festival_trends` 30일(DB 설계서 7-0) |

| 응답 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `crawled_at` | string(date-time) | null 가능 | 표시한 성공 회차의 기준 시각. `stale`에서도 갱신 없이 그대로 반환. 성공 이력이 없으면 `null` |
| `source` | string | null 가능 | 표시 목록의 `items[].sources` 합집합 기준. 데이터랩만 `naver_datalab`, 구석구석만 `visitkorea`, 둘 다 있으면 `combined`, 빈 목록은 `null` |
| `status` | string | 불가 | `ok` 현재 회차, `stale` 마지막 성공 회차, `unavailable` 성공 이력 없음 |
| `partial_sources` | boolean | 불가 | 표시 목록에 한 출처만 반영된 항목이 하나라도 있으면 `true`. `stale`이면 이전 목록 값을 사용하며 빈 목록은 `false` |
| `items[].rank` | int | 불가 | 응답 표시 순서(1부터) |
| `items[].festival_id`·`name`·`region_code`·`start_date`·`end_date`·`thumbnail_url`·`image_credit` | — | 썸네일 null 가능 | `festivals` 표시 필드 |
| `items[].source_rank` | int | 가능 | 점수에 반영한 구석구석 순위. 구석구석 점수를 반영하지 않으면 `null` |
| `items[].crawled_at` | string(date-time) | 불가 | 해당 항목에 반영된 `festival_trends.crawled_at` 중 가장 최근 시각 |
| `items[].score` | number | 불가 | 0~1 최종 점수. 두 출처의 가중합 또는 사용 가능한 한쪽 점수 |
| `items[].signal` | string | 불가 | 네이버 점수가 반영되면 `ok`, 사용할 수 없으면 `no_signal`. `no_signal`이어도 구석구석 점수는 반영 가능 |
| `items[].sources` | array<string> | 불가 | 점수에 반영된 출처만 포함. `trend_naver_datalab` ↔ `naver_datalab`, `trend_visitkorea` ↔ `visitkorea` |
| `items[].partial_sources` | boolean | 불가 | 항목에 출처 하나만 반영되면 `true` |

#### A81. 요즘 올라온 글 `GET /api/v1/festivals/{festival_id}/posts`

축제 상세에 네이버 검색 API(NAVER API HUB)의 블로그·뉴스·카페 검색 결과를 보여 줍니다. 검색 결과 제공 목적의 표시 전용 API이며 A42 점수 산출에서 제외합니다. 결과마다 출처를 표시하고, 카페 결과는 원문 링크로만 제공합니다(요약 없음).

| 항목 | 명세 |
|---|---|
| 요청 | 인증 없음. `X-Request-ID` 선택. 경로 변수만 받음 |
| 공급원 | `GET /search/v1/blog`의 `postdate`(yyyyMMdd), `GET /search/v1/news`의 `pubDate`(KST로 변환), `GET /search/v1/cafearticle`(날짜 없음). `title`·`description`의 검색 강조 `<b>` 태그 제거(8-4) |
| 결과 선별 | 태그를 제거한 제목에 정식 축제 이름(`festivals.title`)이 정확히 포함된 글을 선별. 블로그·뉴스는 KST 게시일이 축제 시작일 30일 전 이후(경계일 포함)인 글을 최신순으로 정렬하며, 시작일이 없으면 해당 두 출처의 글은 제외. 카페는 제목 정확 일치 조건만 적용하고 날짜가 있는 글 다음에 공급원 반환 순서로 표시. 세 출처를 합쳐 최대 `POSTS_LIMIT`건(설정 범위 3~5, 기본 5) |
| 캐시 | 정상 결과의 제목·링크·게시일·출처 종류만 Redis `posts:{festival_id}`에 `POSTS_CACHE_TTL_S`(600초) 동안 저장. 글 목록의 영구 저장과 본문 저장은 하지 않음 |
| 정상·실패 | HTTP 200. 정상 조회는 `status: ok`(결과가 없으면 `items: []`), 공급원 오류·한도 초과 시 `items: []`, `status: unavailable`, `retryable: true`. 실패 응답은 캐시하지 않음 |
| 오류 | 404 `FESTIVAL_NOT_FOUND`(존재하지 않거나 공개되지 않은 축제), 422 `VALIDATION_ERROR`(경로 변수 형식 오류). 공통 오류 형식(2절) |

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `festival_id` | path | string | 예 | `^fst_[0-9A-Za-z]{6,26}$`, 공개 축제 ID |
| `status` | 응답 | string | 예 | `ok` 또는 `unavailable` |
| `retryable` | 응답 | boolean | 예 | 공급원 실패 시 `true`, 정상 조회 시 `false` |
| `items` | 응답 | array<object> | 예 | 게시일이 있는 글을 최신순으로 표시한 후 카페 글을 공급원 반환 순서로 표시 |
| `items[].title` | 응답 | string | 예 | 원문 제목(평문) |
| `items[].url` | 응답 | string(uri) | 예 | 원문 링크. 카페는 이 링크로 이동 |
| `items[].published_date` | 응답 | string(date) 또는 null | 예 | 블로그·뉴스 게시일(ISO 8601, KST). 카페는 `null` |
| `items[].source_type` | 응답 | string | 예 | `blog`·`news`·`cafe`. 화면에서 네이버 블로그·뉴스·카페로 출처 표시 |

#### A30. 데이터 공급원 상태 `GET /api/v1/data-sources`

| 항목 | 명세 |
|---|---|
| 권한 | 공개(화면의 '미지원' 안내용). 키 정보는 절대 안 보여 줌 |
| 쿼리 | `region_code`: 선택 — 주면 그 지역에서 켜진 공급원만 |
| 응답 `items[]` | `{source_id, name, scope, enabled_region_codes[], is_realtime, refresh_s, status, last_success_at}` — DB `data_sources`(`key_site`·`notes`는 빼고) |
| 규칙 | `status`가 `verified`가 아니면 화면은 그 정보를 '준비 중'으로. 조회만, 캐시 10분 |

**A30 요청·응답 (200)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `region_code` | query | string | 아니요 | 2-1절의 지역 코드, 지정하면 그 지역에서 켜진 공급원만 조회 |
| `items` | 응답 | array<object> | 예 | 공급원 목록 |
| `items[].source_id` | 응답 | string | 예 | `data_sources.source_id` |
| `items[].name` | 응답 | string | 예 | 공급원 표시 이름 |
| `items[].scope` | 응답 | string | 예 | `national`·`seoul_only`·`region_specific` |
| `items[].enabled_region_codes` | 응답 | array<string> | 예 | 켜진 지역 코드 목록 |
| `items[].is_realtime` | 응답 | boolean | 예 | 실시간 공급원 여부 |
| `items[].refresh_s` | 응답 | int 또는 null | 예 | 갱신 주기(초) |
| `items[].status` | 응답 | string | 예 | `planned`·`key_issued`·`verified`·`disabled` |
| `items[].last_success_at` | 응답 | string(date-time) 또는 null | 예 | 마지막 수집 성공 시각 |

### 7-2. 맞춤 추천·친구·동행·채팅·알림·마이페이지 — 상세 명세

기획서 FR-REC01~16·FR-COM12~14와 취향 5개·권한 기준안을 기준으로 합니다. DB는 04 문서 마이그레이션 005(시험 T29~T33).

#### 7-2-1. 축제를 5가지 취향으로 분류하는 방법 (규칙 후보 → LLM 검증)

**원칙(FR-REC09):** 공식 원문에 근거가 있는 태그만 추천에 씁니다. 반려견 동반 가능, '한가로움' 같은 속성을 추측으로 붙이지 않습니다. 근거가 없으면 그 취향으로 분류하지 않습니다(추천에서 빠질 뿐, 축제 검색에는 그대로 나옴).

**① 취향 → 태그 연결표** (축제에는 *태그*를 붙이고, 취향은 태그 조합으로 찾음)

| 취향 (`scenario`) | 필요한 태그 | 태그 뜻 | 후보 규칙이 보는 공식 원문 (TourAPI) |
|---|---|---|---|
| `family_relaxed` 가족 + 한가로운 | `family_program` **그리고** `relaxed` | 가족·어린이 대상 프로그램 / 붐비지 않는 관람형 | `program`·`subevent`·`overview`의 "가족·어린이·체험"; `relaxed`는 원문 "산책·휴식·여유" **또는** 방문 집중 예측(A29) 하위 30% |
| `friends_activity` 친구 + 액티비티 | `activity` | 직접 참여하는 체험·공연·경연 | "체험·참여·경연·공연·만들기·레이스" |
| `couple_photo` 연인 + 포토존 | `photo_spot` | 포토존·야경·조명 | "포토존·야경·빛·조명·일루미네이션" |
| `pet` 반려견과 함께하는 축제 | `pet_allowed` | 반려견 동반 가능이 **명시** | "반려견·애견·펫 동반 가능" — 원문(`overview`·`program`·`subevent`·`agelimit`)에 있을 때만(DB가 예측 데이터 근거를 거부, T30c) |
| `solo` 혼자 즐기기 | `solo_friendly` | 혼자 관람·참여해도 되는 관람형·전시·야시장 | "관람·전시·야시장·1인" |

**② 처리 순서** (축제 수집 뒤 워커 주기 작업 `classify_festival_tags`, 요청 때 실행하지 않음)

| 단계 | 누가 | 하는 일 | 결과 (`festival_tags.status`) |
|---|---|---|---|
| 1 후보 | 규칙 코드 | 위 표의 키워드 규칙(`rule_id`, 예 `kw_photo_v1`)으로 태그 후보와 **원문 문장 위치**를 찾음 | `candidate` |
| 2 검증 | **LLM** | 후보 1개마다 *"이 원문 문장이 이 태그의 근거가 되는가?"*만 판단. 입력 = 태그 정의 + 원문 필드 원문 그대로, 출력 = `{decision: accept·reject·insufficient, evidence_quote, evidence_field}`(JSON 스키마 고정, temperature 0) | — |
| 3 코드 확인 | 코드 | **`evidence_quote`가 해당 원문 필드에 글자 그대로 들어 있는지** 확인(LLM이 근거를 지어내면 여기서 걸림 → `insufficient`). 반려견 동반은 원문 필드만 허용 | `verified`·`rejected`·`insufficient` |
| 4 사용 | 추천 API | `verified`만 점수·추천 이유에 씀 | — |
| 다시 분류 | 워커 | 원문이 바뀌면(`festival_sources.raw_checksum` 변경) 그 축제만 다시. 예전 태그는 `revoked` | 새 행 |
| 관리자 | 운영자(선택) | 잘못된 태그를 `revoked`로 내릴 수 있음(필수 승인 단계는 없음) | `revoked` |

- **LLM 비용 상한:** 새로 들어오거나 바뀐 축제만, 하루 최대 300건(초기값 `TAG_LLM_DAILY_MAX`, 8-4). 축제당 후보만 보내므로 전국 첫 분류도 며칠에 나눠 처리. 모델은 팀 LLM 결정을 따르고 `model`·`prompt_version`을 행마다 남깁니다.
- **LLM이 실패하면**(시간 초과·형식 오류) 후보는 `candidate`로 남고 추천에 쓰지 않습니다 — 추천이 줄어들 뿐 틀린 추천은 나오지 않습니다.
- **원문이 짧아 근거가 없는 축제가 많으면** 그 취향 추천이 비어 보일 수 있습니다 → 화면은 '전체 축제 보기'로 안내(FR-REC15). 실제 비율은 수집 뒤 확인.

**③ 점수 (A38, FR-REC08)** — 가중치는 초기값 `REC_WEIGHTS_VERSION = rec-0.1`

`점수 = 0.5 × 태그 일치 + 0.2 × 날짜 적합 + 0.2 × 정보 완성도 + 0.1 × 관심 저장 보정`

| 항목 | 계산 (0~1) |
|---|---|
| 태그 일치 | 고른 취향마다 필요한 태그를 모두 가진 비율(여러 취향을 고르면 가장 높은 값). 취향 `pet`(반려견과 함께하는 축제)을 고르면 그 취향 점수는 `pet_allowed`가 검증된 축제만 1, 없으면 0 — 반려견은 **별도 칸 없이 취향 값 하나**(기획서 FR-REC03) |
| 날짜 적합 | 진행 중 1.0, 14일 안 시작 0.7, 30일 안 0.4, 그 뒤 0.1. 종료·취소·비공개는 **후보에서 제외** |
| 정보 완성도 | 대표 이미지·소개·장소 좌표·입장료 중 있는 비율 |
| 관심 저장 보정 | 최근 7일 관심 추가 수의 순위 백분위 |

동점이면 시작일 → `festival_id` 순으로 고정합니다(같은 요청이면 같은 순서).

#### 7-2-2. 추천 API (A36~A41)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A36** `GET /api/v1/me/festival-preferences` | — | `{scenarios[], onboarding_status, updated_at}` (행이 없으면 `onboarding_status:"pending"`) | user, 본인만(RLS, T29e) | 401 |
| **A37** `PUT /api/v1/me/festival-preferences` | `{scenarios: [5개 중 0~5개], skip: bool}` — 반려견은 `scenarios`에 `pet`으로 | 200 A36과 같은 모양 | user. `skip=true` 또는 빈 배열 → `skipped`(FR-REC04), 1개 이상 → `completed`. 바꾸면 다음 A38부터 다시 계산(FR-REC05) | 401 / 422(모르는 값 — DB도 거부, T29a) |
| **A38** `GET /api/v1/festivals/recommended` | 쿼리 `scenarios`(비로그인일 때 쉼표 구분, 로그인이면 저장된 취향이 기본) · `region` · `date_from`·`date_to` · `page`·`page_size`(≤50) | `{items[] {festival_id, name, region_code, start_date, end_date, event_status, thumbnail_url, image_credit, score, applied_tags[], recommendation_reason[]}, score_version, total, page, page_size, fallback}` | 선택 로그인. `recommendation_reason`은 **검증된 태그의 근거 문장으로 만든 고정 문구**(요청 때 LLM 안 씀). 예: "공식 안내에 '야간 포토존 운영'이 있어요". 일치 축제가 없으면 `items:[]`, `fallback:"all_festivals"`(FR-REC15). 추천됐다고 관심 저장하지 않음(FR-REC14) | 422 |
| **A39** `GET /api/v1/festivals/popular` | `region` · `page` | `{items[] {…카드 필드, views_7d, favorites_7d}, window:"7d", fallback}` | 공개. 최근 7일 `festival_engagement_daily` 합. **사람 1명 하루 1회**만 셈(Redis `eng:{festival_id}:{day}`에 세션 HMAC 집합 → 하루 끝에 숫자만 DB로, 테스트·봇 User-Agent 제외). 지표가 20건 미만이면 `fallback:"recent"`로 A41 목록 | 422 |
| **A40** `GET /api/v1/festivals/discover` | `region` · `page` · `seed`(선택) | `{items[], seed, page}` | 공개. 섞는 순서 = `hash(seed, festival_id)`. `seed` 없으면 서버가 `날짜+세션`으로 만들어 돌려줌 → 같은 seed면 페이지를 넘겨도 순서 고정(FR-REC11) | 422 |
| **A41** `GET /api/v1/festivals/recent` | `region` · `page` | `{items[] {…, published_at}}` | 공개. `festivals.published_at` 최신순. 재수집해도 최초 공개일 유지(FR-REC13) | 422 |

- A36·A37은 `AUTH_PROVIDER=db`에서 본인의 `user_festival_preferences` 행을 읽고 저장하며, 기본은 모의 모드입니다. 미저장 상태는 빈 배열과 `updated_at:null`로 응답합니다. 건너뛰면 빈 배열을 저장하고, 중복 취향은 첫 선택 순서를 유지해 하나로 저장합니다.

- A38~A41의 축제 목록은 승인·게시된 예정/진행 축제만(종료·취소·비공개 제외), 없는 축제를 만들지 않음. A36~A41 고정 경로는 `/festivals/{festival_id}`보다 먼저 등록(3절 라우터 규칙).

**A36 조회·A37 저장 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `scenarios` | body | array<string> | A37 예 | 0~5개, `family_relaxed`·`friends_activity`·`couple_photo`·`pet`·`solo` |
| `skip` | body | boolean | A37 예 | `true` 또는 빈 `scenarios`이면 건너뛰기 |
| `scenarios` | 응답 | array<string> | A36·A37 예 | 저장한 취향, 위 5개 값 |
| `onboarding_status` | 응답 | string | A36·A37 예 | `pending`(저장 행 없음)·`completed`·`skipped` |
| `updated_at` | 응답 | string(date-time) 또는 null | A36·A37 예 | 취향 저장 행의 마지막 갱신 시각 |

**A38 맞춤·A39 인기·A40 둘러보기·A41 최신 목록 쿼리**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `region` | query | string | 아니요 | 시·도 코드, 2-1절 |
| `page` | query | int | 아니요 | 조회할 페이지 번호 |
| `scenarios` | query | string | A38 선택 | 비로그인일 때 쉼표로 구분한 취향 코드, 로그인 시 저장 취향이 기본 |
| `date_from` | query | string(date) | A38 선택 | 축제 기간 필터 시작일 |
| `date_to` | query | string(date) | A38 선택 | 축제 기간 필터 종료일 |
| `page_size` | query | int | A38 선택 | 페이지당 최대 50건 |
| `seed` | query | string | A40 선택 | 정렬 시드, 생략 시 서버가 날짜와 세션으로 생성 |

**A38·A39·A40·A41 공통 축제 카드와 각 목록 응답**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `items` | 응답 | array<object> | 예 | 승인·게시된 예정/진행 축제 카드 목록 |
| `items[].festival_id` | 응답 | string | 예 | 축제 ID |
| `items[].name` | 응답 | string | 예 | 축제명 |
| `items[].region_code` | 응답 | string | 예 | 시·도 코드 |
| `items[].start_date` | 응답 | string(date) 또는 null | 예 | 시작일 |
| `items[].end_date` | 응답 | string(date) 또는 null | 예 | 종료일 |
| `items[].event_status` | 응답 | string | 예 | `upcoming`·`ongoing` |
| `items[].thumbnail_url` | 응답 | string 또는 null | 예 | 카드 이미지 URL |
| `items[].image_credit` | 응답 | string 또는 null | 예 | 이미지 출처(4-2절) |
| `items[].score` | 응답 | number | A38 예 | 추천 규칙으로 계산한 점수 |
| `items[].applied_tags` | 응답 | array<string> | A38 예 | 적용한 검증 태그(`festival_tags.tag`, 7-2-1절) |
| `items[].recommendation_reason` | 응답 | array<string> | A38 예 | 검증된 근거 문장으로 만든 고정 추천 문구 |
| `score_version` | 응답 | string | A38 예 | 추천 점수 규칙 버전 |
| `total` | 응답 | int | A38 예 | 추천 필터 적용 후 전체 건수 |
| `page` | 응답 | int | A38·A40 예 | 응답 페이지 번호 |
| `page_size` | 응답 | int | A38 예 | 적용한 페이지 크기 |
| `fallback` | 응답 | string | 조건부 | A38 일치 축제가 없으면 `all_festivals`, A39 지표가 20건 미만이면 `recent` |
| `window` | 응답 | string | A39 예 | `7d`, 인기 지표 집계 기간 |
| `items[].views_7d` | 응답 | int | A39 인기 항목 | 최근 7일 상세 조회 합계(`detail_views`) |
| `items[].favorites_7d` | 응답 | int | A39 인기 항목 | 최근 7일 관심 추가 합계(`favorites_added`) |
| `seed` | 응답 | string | A40 예 | 실제 정렬에 사용한 시드 |
| `items[].published_at` | 응답 | string(date-time) | A41 최신 항목 | 최초 공개 시각, 최신순 정렬 기준 |

#### 7-2-3. 친구 API (A43~A50)

**동작 규칙** — A43~A50은 `AUTH_PROVIDER=db`면 PostgreSQL, 기본은 mock 모드입니다. A43은 사용자별 최근 60초에 20회까지 허용하며 Redis 연동 전에는 API 프로세스 메모리에 횟수를 보관합니다. A47은 1페이지부터 20건씩 반환합니다. A49에서 기존 1:1 방을 닫고, A50은 실제 차단 삭제가 끝나면 채팅 연동 함수 `notify_chat_unblocked`를 호출합니다. 새 1:1 방 개설은 A67에서 처리합니다.

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A43** `GET /api/v1/users/search` | 쿼리 `nickname`(2~12자) — **정확히 일치만**(대소문자 무시, 일부만 치면 0건) | `{items[] {user_id, display_name, friendship_status: none·pending_sent·pending_received·friends}}` 최대 1건(닉네임은 겹치지 않음) | user. **친구 코드 없음, 닉네임으로 검색**(DB `app_find_user_by_nickname`). 나이·성별은 돌려주지 않음. 이메일·전화번호로는 검색 안 됨. 나를 차단한 사람·내가 차단한 사람은 안 나옴 | 401 / 422 / 429(분당 20회) |
| **A44** `POST /api/v1/friend-requests` | `{to_user_id}` | 201 `{request_id: "frq_…", status:"pending"}` | user. 나 자신(DB 거부, T32c)·이미 친구·차단 관계면 거부. 반대 방향으로 대기 중 신청이 있으면 **그 신청을 바로 수락으로 처리**(중복 신청 대신) | 401 / 404 / 409 `ALREADY_FRIENDS`·`REQUEST_PENDING`·`BLOCKED` |
| **A45** `GET /api/v1/me/friend-requests` | 쿼리 `box`: `received`(기본)·`sent` | `{items[] {request_id, user_id, display_name, status, created_at}}` | user, 당사자만(RLS, T33c) | 401 |
| **A46** `POST /api/v1/friend-requests/{request_id}/{action}` | `action`: `accept`·`reject`(받은 사람) / `cancel`(보낸 사람) | 200 `{request_id, status}` | 정해진 사람만. `accept`는 **한 트랜잭션**으로 신청 상태 변경 + `friendships` 1행(작은 ID가 `user_a`) | 401 / 403 / 404 / 409 `REQUEST_NOT_PENDING` |
| **A47** `GET /api/v1/me/friends` | `page` | `{items[] {user_id, display_name, since}}` | user, 당사자만 | 401 |
| **A48** `DELETE /api/v1/me/friends/{user_id}` | — | 204 (친구가 아니어도 204, 멱등) | user | 401 |
| **A49** `PUT /api/v1/me/blocks/{user_id}` | — | 200 `{blocked: true}` | user. **한 트랜잭션**: 차단 추가 + 친구 관계 삭제 + 대기 중 신청 `cancelled`. 차단당한 사람은 차단 사실을 볼 수 없음(T33d). 두 사람의 1:1 방은 `closed`로 전환하고 차단 해제 뒤에도 닫힌 채 유지. 다시 대화하려면 새 방에서 시작(A50·A67). 공동 단체방·동행방은 남음(서로의 메시지 숨김은 범위 밖) | 401 / 422(자기 자신) |
| **A50** `DELETE /api/v1/me/blocks/{user_id}` | — | 204 | user. 차단을 풀어도 친구 관계는 자동 복원하지 않으며 **기존 1:1 방은 닫힌 채 유지**. 다시 친구가 된 뒤 새 방에서 대화를 시작(A67) | 401 |

**A43 정확한 닉네임 검색**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `nickname` | query | string | 예 | 2~12자, 대소문자 무시 정확히 일치 |
| `items` | 응답 | array<object> | 예 | 검색 결과 최대 1건 |
| `items[].user_id` | 응답 | string (UUID) | 예 | 찾은 사용자 ID |
| `items[].display_name` | 응답 | string | 예 | 그 사용자의 닉네임 |
| `items[].friendship_status` | 응답 | string | 예 | `none`·`pending_sent`·`pending_received`·`friends` |

**A44 신청·A45 신청 목록·A46 신청 처리**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `to_user_id` | body | string (UUID) | A44 예 | 받는 사람 ID, `friend_requests.to_user`, 자기 자신 제외 |
| `box` | query | string | A45 선택 | `received`(기본)·`sent` |
| `request_id` | path | string | A46 예 | `^frq_[0-9A-Za-z]{6,26}$`, 처리할 신청 ID |
| `action` | path | string | A46 예 | `accept`·`reject`는 받은 사람, `cancel`은 보낸 사람 |
| `request_id` | 응답 | string | A44·A46 예 | 생성하거나 처리한 신청 ID |
| `status` | 응답 | string | A44·A46 예 | 신규 신청은 `pending`, 자동 수락은 `accepted`. A46 처리 후 `accepted`·`rejected`·`cancelled` |
| `items` | 응답 | array<object> | A45 예 | 받거나 보낸 신청 목록 |
| `items[].request_id` | 응답 | string | A45 예 | 신청 ID |
| `items[].user_id` | 응답 | string (UUID) | A45 예 | 받은 신청의 보낸 사람 또는 보낸 신청의 받은 사람 |
| `items[].display_name` | 응답 | string 또는 null | A45 예 | 신청 상대 닉네임 |
| `items[].status` | 응답 | string | A45 예 | `pending`·`accepted`·`rejected`·`cancelled` |
| `items[].created_at` | 응답 | string(date-time) | A45 예 | 신청 시각 |

**A47 친구 목록·A48 삭제·A49 차단·A50 차단 해제**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `page` | query | int | A47 선택 | 조회할 페이지 번호 |
| `user_id` | path | string (UUID) | A48·A49·A50 예 | 대상 사용자 ID, A49는 자기 자신 제외 |
| `items` | 응답 | array<object> | A47 예 | 내 친구 목록 |
| `items[].user_id` | 응답 | string (UUID) | A47 예 | 친구 사용자 ID |
| `items[].display_name` | 응답 | string 또는 null | A47 예 | 친구 닉네임 |
| `items[].since` | 응답 | string(date-time) | A47 예 | 친구가 된 시각(`friendships.created_at`) |
| `blocked` | 응답 | boolean | A49 예 | 차단 완료 시 `true` |

- A46은 먼저 RLS 조회로 신청 당사자와 처리 권한을 확인합니다. API 서버는 `noldaga_service` 역할로 두 사용자 행을 잠근 뒤 신청 상태와 차단 여부를 다시 확인하고 한 트랜잭션에서 쓰기를 처리합니다(04 문서 3절, T33b).
- A44의 교차 신청도 201로 응답하며 기존 신청 ID와 `accepted`를 반환합니다. 자기 자신에게 신청하면 404입니다.
- 동행 승인은 친구 추가로 이어지지 않습니다(친구 추가 API로만).
- **친구 추천**(같이 동행한 사람, 취향이 비슷한 사람 등)은 기획서에 없어 **이번 범위에서 뺍니다.** 후보로만 남깁니다. 넣으면 개인정보 노출(누가 누구와 동행했는지) 검토가 먼저 필요합니다.

#### 7-2-4. 동행 API (A57~A65)

**동작 규칙** — A57~A65와 글 수정·수동 마감을 연결했습니다. 기본은 메모리 mock이며 `AUTH_PROVIDER=db`에서 RLS 조회와 서비스 트랜잭션을 사용합니다. 채팅방 생성·입장은 `ChatRooms` 기본 DB 구현을 호출합니다. A60 신청과 A62 승인은 양방향 차단 관계를 검사하고 `409 BLOCKED`로 거부합니다. [동행 구현·검증](../../backend/Doc/companions/IMP-PLAN.md)

시간당 정기 작업이 기본 `meet_at + 12시간`에 도달한 글을 자동 종료하고 방을 읽기 전용으로 전환합니다. 종료·취소 시각부터 72시간이 지나면 동행 내용을 정리합니다.

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A57** `GET /api/v1/festivals/{festival_id}/companion-posts` | `status`(기본 `open`)·`page`(기본 1, 20개씩) | `{items[] {post_id, author_display_name, meet_at, capacity, approved_count, age_pref, gender_pref, memo, status}}` | 공개. **정확한 만남 장소는 안 줌**(FR-COM01·08) | 404 / 422 |
| **A58** `POST /api/v1/companion-posts` | `{festival_id, meet_at, capacity(1~10, 작성자 제외), age_pref?, gender_pref?, memo?(≤500)}` | 201 `{post_id, room_id}` | user. `meet_at`은 **축제 기간 안의 미래 시각만**(400 `MEET_AT_INVALID`, FR-COM03). 한 트랜잭션: 동행방(`companion`) 만들기 + 작성자 방장 입장 + 글 저장, 만남 장소는 처음 '미정'(FR-COM04) | 401 / 400 / 404 / 422 |
| **A59** `GET /api/v1/companion-posts/{post_id}` | — | A57 한 건 + `my_application_status` | 공개 | 404 |
| **A58 보완** `PATCH /api/v1/companion-posts/{post_id}` | `meet_at`·`capacity`·`age_pref`·`gender_pref`·`memo` 중 1개 이상 | 200 `{post_id, status}` | 작성자만. 일정 검증은 A58과 같으며 정원은 승인 인원 이상이어야 함. `age_pref`·`memo`의 null은 기존 값 제거. 수동 마감은 정원 변경 뒤에도 유지 | 401 / 400 `MEET_AT_INVALID` / 403 / 404 / 409 `CAPACITY_FULL`·`POST_CLOSED` / 422 |
| **A60** `POST /api/v1/companion-posts/{post_id}/applications` | `{message?(≤200)}` | 201 `{application_id, status:"pending"}` | user. 본인 글·마감·종료 글 거부, **대기·승인·거절 기록이 있으면 재신청 불가, 취소했으면 재신청 가능**(DB 부분 UNIQUE, T36a). 차단 관계면 신청 거부. 작성자에게 알림 | 401 / 403 `OWN_POST` / 404 / 409 `APPLICATION_EXISTS`·`POST_CLOSED`·`BLOCKED` |
| **A61** `GET /api/v1/companion-posts/{post_id}/applications` | `status` | `{items[] {application_id, applicant_display_name, applicant_age, applicant_gender, message, status, created_at}}` — `applicant_age`는 서버가 출생연도로 계산한 나이(올해 − 출생연도), 출생연도 자체는 보내지 않음. 대기·승인 중인 신청만, 탈퇴자는 '알 수 없음' — 신청 화면에서 '닉네임·나이·성별이 작성자에게 보여요'를 미리 알림(S07) | **작성자만**(나이·성별은 DB `app_applicant_profile`, T43b·c)(신청자는 A59의 자기 상태만, RLS T37c) | 401 / 403 |
| **A62** `POST /api/v1/companion-applications/{application_id}/{action}` | `action`: `approve`·`reject`(작성자) / `cancel`(신청자, 승인 전만) | 200 `{application_id, status, post_status}` | `approve`는 **한 트랜잭션**: `SELECT … FOR UPDATE`로 글을 잠그고 정원 확인 → 신청 승인 → `approved_count+1`(정원 넘으면 DB가 거부, T36c) → 방 멤버 입장 → 시스템 메시지 → 정원이 차면 `full`(FR-COM06·07). 차단 관계면 승인 거부. 승인·거절 알림. **친구는 자동 추가 안 함**(FR-COM13) | 401 / 403 / 404 / 409 `CAPACITY_FULL`·`APPLICATION_NOT_PENDING`·`POST_CLOSED`·`BLOCKED` |
| **A63** `PUT /api/v1/companion-posts/{post_id}/meeting-place` | `{name, address?, lat?, lng?, guide?}` (좌표 없이 이름·주소만도 가능 — 지도 오류 시 텍스트) | 200 `{post_id, updated_at}` | **작성자만**. 바꾸면 시스템 메시지 + 참여자 알림 `meeting_place_changed`(FR-COM10·11) | 401 / 403 / 422 |
| **A64** `GET /api/v1/companion-posts/{post_id}/meeting-place` | — | `{name, address, lat, lng, guide, updated_at}` 없으면 `{status:"undecided"}` | **작성자·승인 참여자만**(RLS, T37a·f) | 401 / 403 |
| **A65** `POST /api/v1/companion-posts/{post_id}/{action}` | `action`: `close`(모집 마감)·`end`(종료)·`cancel`(만남 전 취소) | 200 `{post_id, status}` | 작성자만. 수동 마감은 `full`로 표시. 만남 시각 + 12시간(초기값 `COMPANION_AUTO_END_H`)이 지나면 자동 `end`. 종료·취소 → 동행방 **읽기 전용**(`read_only_at`) → '지난 동행'(FR-COM18·19) → 3일 뒤 내용 정리(04 문서 7-0) | 401 / 403 / 404 / 409 `POST_CLOSED` |

**A57 목록·A58 등록·A59 상세 요청**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `festival_id` | path | string | A57 예 | `fst_…`, 목록을 조회할 축제 ID |
| `status` | query | string | A57 선택 | `open`(기본)·`full`·`ended`·`cancelled` |
| `page` | query | int | A57 선택 | 조회할 페이지 번호 |
| `festival_id` | body | string | A58 예 | `fst_…`, 모집할 축제 ID |
| `meet_at` | body | string(date-time) | A58 예 | 축제 기간 안의 미래 시각 |
| `capacity` | body | int | A58 예 | 1~10명, 작성자 제외 |
| `age_pref` | body | string | A58 선택 | `any`·`20s`·`30s`·`40s`·`50s_plus` |
| `gender_pref` | body | string | A58 선택 | `any`(DB 기본값)·`female`·`male` |
| `memo` | body | string | A58 선택 | 모집 안내, 500자 이하 |
| `post_id` | path | string | A59 예 | `^cpo_[0-9A-Za-z]{6,26}$`, 조회할 모집 글 ID |

**A57 목록·A58 등록·A59 상세 응답**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `items` | 응답 | array<object> | A57 예 | 축제 동행 모집 글 목록 |
| `post_id` | 응답 | string | 예 | 모집 글 ID, A57에서는 `items[].post_id` |
| `author_display_name` | 응답 | string 또는 null | A57·A59 예 | 작성자 닉네임(`app_public_display_name`), A57에서는 항목 필드 |
| `meet_at` | 응답 | string(date-time) | A57·A59 예 | 만남 시각 |
| `capacity` | 응답 | int | A57·A59 예 | 모집 정원(작성자 제외 1~10명) |
| `approved_count` | 응답 | int | A57·A59 예 | 승인 인원, 0 이상 정원 이하 |
| `age_pref` | 응답 | string 또는 null | A57·A59 예 | 위 A58의 연령대 조건 |
| `gender_pref` | 응답 | string | A57·A59 예 | 위 A58의 성별 조건 |
| `memo` | 응답 | string 또는 null | A57·A59 예 | 모집 안내 |
| `status` | 응답 | string | A57·A59 예 | `open`·`full`·`ended`·`cancelled` |
| `room_id` | 응답 | string | A58 예 | 모집 글과 함께 생성한 동행 채팅방 ID |
| `my_application_status` | 응답 | string 또는 null | A59 예 | 본인 신청의 `pending`·`approved`·`rejected`·`cancelled`, 본인 신청이 없으면 null |

A57의 글 필드는 `items[]` 안에 있으며, A59는 글 한 건과 본인 신청 상태를 반환합니다.

**A60 신청·A61 신청 목록·A62 승인·거절·취소**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `post_id` | path | string | A60·A61 예 | `^cpo_[0-9A-Za-z]{6,26}$`, 모집 글 ID |
| `message` | body | string | A60 선택 | 신청 메시지, 200자 이하 |
| `status` | query | string | A61 선택 | 신청 상태 필터, 조회 대상은 `pending`·`approved` |
| `application_id` | path | string | A62 예 | `^cap_[0-9A-Za-z]{6,26}$`, 처리할 신청 ID |
| `action` | path | string | A62 예 | `approve`·`reject`는 작성자, `cancel`은 승인 전 신청자 |
| `application_id` | 응답 | string | A60·A62 예 | 등록하거나 처리한 신청 ID |
| `status` | 응답 | string | A60·A62 예 | A60은 `pending`, A62는 `approved`·`rejected`·`cancelled` |
| `post_status` | 응답 | string | A62 예 | 처리 후 모집 글 상태, 정원이 차면 `full` |
| `items` | 응답 | array<object> | A61 예 | 작성자만 받는 신청 목록 |
| `items[].application_id` | 응답 | string | A61 예 | 신청 ID |
| `items[].applicant_display_name` | 응답 | string 또는 null | A61 예 | 신청자 닉네임, 탈퇴자는 화면에서 ‘알 수 없음’ |
| `items[].applicant_age` | 응답 | int 또는 null | A61 예 | 올해에서 출생연도를 뺀 값, 원본 출생연도 제외 |
| `items[].applicant_gender` | 응답 | string 또는 null | A61 예 | `male`·`female`, 작성자에게만 공개 |
| `items[].message` | 응답 | string 또는 null | A61 예 | 신청 메시지 |
| `items[].status` | 응답 | string | A61 예 | `pending`·`approved` |
| `items[].created_at` | 응답 | string(date-time) | A61 예 | 신청 시각 |

**A63·A64 만남 장소·A65 모집 글 종료 또는 취소**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `post_id` | path | string | A63·A64·A65 예 | `^cpo_[0-9A-Za-z]{6,26}$`, 모집 글 ID |
| `action` | path | string | A65 예 | `close`·`end`·`cancel` |
| `name` | body | string | A63 예 | 장소 이름 1~60자 |
| `address` | body | string | A63 선택 | 주소 |
| `lat` | body | number | A63 쌍으로 선택 | 위도 33~39, 경도와 함께 제공하거나 둘 다 생략 |
| `lng` | body | number | A63 쌍으로 선택 | 경도 124~132, 위도와 함께 제공하거나 둘 다 생략 |
| `guide` | body | string | A63 선택 | 만남 안내, 300자 이하 |
| `post_id` | 응답 | string | A63·A65 예 | 수정하거나 종료·취소한 모집 글 ID |
| `updated_at` | 응답 | string(date-time) | A63 및 A64 장소가 있으면 예 | 장소 최종 변경 시각 |
| `name` | 응답 | string | A64 장소가 있으면 예 | 장소 이름 |
| `address` | 응답 | string 또는 null | A64 장소가 있으면 예 | 주소 |
| `lat` | 응답 | number 또는 null | A64 장소가 있으면 예 | 위도, 텍스트 안내만 있으면 null |
| `lng` | 응답 | number 또는 null | A64 장소가 있으면 예 | 경도, 텍스트 안내만 있으면 null |
| `guide` | 응답 | string 또는 null | A64 장소가 있으면 예 | 만남 안내 |
| `status` | 응답 | string | A64 장소가 없으면 예·A65 예 | A64 미정이면 `undecided`, A65 완료면 `full`·`ended`·`cancelled` |

#### 7-2-5. 채팅 API (A66~A73 + WebSocket)

**동작 규칙** — A66~A73 및 WebSocket을 구현했습니다. `AUTH_PROVIDER=db`는 007·016·021_chat과 RLS를 사용하며 기본값은 모의입니다. 연결 표와 브로드캐스트는 단일 서버 메모리를 사용합니다. A69는 정의되지 않은 동작에 `404 NOT_FOUND`를 반환합니다. 실제 WebSocket 서버 실행과 연동 함수는 [채팅 구현 명세](../../backend/Doc/chat/SPEC.md)를 따릅니다.

정기 작업이 30일 지난 친구 채팅과 종료 72시간이 지난 동행방의 메시지 본문을 비우고 삭제 시각을 기록합니다. DB는 메시지 순서를 보존합니다.

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A66** `GET /api/v1/me/chat-rooms` | `filter`: `all`·`companion`·`friend`·`past` | `{items[] {room_id, room_type, name, status, last_message_at, unread_count, my_status}}` — 없으면 `items:[]` + `empty_hint`("동행을 찾거나 친구를 추가해 보세요", FR-COM20) | user, 내가 `invited`·`joined`인 방만(RLS) | 401 |
| **A67** `POST /api/v1/chat-rooms` | 1:1 `{type:"direct", friend_id}` / 단체 `{type:"friend_group", name(1~40), invitee_ids[2~19]}` | 201 `{room_id}` (열린 1:1 방이 이미 있으면 **200 + 기존 `room_id`**) | user. **실제 친구만**(`friendships`), 차단 관계 제외(FR-COM14·15). 차단 해제 뒤 닫힌 방은 재사용하지 않으며 새 대화에는 새 방 생성(DB 6-8). 단체방은 만든 사람이 방장, 나머지는 `invited` | 401 / 403 `NOT_FRIENDS`·`BLOCKED` / 422 |
| **A68** `POST /api/v1/chat-rooms/{room_id}/invitations` | `{invitee_ids[]}` | 200 | 단체방 **방장만**, 친구만, 동행방에는 초대 불가(FR-COM08). 초대 알림 | 401 / 403 / 409 |
| **A69** `POST /api/v1/chat-rooms/{room_id}/{action}` | `accept`·`decline`(초대받은 사람) / `leave`(멤버) | 200 `{room_id, my_status}` | `accept` 하면 그때부터(`joined_at`) 메시지가 보임 — **이전 메시지는 안 보임**(FR-COM16, T38f). 방장이 나가면 **가장 먼저 들어온 멤버가 방장**(FR-COM17). 동행방은 `leave` 대신 신청 취소·종료 흐름 | 401 / 403 / 404 `NOT_FOUND`(지원하지 않는 동작) / 409 |
| **A70** `PATCH /api/v1/chat-rooms/{room_id}` | `{name}` | 200 | 단체방 방장만(FR-COM17) | 401 / 403 / 422 |
| **A71** `GET /api/v1/chat-rooms/{room_id}/messages` | `after_seq`(재접속: 마지막으로 받은 순서 이후) · `before_seq`(위로 스크롤) · `limit`(≤100) | `{items[] {message_id, seq, sender_id, sender_display_name, msg_type, body, created_at}, has_more}` | `joined` 멤버만, **입장 뒤 메시지만**(RLS, T37g). 차단으로 닫힌 1:1 방의 메시지는 차단 해제 뒤에도 제공하지 않음. 최근 100개는 Redis에서, 없으면 DB(Redis 장애여도 DB로 답함). **Redis에서 읽어도 서버가 DB와 같은 규칙으로 거름**: 지금 `joined`인지, 내 `joined_at` 이후인지, 숨김(`deleted_at`) 아닌지, 차단한 사람 메시지인지. 메시지 숨김(A77)·보존 정리·방 종료 때 `chat:recent:{room_id}`에서도 지움 | 401 / 403 |
| **A72** `POST /api/v1/chat-rooms/{room_id}/read` | `{seq}` | 204 | 내 `last_read_seq`만 앞으로(뒤로 안 감) → `unread_count` | 401 / 403 |
| **A73** `POST /api/v1/ws-tickets` | `{}` | 201 `{ticket, expires_in: 30}` | user. 브라우저 WebSocket은 헤더를 못 붙이므로 **30초짜리 1회용 표**(Redis `ws:ticket:{hash}`)로 연결 | 401 |
| **WS** `GET /api/v1/ws/chat?ticket=…` | 아래 메시지 형식 | 아래 | 연결·구독·전송마다 **현재 멤버·입장 시각·차단·방 상태**를 다시 확인(5.20). 서버 여러 대면 Redis Pub/Sub `chat:{room_id}`로 전달하되 **Pub/Sub은 저장·수신 보장이 아님**(놓친 것은 A71로) | 연결 거부 4401(표 없음·만료) / 4403(권한) |

**A66 내 채팅방 목록**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `filter` | query | string | 아니요 | `all`·`companion`·`friend`·`past` |
| `items` | 응답 | array<object> | 예 | 내가 초대됐거나 입장한 채팅방 목록 |
| `items[].room_id` | 응답 | string | 예 | 채팅방 ID |
| `items[].room_type` | 응답 | string | 예 | `companion`·`direct`·`friend_group` |
| `items[].name` | 응답 | string 또는 null | 예 | 채팅방 이름, 단체방은 1~40자 |
| `items[].status` | 응답 | string | 예 | `active`·`read_only`·`closed` |
| `items[].last_message_at` | 응답 | string(date-time) 또는 null | 예 | 마지막 메시지 시각 |
| `items[].unread_count` | 응답 | int | 예 | 내가 아직 읽지 않은 메시지 수 |
| `items[].my_status` | 응답 | string | 예 | `invited`·`joined` |
| `empty_hint` | 응답 | string | 목록이 비면 예 | 동행을 찾거나 친구를 추가해 보세요 |

**A67 생성·A68 초대·A69 초대 처리 또는 퇴장·A70 이름 변경**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `type` | body | string | A67 예 | `direct`·`friend_group` |
| `friend_id` | body | string (UUID) | A67 1:1방 예 | 실제 친구의 사용자 ID |
| `name` | body | string | A67 단체방·A70 예 | 단체방 이름 1~40자 |
| `invitee_ids` | body | array<string (UUID)> | A67 단체방·A68 예 | 초대할 친구 ID, A67 단체방 생성 시 2~19명 |
| `room_id` | path | string | A68·A69·A70 예 | `^crm_[0-9A-Za-z]{6,26}$`, 대상 채팅방 ID |
| `action` | path | string | A69 예 | `accept`·`decline`은 초대받은 사람, `leave`는 멤버 |
| `room_id` | 응답 | string | A67·A69 예 | 생성하거나 상태가 바뀐 방 ID, 기존 1:1 방은 기존 ID |
| `my_status` | 응답 | string | A69 예 | 처리 후 `joined`·`declined`·`left` |

A68 초대와 A70 이름 변경의 성공 응답(200) 본문은 아래와 같습니다(`chat_members`·`chat_rooms` 컬럼 기준).

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `room_id` | 응답 | string | A68·A70 예 | 대상 방 ID |
| `invited` | 응답 | array<object> | A68 예 | 이번에 초대한 멤버. 항목마다 `user_id`(UUID)·`status`(`invited`)·`invited_at`(ISO 8601). 이미 멤버이거나 초대 중인 사람은 넣지 않음 |
| `name` | 응답 | string | A70 예 | 바뀐 방 이름 1~40자 |

**A71 메시지 이력·A72 읽음·A73 연결 표 발급**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `room_id` | path | string | A71·A72 예 | `^crm_[0-9A-Za-z]{6,26}$`, 대상 채팅방 ID |
| `after_seq` | query | int (64비트) | A71 선택 | 이 순번보다 새 메시지 조회 |
| `before_seq` | query | int (64비트) | A71 선택 | 이 순번보다 이전 메시지 조회 |
| `limit` | query | int | A71 선택 | 최대 100건 |
| `seq` | body | int (64비트) | A72 예 | 읽은 마지막 방별 순번, 기존 읽음 위치보다 앞선 값만 반영 |
| `items` | 응답 | array<object> | A71 예 | 입장 후 열람 가능한 메시지 목록 |
| `items[].message_id` | 응답 | int (64비트) | A71 예 | `chat_messages.message_id` |
| `items[].seq` | 응답 | int (64비트) | A71 예 | 방별 메시지 순번 |
| `items[].sender_id` | 응답 | string (UUID) 또는 null | A71 예 | 발신자 ID, 시스템 메시지는 null |
| `items[].sender_display_name` | 응답 | string 또는 null | A71 예 | 발신자 닉네임(`app_public_display_name`) |
| `items[].msg_type` | 응답 | string | A71 예 | `text`·`system` |
| `items[].body` | 응답 | string | A71 예 | 숨김 처리되지 않은 메시지 본문, 1~1000자 |
| `items[].created_at` | 응답 | string(date-time) | A71 예 | 저장 시각 |
| `has_more` | 응답 | boolean | A71 예 | 조회한 방향에 메시지가 더 있는지 표시 |
| `ticket` | 응답 | string | A73 예 | WebSocket 연결에 쓰는 1회용 표, 요청 본문은 빈 객체 |
| `expires_in` | 응답 | int | A73 예 | 연결 표 유효 시간(초), 30 |

**WebSocket 메시지 (JSON 한 줄씩)**

| 방향 | `type` | 내용 |
|---|---|---|
| 앱 → 서버 | `subscribe` | `{room_id, after_seq}` — 그 뒤 메시지를 먼저 보내 주고 실시간으로 이어 감 |
| 앱 → 서버 | `send` | `{room_id, client_message_id(8~64, 앱이 만든 UUID), body(1~1000)}` |
| 서버 → 앱 | `ack` | `{client_message_id, message_id, seq}` — **DB 저장(commit) 뒤에만** 보냄. 저장 실패면 `error`(완료 아님) |
| 서버 → 앱 | `message` | `{room_id, message_id, seq, sender_id, msg_type, body, created_at}` |
| 서버 → 앱 | `error` | `{code: FORBIDDEN·ROOM_READ_ONLY·RATE_LIMITED·VALIDATION_ERROR·STORE_FAILED, client_message_id?}` |
| 서버 → 앱 | `room_status` | `{room_id, status: read_only·closed}` (동행 종료 등) |
| 서버 → 앱 | `notification` | `{notification_id, type, ref_type, ref_id, created_at}` — A74와 같은 내용(앱 안 알림) |
| 서버 → 앱 | `unsubscribed` | `{room_id, reason: left·removed·blocked·deleted}` — **멤버 상태가 바뀌면(나가기·내보내기·차단·탈퇴) 서버가 그 방 구독을 즉시 끊고** 이후 `message`를 보내지 않음 |

**WS 연결 쿼리와 메시지 종류별 필드**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `ticket` | query | string | 예 | A73에서 받은 1회용 연결 표 |
| `type` | body | string | 예 | 앱 → 서버 이벤트 종류 `subscribe`·`send` |
| `room_id` | body | string | 예 | 구독하거나 전송할 채팅방 ID, `crm_…` |
| `after_seq` | body | int (64비트) | `subscribe` 예 | 재수신 기준이 되는 마지막 방별 순번 |
| `client_message_id` | body | string | `send` 예 | 앱에서 만든 UUID, 8~64자, 재전송 시 같은 값 사용 |
| `body` | body | string | `send` 예 | 텍스트 본문 1~1000자 |
| `type` | 응답 | string | 예 | 서버 → 앱 이벤트 종류 `ack`·`message`·`error`·`room_status`·`notification`·`unsubscribed` |
| `room_id` | 응답 | string | `message`·`room_status`·`unsubscribed` 예 | 메시지·상태 변경·구독 해제 대상 채팅방 ID |
| `client_message_id` | 응답 | string | `ack` 예, `error` 선택 | 대응하는 앱 전송 ID |
| `message_id` | 응답 | int (64비트) | `ack`·`message` 예 | DB에 저장된 메시지 ID |
| `seq` | 응답 | int (64비트) | `ack`·`message` 예 | 저장 시 발급된 방별 순번 |
| `sender_id` | 응답 | string (UUID) 또는 null | `message` 예 | 발신자 ID, 시스템 메시지는 null |
| `msg_type` | 응답 | string | `message` 예 | `text`·`system` |
| `body` | 응답 | string | `message` 예 | 메시지 본문 1~1000자 |
| `created_at` | 응답 | string(date-time) | `message`·`notification` 예 | 메시지 또는 알림 생성 시각 |
| `code` | 응답 | string | `error` 예 | `FORBIDDEN`·`ROOM_READ_ONLY`·`RATE_LIMITED`·`VALIDATION_ERROR`·`STORE_FAILED` |
| `status` | 응답 | string | `room_status` 예 | `read_only`·`closed` |
| `notification_id` | 응답 | int (64비트) | `notification` 예 | A74의 알림 ID |
| `type` | 응답 | string | `notification` 내용에 예 | A74의 알림 유형(이벤트 종류 `notification`과 구분) |
| `ref_type` | 응답 | string | `notification` 예 | A74의 알림 참조 유형 |
| `ref_id` | 응답 | string | `notification` 예 | A74의 알림 참조 ID |
| `reason` | 응답 | string | `unsubscribed` 예 | `left`·`removed`·`blocked`·`deleted` |

이벤트 종류와 알림 내용의 `type`은 위 메시지 표의 두 항목을 각각 가리킵니다.

- **전송 처리 순서:** ① 멤버·차단·방 상태 확인 → ② 한 트랜잭션에서 `chat_rooms.last_seq + 1`로 순서 발급 + `chat_messages` 저장 → ③ commit 성공 뒤 `ack` → ④ Redis 최근 메시지 갱신·Pub/Sub 발행. 같은 `client_message_id` 재전송은 DB UNIQUE(T38b)로 **처음 저장된 메시지의 `ack`를 다시** 보냄(중복 저장 없음). Redis 실패는 전송 성공에 영향 없음(읽을 때 DB로).
- 전송 제한: 사람당 초당 5개·방당 초당 20개(초기값, 8-4). 사용자 대화는 AI·RAG에 넣지 않음(5.20).

#### 7-2-6. 알림·신고·마이페이지·탈퇴·비밀번호 변경 (A74~A80·A82)

**동작 규칙** — A74·A75를 구현했습니다. 본인의 알림을 조회하고 읽음 처리합니다. WebSocket은 `{"type":"notification","notification":{...}}`으로 새 알림을 전달합니다.

**동작 규칙** — A74·A75에 동행 신청·승인, 친구 신청·수락, 채팅 초대 알림을 연결했습니다. A76은 접수 시 대상 권한과 KST 날짜 기준 중복을 확인합니다. A77은 `operator`·`admin`이 서비스 계정으로 조회·처리합니다. 첫 상세 조회에서 `reviewing`으로 전환하며, 바로 처리하면 같은 트랜잭션에서 `reviewing`을 거칩니다. 채팅 신고 상세는 신고 사유를 열람 이유로 기록한 뒤 응답합니다. `block_user`는 일반 사용자 계정만 `disabled`로 전환합니다. A78은 A32와 같은 닉네임 검증을 사용합니다.

**마이페이지 API** — 관심 축제(A11~A13), 축제 취향(A36·A37), 본인 프로필(A78), 내 동행 내역(A79), 탈퇴(A80), 비밀번호 변경(A82)을 제공합니다. 필수 범위는 비밀번호 변경·탈퇴·관심 축제이고, A36·A37·A78·A79는 함께 제공하되 화면에 넣을지는 화면 담당이 정합니다. `AUTH_PROVIDER=db`에서 실제 DB, 기본은 모의 모드이며 모의 동행 내역은 빈 배열입니다. 운영 공지·이용약관은 고정 문서 링크를 사용합니다.

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A74** `GET /api/v1/me/notifications` | `unread_only`·`page` | `{items[] {notification_id, type, ref_type, ref_id, created_at, read_at}, unread_count}` | user, 본인 것만(RLS, T39c). **앱 안 알림만**(외부 푸시는 범위 밖, FR-COM21). 화면은 WebSocket 연결 중이면 `notification` 이벤트로도 받음 | 401 |
| **A75** `POST /api/v1/me/notifications/read` | `{ids[]}` 또는 `{all: true}` | 204 | 읽음 칸만 바꿈(T39a·b) | 401 |
| **A76** `POST /api/v1/reports` | `{target_type: companion_post·chat_message·chat_room·user, target_id, reason(6종), detail?}` | 201 `{report_id}` | user. 같은 대상은 신고자당 KST 날짜 기준 하루 1회(8-4 ⑧). 방 신고는 현재 입장한 멤버, 메시지 신고는 해당 메시지 열람 권한이 있는 멤버만 접수. 신고자는 자기 신고만 봄(T40d) | 400 `VALIDATION_ERROR`(본인 계정 신고) / 401 / 404 / 409 |
| **A77** `GET`·`POST /api/v1/admin/reports` | GET 목록 `status`·`page`, 상세 `report_id` / POST `{report_id, action: dismiss·hide_message·hide_post·close_room·block_user, note}` (`close_room` = 신고된 채팅방을 `read_only`로) | 200 | operator·admin. 관리자 열람 범위는 **신고된 메시지만**입니다: 메시지 신고(`chat_message`)는 그 메시지 1건만 보여 주고, 방 신고(`chat_room`)는 메시지 원문을 열지 않고 방 정보·신고 사유만 보고 처리(`close_room` 등)합니다. 채팅 신고 상세를 열람할 때마다 **`chat_admin_access`에 이유와 함께 기록한 뒤** 보여 줌(기록은 수정·삭제 불가 T40c). 서버의 열람 범위 검사와 시험은 8-2-2절에 연결. 메시지 숨김은 `chat_messages.deleted_at`으로 처리하고 다음 이력 조회에서 제외, 글 숨김은 `companion_posts.hidden_at`·`hidden_by`(마이그레이션 008, T42d~f — 작성자 외에는 안 보임). `block_user`는 대상의 `profiles.role='user'`일 때만 가능 | 401 / 403 `FORBIDDEN`(운영자·관리자 계정 정지 거부) / 404 |
| **A78** `GET`·`PATCH /api/v1/me/profile` | PATCH `{display_name?}` (A32와 같은 닉네임 규칙으로 변경) | `{user_id, display_name, birth_year, gender, onboarding_status}` (출생연도·성별은 본인 화면용. 다른 사람에게는 **동행 신청 때 그 글 작성자에게만 나이·성별**이 보임 — A61) | user, 본인만. 이메일·전화번호·나이·성별은 다른 사람에게 보이지 않음(FR-COM22) | 401 / 409 `NICKNAME_TAKEN` / 422 |
| **A79** `GET /api/v1/me/companion-activity` | `type`: `posts`·`applications` | 200 `{items[]}`, 조회 유형별 항목 필드는 아래 A79 표 | user, 본인 내역(작성 글 또는 보낸 신청), 생성 최신순 | 401 / 422 |
| **A80** `DELETE /api/v1/me` (탈퇴) | `{password}` 재확인 | 204 | user. **DB 한 트랜잭션**(DB 설계서 7-0 ②): Refresh 토큰·관심·취향·알림·친구 신청·관계·차단 행 삭제, 진행 중 동행 글·신청 취소, 채팅방 퇴장과 방장 승계, 챗봇 질문·답변·방문 코스 결과 삭제, 프로필 개인정보 NULL, 계정 이메일·비밀번호 해시 덮어쓰기와 `status='deleted'`. 같은 DB에 LangGraph 체크포인트 테이블이 있으면 본인 대화 상태도 함께 삭제. 커밋 뒤 현재 Access의 `jti`를 폐기하며 모든 기기의 Access는 계정 상태 검사에서 거부(커밋 뒤 폐기 저장소가 응답하지 않아도 탈퇴는 유지하고 204 — 계정 상태 검사가 막음). 열린 WebSocket은 세션 재확인(1초 주기) 때 구독 해지(`unsubscribed`, `reason:"deleted"`) 뒤 4403으로 닫힘. 메시지는 화면에서 작성자 ‘알 수 없음’으로 표시하고 본문은 방 보존 정책을 따름. 커밋 뒤 DB 밖 탈퇴 기록(`WITHDRAWAL_LOG_PATH`, user_id·시각만)에 한 줄 추가 — 백업에서 복원하면 이 기록으로 다시 정리(DB 설계서 7-0 ⑥) | 401 / 403 `PASSWORD_MISMATCH` / 422 / 503 `AUTH_CHECK_UNAVAILABLE`(요청 시작 때 인증 확인 불가) |
| **A82** `POST /api/v1/me/password` (비밀번호 변경) | `{current_password, new_password}` | 204 | user. 새 비밀번호는 A32와 같은 규칙(영문·숫자 포함 8~64자), 현재 비밀번호와 같으면 거부. **DB 한 트랜잭션**: `users` 행 잠금 → 현재 비밀번호 확인 → `password_hash`를 Argon2id 새 해시로 교체 → 그 계정의 모든 `refresh_tokens.revoked_at` 기록. 커밋 뒤 현재 Access의 `jti` 폐기(이 기기 즉시 로그아웃, 열린 WebSocket도 다음 재확인 때 4403). **다른 기기의 Access는 남은 수명(기본 30분, `ACCESS_JWT_TTL_MIN`, 8-4) 동안 쓸 수 있고** 갱신은 거부됨 → 새 비밀번호로 다시 로그인. 세션이 끝나는 범위는 모의 모드도 같음(폐기된 Refresh를 다시 보내면 DB 모드는 401 `REFRESH_REUSED`, 모의 모드는 401 `REFRESH_INVALID`). 커밋 뒤 폐기 저장소가 응답하지 않으면 변경은 유지하고 204(현재 Access도 만료까지 유효, 서버 경고 기록) | 401 / 403 `PASSWORD_MISMATCH` / 422 `VALIDATION_ERROR` / 503 `AUTH_CHECK_UNAVAILABLE`(요청 시작 때 인증 확인 불가) |

**A74 알림 목록·A75 읽음 처리**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `unread_only` | query | boolean | A74 선택 | 읽지 않은 알림만 조회 |
| `page` | query | int | A74 선택 | 조회할 페이지 번호 |
| `items` | 응답 | array<object> | A74 예 | 본인에게 온 앱 안 알림 |
| `items[].notification_id` | 응답 | int (64비트) | A74 예 | 알림 ID |
| `items[].type` | 응답 | string | A74 예 | `companion_applied`·`companion_approved`·`companion_rejected`·`companion_ended`·`companion_cancelled`·`meeting_place_changed`·`friend_requested`·`friend_accepted`·`room_invited` |
| `items[].ref_type` | 응답 | string | A74 예 | `companion_post`·`companion_application`·`friend_request`·`chat_room` |
| `items[].ref_id` | 응답 | string | A74 예 | 참조 대상 ID |
| `items[].created_at` | 응답 | string(date-time) | A74 예 | 알림 생성 시각 |
| `items[].read_at` | 응답 | string(date-time) 또는 null | A74 예 | 읽음 시각, 읽기 전에는 null |
| `unread_count` | 응답 | int | A74 예 | 본인의 읽지 않은 알림 수 |
| `ids` | body | array<int (64비트)> | A75 일부 처리 시 예 | 읽음으로 표시할 본인 알림 ID |
| `all` | body | boolean | A75 전체 처리 시 예 | `true`면 본인 알림 전체를 읽음 처리. 본문은 `ids` 또는 `all: true` |

**A76 신고 등록·A77 관리자 신고 조회·처리 요청**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `target_type` | body | string | A76 예 | `companion_post`·`chat_message`·`chat_room`·`user` |
| `target_id` | body | string | A76 예 | `reports.target_id`, 선택한 유형의 신고 대상 ID |
| `reason` | body | string | A76 예 | `spam`·`abuse`·`harassment`·`fraud`·`privacy`·`other` |
| `detail` | body | string | A76 선택 | 신고 상세, 500자 이하 |
| `report_id` | 응답 | string | A76 예 | 생성한 신고 ID(`rpt_…`) |
| `status` | query | string | A77 GET 목록 선택 | `received`·`reviewing`·`actioned`·`dismissed` |
| `page` | query | int | A77 GET 목록 선택 | 조회할 페이지 번호 |
| `report_id` | query | string | A77 GET 상세 필수 | `^rpt_[0-9A-Za-z]{6,26}$`, 상세 조회할 신고 ID |
| `report_id` | body | string | A77 POST 예 | `^rpt_[0-9A-Za-z]{6,26}$`, 처리할 신고 ID |
| `action` | body | string | A77 POST 예 | `dismiss`·`hide_message`·`hide_post`·`close_room`·`block_user` |
| `note` | body | string | A77 POST 예 | 관리자 처리 메모 |

**A77 조회에서 열람하는 대상별 데이터 (DDL 컬럼 기준)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `reason` | 응답 | string | 채팅방 신고 열람 | 신고 사유, `reports.reason`의 6개 값(A76) |
| `room_id` | 응답 | string | 채팅방 신고 열람 | 신고된 방 ID |
| `room_type` | 응답 | string | 채팅방 신고 열람 | `companion`·`direct`·`friend_group` |
| `name` | 응답 | string 또는 null | 채팅방 신고 열람 | 방 이름 |
| `status` | 응답 | string | 채팅방 신고 열람 | `active`·`read_only`·`closed` |
| `message_id` | 응답 | int (64비트) | 메시지 신고 열람 | 신고된 메시지 한 건의 ID |
| `body` | 응답 | string 또는 null | 메시지 신고 열람 | 신고된 메시지 한 건의 본문 |

A77 목록과 상세는 같은 GET 경로를 사용합니다. `status`·`page`는 목록에 적용하고, `report_id`로 상세 한 건을 조회합니다. 채팅 신고 상세를 열람할 때마다 `chat_admin_access`에 관리자·방·신고·사유를 먼저 기록합니다.

| 필드 | 응답 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `items` | GET 목록 | array<object> | 예 | 신고 요약 목록. 각 항목은 아래 `report` 필드를 사용. 0건이면 빈 배열 |
| `page` | GET 목록 | int | 예 | 반환한 페이지 번호 |
| `report` | GET 상세 | object | 예 | `report_id`·`target_type`(`companion_post`·`chat_message`·`chat_room`·`user`)·`target_id`·`reason`·`status`(`received`·`reviewing`·`actioned`·`dismissed`)·`created_at` |
| `room` | GET 상세 | object 또는 null | 예 | 채팅 신고에는 `room_id`·`room_type`·`name`·`status`. 동행 글·사용자 신고는 `null` |
| `message` | GET 상세 | object 또는 null | 예 | `chat_message`의 신고된 한 건만 `message_id`·`seq`·`sender_id`·`body`·`created_at`을 반환. 나머지는 `null` |
| `access_id` | GET 상세 | int (64비트) 또는 null | 예 | 이번 채팅 열람 기록의 ID(`chat_admin_access.access_id`, BIGSERIAL). 동행 글·사용자 신고는 `null` |
| `report_id`·`status`·`handled_by`·`handled_at` | POST 처리 | object | 예 | 처리 결과. `handled_by`는 관리자 `user_id` |

**A78 본인 프로필 조회·수정**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `display_name` | body | string | PATCH 선택 | 제어문자 없이 앞뒤 공백 제거 후 2~12자. 정규화한 닉네임으로 대소문자 무시 중복 검사(009) |
| `user_id` | 응답 | string (UUID) | 예 | 본인 사용자 ID |
| `display_name` | 응답 | string 또는 null | 예 | 본인 닉네임 |
| `birth_year` | 응답 | int 또는 null | 예 | 본인 출생연도, 009 저장 범위 1900~2100(A32 가입은 1900~올해) |
| `gender` | 응답 | string 또는 null | 예 | 본인 성별, `male`·`female` |
| `onboarding_status` | 응답 | string | 예 | A36의 `pending`·`completed`·`skipped` |

**A79 내 동행 내역 요청·유형별 응답**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `type` | query | string | 예 | `posts`는 내가 작성한 모집 글, `applications`는 내가 보낸 동행 신청 |
| `items` | 응답 | array<object> | 예 | A57·A61과 같은 목록 형식. 선택한 유형의 본인 내역을 아래 항목 구조로 반환 |

**A79 type=posts 항목 (A57 글 필드와 companion_posts)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `items[].post_id` | 응답 | string | 예 | 내 모집 글 ID |
| `items[].festival_id` | 응답 | string | 예 | 모집 대상 축제 ID |
| `items[].meet_at` | 응답 | string(date-time) | 예 | 만남 시각 |
| `items[].capacity` | 응답 | int | 예 | 모집 정원(작성자 제외 1~10명) |
| `items[].approved_count` | 응답 | int | 예 | 승인 인원, 0 이상 정원 이하 |
| `items[].age_pref` | 응답 | string 또는 null | 예 | A58의 연령대 조건 |
| `items[].gender_pref` | 응답 | string | 예 | A58의 성별 조건 |
| `items[].memo` | 응답 | string 또는 null | 예 | 모집 안내, 500자 이하 |
| `items[].status` | 응답 | string | 예 | `open`·`full`·`ended`·`cancelled` |

**A79 type=applications 항목 (A60~A62와 companion_applications)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `items[].application_id` | 응답 | string | 예 | 내 신청 ID |
| `items[].post_id` | 응답 | string | 예 | 신청한 모집 글 ID |
| `items[].message` | 응답 | string 또는 null | 예 | 내가 보낸 신청 메시지, 200자 이하 |
| `items[].status` | 응답 | string | 예 | `pending`·`approved`·`rejected`·`cancelled` |
| `items[].created_at` | 응답 | string(date-time) | 예 | 신청 시각 |

**A80 탈퇴 요청 (204)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `password` | body | string | 예 | 탈퇴 전 본인 계정의 비밀번호 재확인 |

**A82 비밀번호 변경 요청 (204)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `current_password` | body | string (SecretStr) | 예 | 지금 쓰는 비밀번호. 틀리면 403 `PASSWORD_MISMATCH`(A80과 같은 코드) |
| `new_password` | body | string (SecretStr) | 예 | 영문·숫자를 포함한 8~64자(A32 규칙). `current_password`와 같으면 422. 다른 필드가 있으면 422 |
| `Authorization` | header | string | 예 | `Bearer` Access 토큰. 성공 뒤 이 토큰은 바로 쓸 수 없음 |

### 7-3. AI 방문 코스·공지 관리·축제 관리

#### A51. AI 방문 코스 만들기 `POST /api/v1/assistant/visit-course` (FR-P01·P03, Must 최종)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 고른 축제에서 **무엇을 어떤 순서로 할지** 동행 유형·시간에 맞춰 코스를 만듦(맞춤 추천 A38은 '어느 축제를 갈지', A51은 '그 축제에서 무엇을 할지'). 화면 `assistant/` 방문 코스, API `assistant/chatbot.py`, 에이전트 Festival |
| 2 | 요청 헤더 | A06과 같음 (`Authorization` 선택) |
| 3 | 경로·쿼리 | 없음 |
| 4 | 요청 본문 | `{request_id(8~64), festival_id, companion: family_relaxed·friends_activity·couple_photo·pet·solo, start_at(축제 기간 안 ISO 시각), duration_min: 60~480, constraints: {wheelchair}}` |
| 5 | 검증·권한 | 형식 422 → 축제 없음 404 → `start_at`이 축제 기간 밖이면 400 `COURSE_OUT_OF_PERIOD` → 요청 수 제한 429(A06과 같은 한도) → 같은 `request_id`는 처음 `run_id`(멱등) |
| 6 | 정상 응답 | **202** `{run_id, run_kind:"visit_course", run_status:"queued", status_url, events_url, run_access_token}` — A06과 같은 작업 방식, 결과는 **A06-1**(`result`)·진행은 **A06-2**로 |
| 7 | 오류 응답 | 400 `COURSE_OUT_OF_PERIOD` / 404 `FESTIVAL_NOT_FOUND` / 409 `IDEMPOTENCY_CONFLICT` / 422 / 429 / 503 `AI_AGENT_FAILED` |
| 8 | 실행 규칙 | 워커의 Festival 에이전트가 `get_festival`·`get_facilities`·`get_official_notices`·`get_crowd`만 써서 후보를 고르고, **코드가 검증한 뒤** 결과를 저장(아래). 전체 제한 30초·재시도 1회(A06과 같음, 8-4) |

**A51 방문 코스 요청·접수 응답 (202)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `request_id` | body | string | 예 | 8~64자, 같은 요청 재전송 시 기존 작업 사용 |
| `festival_id` | body | string | 예 | 방문할 축제 ID |
| `companion` | body | string | 예 | `family_relaxed`·`friends_activity`·`couple_photo`·`pet`·`solo` |
| `start_at` | body | string(date-time) | 예 | 축제 기간 안의 시작 시각 |
| `duration_min` | body | int | 예 | 60~480분 |
| `constraints` | body | object | 예 | 이동 제약 |
| `constraints.wheelchair` | body | boolean | 예 | 휠체어 이용 조건 |
| `run_id` | 응답 | string | 예 | 등록된 코스 작업 ID |
| `run_kind` | 응답 | string | 예 | `visit_course` |
| `run_status` | 응답 | string | 예 | `queued` |
| `status_url` | 응답 | string | 예 | A06-1 상태·코스 결과 조회 경로 |
| `events_url` | 응답 | string | 예 | A06-2 진행 이벤트 구독 경로 |
| `run_access_token` | 응답 | string | 예 | 비로그인 작업 조회에 쓰는 토큰 |

**코스 검증 규칙 (FR-P03 — 실존·운영 시각·동선)**

| 검증 | 통과 조건 | 못 통과하면 |
|---|---|---|
| 실제 장소 | 모든 지점이 `festival_id`(축제 프로그램·장소) 또는 `facilities.facility_id`, 또는 카카오 장소 검색 결과의 장소 ID | 그 지점을 빼고 `unverified[]`에 "확인할 수 없는 장소"로 |
| 날짜·운영 시각 | 지점 시간이 축제 기간 안이고, 운영 시각(`playtime`·시설 개방 시간)이 있으면 그 안 | 운영 시각 정보가 없으면 `verified:false` + "운영 시간 확인 필요" |
| 동선 | 지점 사이 직선거리 ÷ 걸음 속도(분당 67m, 초기값)로 이동 시간을 **추정**하고 합계가 `duration_min` 안 | 넘으면 뒤쪽 지점부터 뺌. 이동 시간은 '추정'으로 표시(길찾기 API는 쓰지 않음) |
| 조건 | `companion=pet`이면 `pet_allowed` 검증 태그, `wheelchair`는 검증된 시설 정보가 있을 때만 "가능"으로 | 근거 없으면 `constraint_status: not_verifiable`(추측 금지, FR-REC09·R10과 같음) |
| 저장 | `assistant_runs.result`(마이그레이션 006, 시험 T34)에 **장소 ID·순서·시간·검증 여부만** 저장. 카카오 장소의 이름·좌표는 **저장 불가(카카오 공식 답변)**라 저장하지 않고, 화면이 결과를 열 때 **지점 좌표 주변 카카오 장소 검색을 실시간으로 다시 불러** 이름을 보여 줌(장소 ID 단건 조회 API는 없음) | — |

```json
{ "run_id": "run_01JDC1…", "run_kind": "visit_course", "run_status": "succeeded", "answer": "가족과 2시간 코스를 만들었어요. 운영 시간이 확인 안 된 곳이 1곳 있어요.",
  "result": { "festival_id": "fst_01JD7Z…", "companion": "family_relaxed", "start_at": "2026-11-21T15:00:00+09:00", "duration_min": 120,
              "stops": [ { "order": 1, "type": "festival", "ref_id": "fst_01JD7Z…", "name": "어린이 만들기 체험", "start": "15:00", "end": "15:40", "reason_tag": "family_program", "verified": true },
                         { "order": 2, "type": "facility", "ref_id": "fac_…", "name": "공중화장실", "start": "15:45", "end": "15:50", "verified": true },
                         { "order": 3, "type": "place", "ref_id": "kakao:12345678", "name": null, "start": "16:00", "end": "16:50", "verified": false, "note": "운영 시간 확인 필요" } ],
              "walk_min_estimated": 14, "constraint_status": { "pet": "not_verifiable" }, "unverified": [ "운영 시간 확인 필요: 3번" ] },
  "is_mock": true }
```

**A51 결과 필드 (A06-1의 result, 코스 작업 성공 시)**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `result` | 응답 | object | 예 | 완성된 방문 코스 |
| `result.festival_id` | 응답 | string | 예 | 코스를 만든 축제 ID |
| `result.companion` | 응답 | string | 예 | 적용한 동행 유형(요청과 같은 값) |
| `result.start_at` | 응답 | string(date-time) | 예 | 코스 시작 시각 |
| `result.duration_min` | 응답 | int | 예 | 요청한 코스 시간(분) |
| `result.stops` | 응답 | array<object> | 예 | 검증한 코스 지점 목록 |
| `result.stops[].order` | 응답 | int | 예 | 코스 내 방문 순서 |
| `result.stops[].type` | 응답 | string | 예 | `festival`·`facility`·`place` |
| `result.stops[].ref_id` | 응답 | string | 예 | 축제·시설·카카오 장소 ID |
| `result.stops[].name` | 응답 | string 또는 null | 예 | 화면 표시용 이름, 예시의 카카오 장소명은 null |
| `result.stops[].start` | 응답 | string(time) | 예 | 예시의 `HH:mm` 형식 방문 시작 시각 |
| `result.stops[].end` | 응답 | string(time) | 예 | 예시의 `HH:mm` 형식 방문 종료 시각 |
| `result.stops[].reason_tag` | 응답 | string | 아니요 | 지점 선정 태그, 예: `family_program` |
| `result.stops[].verified` | 응답 | boolean | 예 | 지점 검증 여부 |
| `result.stops[].note` | 응답 | string | 아니요 | 운영 시간 등 추가 확인 안내 |
| `result.walk_min_estimated` | 응답 | int | 예 | 지점 사이 도보 이동 시간 추정치(분) |
| `result.constraint_status` | 응답 | object | 예 | 조건별 확인 결과, 근거가 없으면 `not_verifiable` |
| `result.unverified` | 응답 | array<string> | 예 | 확인할 수 없는 장소·운영 시간 안내 |

- 코스 수정·재추천(FR-P02)은 Should라 이번 범위 밖입니다(같은 요청을 조건만 바꿔 새로 보내면 됨).

#### A52~A54. 공식 공지 관리 (FR-O06 등록·수정, FR-D05 승인 — 둘 다 "적용 시" Must)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A52** `POST /api/v1/admin/notices` | `{festival_id?, type(5종, A07), title(1~200), content, effective_from, effective_to, source_url}` | 201 `{notice_id, approval_status:"pending"}` | operator·admin. 등록만으로는 **공개·경로 차단에 쓰지 않음**(승인 전 `pending`, RLS로 공개 조회 안 됨 — T35e). `notice_events`에 `create` 1줄 | 401 / 403 / 404(축제) / 422 |
| **A53** `PATCH /api/v1/admin/notices/{notice_id}` | 바꿀 칸만 | 200 `{notice_id, approval_status}` | operator·admin. 승인·반려 공지를 고치면 **다시 `pending`**(재승인 필요). 바뀌기 전·후 값을 `notice_events`(`update`)에 | 401 / 403 / 404 / 422 |
| **A54** `POST /api/v1/admin/notices/{notice_id}/review` | `{decision: "approve"·"reject", reason}` (반려는 이유 필수 — DB도 거부, T35b) | 200 `{notice_id, approval_status, control_version}` | operator·admin. **등록한 사람과 다른 검토자 권장**(2인 확인, 팀 인원상 필수는 아님). 승인되면 `control_version`이 바뀌어 그 축제의 경로 캐시를 무효화(04 문서 7절) → 귀가 경로가 통제를 반영(FR-R06·R09) | 401 / 403 / 404 / 409 `ALREADY_REVIEWED` / 422 |
| **수동 종료** `POST /api/v1/admin/notices/{notice_id}/end` | 본문 생략 또는 `{reason?}` | 200 `{notice_id, approval_status, control_version}` | operator·admin. 승인된 공지의 효력을 즉시 종료하고 `end` 이력을 남깁니다. 승인 상태를 유지하며 A07은 `active_only=false`에서 종료 공지를 반환합니다. | 401 / 403 / 404 / 409 `NOTICE_NOT_APPROVED`·`ALREADY_ENDED` / 422 |

**A52 공지 등록·A53 수정·A54 승인/반려 요청**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `notice_id` | path | string | A53·A54·수동 종료 예 | 수정·검토·종료할 공지 ID |
| `festival_id` | body | string | A52·A53 선택 | 관련 축제 ID, 공통 공지는 생략 가능 |
| `type` | body | string | A52 예·A53 선택 | `operation`·`traffic_control`·`no_stop`·`bus_detour`·`road_closure` |
| `title` | body | string | A52 예·A53 선택 | 제목 1~200자 |
| `content` | body | string | A52 예·A53 선택 | 공지 내용 |
| `effective_from` | body | string(date-time) | A52 예·A53 선택 | 시간대가 포함된 효력 시작 시각 |
| `effective_to` | body | string(date-time) | A52 예·A53 선택 | 시간대가 포함된 효력 종료 시각, 시작보다 뒤 |
| `source_url` | body | string | A52 예·A53 선택 | HTTP(S) 출처 URL |
| `decision` | body | string | A54 예 | `approve`·`reject` |
| `reason` | body | string | A54 반려 시 예 | 검토 또는 수동 종료 사유, `notice_events.reason` 300자 이하 |

**A52 등록(201)·A53 수정(200)·A54 검토 및 수동 종료(200) 응답**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `notice_id` | 응답 | string | 예 | 등록·수정·검토한 공지 ID |
| `approval_status` | 응답 | string | 예 | `pending`·`approved`·`rejected`. 등록과 승인 공지 수정 후 `pending`, 검토 후 `approved` 또는 `rejected` |
| `control_version` | 응답 | string 또는 null | A54·수동 종료 예 | 승인·종료 시 갱신하는 경로 통제 버전, 반려는 null |

- 이력(`notice_events`)은 추가만 가능하고 수정·삭제할 수 없습니다(트리거, T35c). AI가 공지를 구조화하는 기능(FR-D04·O07)은 Should라 범위 밖 — 들어오면 같은 승인 흐름을 탑니다.

**동작 규칙** — `admin/notices.py`의 운영자·관리자 API가 006·023을 사용합니다. 승인, 승인 공지 재검토, 수동 종료, 효력 시작·종료에 맞춰 축제별 버전을 변경합니다. 공통 공지는 모든 축제에서 조회하고 버전에 반영합니다. [공식 공지 구현 문서](../../backend/Doc/notice/SPEC.md)

#### A55~A56. 축제 직접 등록·수정 (FR-D12·O10 관리자 보완·승인)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A55** `POST /api/v1/admin/festivals` | A03 필드(이름·기간·장소·좌표·지역 필수) + `reason` | 201 `{festival_id, review_status:"pending"}` | admin. 공급원에 없는 축제를 직접 넣을 때. `data_sources`의 `admin_manual` 출처로 기록, 게시는 A56으로 | 401 / 403 / 409 `DUPLICATE_FESTIVAL`(이름·기간·장소가 같은 축제가 있으면 A24 검토 대기열로) / 422 |
| **A56** `PATCH /api/v1/admin/festivals/{festival_id}` | 바꿀 칸 + `reason`, 게시 여부 `published: bool` | 200 `{festival_id, review_status, published_at}` | admin. 칸마다 바뀌기 전·후 값을 `festival_change_history`(`actor='admin'`)에. 공급원 재수집이 관리자 수정을 덮지 않음(바뀐 칸은 A24 충돌 대기열 — FR-D14). 삭제 대신 `review_status='hidden'`(FR-D10) | 401 / 403 / 404 / 422 |

**A55 직접 등록·A56 수정/게시 요청**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `festival_id` | path | string | A56 예 | 수정하거나 게시할 축제 ID |
| `name` | body | string | A55 예·A56 선택 | 축제 이름(`festivals.title`) |
| `region_code` | body | string | A55 예·A56 선택 | 시·도 코드, 2-1절 |
| `start_date` | body | string(date) | A55 예·A56 선택 | 축제 시작일 |
| `end_date` | body | string(date) | A55 예·A56 선택 | 축제 종료일 |
| `venue_name` | body | string | A55 예·A56 선택 | 축제 장소 |
| `lat` | body | number | A55 예·A56 선택 | 위도 33~39(`festivals.latitude`) |
| `lng` | body | number | A55 예·A56 선택 | 경도 124~132(`festivals.longitude`) |
| `address` | body | string | 선택 | 축제 주소 |
| `overview` | body | string | 선택 | 축제 소개 |
| `fee_text` | body | string | 선택 | 입장료 안내(`admission_fee_text`) |
| `homepage_url` | body | string | 선택 | 축제 홈페이지(`official_url`) |
| `event_status` | body | string | 선택 | `upcoming`·`ongoing`·`ended`·`cancelled`·`needs_review` |
| `image_url` | body | string | 선택 | 대표 이미지 URL |
| `thumbnail_url` | body | string | 선택 | 카드 이미지 URL |
| `image_copyright` | body | object | 대표 이미지가 있으면 예 | A03 저작권 정보 객체. DDL 003은 이미지 URL이 있으면 저작권 유형 필요 |
| `image_copyright.type` | body | string | 객체가 있으면 예 | `Type1`·`Type3`, `festivals.image_copyright_type`에 대응 |
| `reason` | body | string | A55·A56 예 | 관리자 등록·수정 이유 |
| `published` | body | boolean | A56 선택 | 게시 여부 |

**A55 등록(201)·A56 수정/게시(200) 응답**

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
|---|---|---|---|---|
| `festival_id` | 응답 | string | 예 | 등록하거나 수정한 축제 ID |
| `review_status` | 응답 | string | 예 | 등록은 `pending`, 수정 후 상태는 `pending`·`approved`·`hidden` |
| `published_at` | 응답 | string(date-time) 또는 null | A56 예 | 공개 시각, 비공개면 null |

**동작 규칙** — `admin/festivals.py`에서 두 요청을 처리합니다. `AUTH_PROVIDER=db`이면 JWT의 본인 프로필을 조회한 뒤 관리자만 서비스 계정을 사용합니다. 등록은 EV01·`admin_manual`·검토 대기로 저장하고, 같은 이름·시작일·종료일·장소의 제안은 A24 대기열에 커밋한 뒤 409를 반환합니다. 주소는 선택이며, 값이 있으면 공백을 뺀 한 줄과 유효한 좌표가 필요합니다. 수정은 기존 행과 합친 값으로 검증하고, 실제로 바뀐 칸마다 사유·작업자·전후 값을 남깁니다. `published=false`는 숨김으로 처리하고 최초 게시 시각을 보존합니다. 비공개 응답의 `published_at`은 null입니다. 두 TourAPI 경로의 수집 충돌은 A24에 표시합니다. 기본 모의 모드는 `MOCK_ADMIN_FESTIVALS_TOKEN`으로 관리자 시연을 지원합니다.

- 담당: `admin/festivals.py`(협업 규칙). 화면 `admin/festival-management/`.

---

## 8. 검증·실행 규칙과 변경 이력


### 8-1. Pydantic 검증 규칙

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

class FestivalEndpoint(BaseModel):                             # 축제 장소(축제 DB 좌표) — DB origin/destination_type='festival'
    type: Literal["festival"]

class PlaceEndpoint(Place):                                     # 사용자가 고른 곳 — DB ..._type='user' + 장소 해시(009)
    type: Literal["place"] = "place"                           # 생략하면 place

Endpoint = FestivalEndpoint | PlaceEndpoint                     # API 값 'place' ↔ DB 값 'user'

class ReturnRouteRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)       # 멱등 키(UUID 권장)
    festival_id: str = Field(pattern=FESTIVAL_ID)
    origin: Endpoint = FestivalEndpoint(type="festival")       # 출발: 기본 축제 장소, 바꿀 수 있음(S06)
    destination: Endpoint                                      # 도착: 보통 사용자 장소
    travel_mode: TravelMode = "transit"
    route_preference: RoutePreference = "fastest"
    user_constraints: UserConstraints = UserConstraints()
    departure: Literal["now"] = "now"                          # 예약 출발은 후속(Should)

class VisitRouteRequest(BaseModel):                             # 축제 가는 길 (D-015)
    request_id: str = Field(min_length=8, max_length=64)
    festival_id: str = Field(pattern=FESTIVAL_ID)
    origin: Endpoint                                           # 출발: 보통 사용자 장소
    destination: Endpoint = FestivalEndpoint(type="festival")  # 도착: 기본 축제 장소, 바꿀 수 있음(S06)
    # 두 모델 공통: origin·destination이 둘 다 festival이면 422(DB CHECK route_requests_endpoints_check와 같음)
    travel_mode: TravelMode = "transit"
    route_preference: RoutePreference = "fastest"
    user_constraints: UserConstraints = UserConstraints()
    departure: Literal["now"] = "now"

class FestivalSearchQuery(BaseModel):
    region: RegionCode = "ALL"
    date_from: str | None = None                               # YYYY-MM-DD
    date_to: str | None = None
    q: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = None   # 쉼표로 여러 값 "ongoing,upcoming" — 값마다 upcoming·ongoing·ended·cancelled 검사(코드 api/schemas/festivals.py)
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

RunStatus = Literal["queued", "running", "retrying", "succeeded", "failed"]   # 챗봇 작업 상태(6-9), RouteStatus와 별개

class AssistantContext(BaseModel):
    festival_id: str | None = Field(default=None, pattern=FESTIVAL_ID)
    route_request_id: str | None = Field(default=None, pattern=r"^rr_[0-9A-Za-z]{6,26}$")

class AssistantQueryRequest(BaseModel):                         # A06 (6-9)
    request_id: str = Field(min_length=8, max_length=64)       # 멱등 키
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(default=None, pattern=r"^cv_[0-9A-Za-z]{6,26}$")
    context: AssistantContext = AssistantContext()
    reference_date: str | None = None                          # YYYY-MM-DD, 없으면 서버 KST 오늘
```

- `RouteLoadSimulationRequest.upstream`에는 일부러 **시험용 어댑터만** 둡니다. 외부 길찾기 API에 부하를 거는 요청은 스키마 단계에서 막힙니다. Free 한도는 TMAP 하루 10건(오류 포함), 카카오 2차 하루 1,000건입니다. 부하 시험은 모의 응답으로만 합니다.
- `cache_state`·`repeat_group`·`run_index`는 요청량·중복 비율·캐시 준비 상태·실행 횟수를 남겨 같은 조건으로 다시 시험할 수 있게 합니다.
- 숫자 상한(동시 요청 200, 지속 300초 등)은 **초기값**이며 확정값은 8-4절 규칙을 따릅니다.
- **BFCL의 `F01`·`RR02`·`INC-003`은 평가용 가짜 ID**입니다. 실제 API는 2절 ID 형식(`fst_…`·`rr_…`·`inc_…`)만 받습니다. 평가 실행기는 모의 응답을 쓰므로 실제 API 검증을 거치지 않습니다([기록 4-7](API_구현_검증기록.md#4-7-bfcl-30문항과의-대조-강사-일일-피드백-5)절).
- 이 절의 모델에 걸리는 것은 모두 **422**입니다. 목적지를 실제로 찾을 수 있는지, 권한이 있는지는 여기서 판단하지 않고 서버 로직이 400·403으로 답합니다(2절 공통 규칙).

### 8-2. 위치·대화 정보 전달 범위

#### 8-2-1. 어떤 정보를 어느 기능에 넘기나
| 정보 | 쓰는 기능 | 도구·공급원이 받는 것 | 결과를 볼 수 있는 사람 | 로그·DB에 남기는 것 | 하지 않는 것 |
|---|---|---|---|---|---|
| 축제 장소 좌표 | 축제 상세·지도·귀가 출발 | 공개 정보 그대로 | 모두 | 그대로 | — |
| **사용자 출발·도착 장소**(검색어·좌표) | 귀가·가는 길(A04·A25)만 | 카카오 장소 검색(검색어)·TMAP/카카오 경로(좌표)는 요청 처리 중에만 전달 | 요청한 본인(A05 조회 토큰, 로그인 여부 공통) | `ROUTE_PROVIDER=real`에서 메모리 원문은 TMAP 캐시가 만료될 때 또는 카카오·실패 처리 종료 때 정리([기록 17-3](API_구현_검증기록.md#17-3-저장캐시-규칙--실제-코드-강사-1120-api-2)). DB에는 장소 **HMAC 해시**만(009). Redis 라벨 보존은 24시간으로 확정했고 연동은 후속입니다. 서버 로그는 경로 템플릿·`X-Request-ID`·`route_request_id`·HTTP/처리 상태, 공급원 호출 로그는 공급원·HTTP 상태를 기록 | 원문 좌표·검색어를 로그·DB·모델 프롬프트 기록에 남기지 않음, 다른 기능(추천·동행)에 재사용하지 않음 |
| 경로 결과(TMAP) | A04·A05 | — | 본인 | 메모리 캐시 60초. DB 후보 요약은 기본 23시간 기준으로 시간당 정리(정상 실행 시 최대 24시간 보관). 정리 작업 운영 예약·감시는 후속 | 만료 후보 제공 |
| 경로 결과(카카오) | A04 동기 응답 | — | 본인 | **아무 데도 안 남김** | 캐시·재전달 |
| 챗봇 질문(A06) | AI 질문 | 에이전트: 질문 문장 + 선택한 `festival_id` | 본인 | 마스킹한 질문(전화·이메일 등, DB 설계서 7-0) | 동행 채팅 원문·다른 사용자 정보를 프롬프트에 넣지 않음 |
| 동행 채팅 원문 | 채팅방 참여자 간 전달 | **에이전트·LLM에 넘기지 않음** | 참여자. 관리자(A77)는 신고된 메시지 1건만, 방 신고는 방 정보·사유만 | DB 보존 규칙(동행 종료 3일, DB 설계서 7-0) | 모델·로그로 전달 |
| 가입 정보(출생연도·성별) | 동행 신청 확인 | `app_applicant_profile`(글 작성자만) | 동행 글 작성자 | DB | 에이전트·추천에 원문 전달 |

#### 8-2-2. 허용·차단 시험

8-2-1의 금지 규칙마다 시험을 하나씩 둡니다. 시험 목록과 결과는 [API 구현·검증 기록 21절](API_구현_검증기록.md#21-정보-전달-허용차단-시험-설계서-8-2-2에서-옮김)에 있습니다.

### 8-3. 실행 규칙: 장애 격리·호출 제한 (타임아웃·재시도·중복 실행 방지)

| 장치 | 설정(초안) | 이유 |
|---|---|---|
| 작업 풀 분리 | 귀가 조회 처리와 축제 검색·상세를 서로 다른 동시성 한도로 처리 | 귀가 부하가 검색을 멈추지 않게 (FR-H18, BFCL NLD-06) |
| 타임아웃 | 길찾기 어댑터 TMAP 5초·카카오 3초 · 그 밖의 외부 데이터 3초 · **도구 호출 5초(`TOOL_TIMEOUT`, 공통 실행기 기본값 — A04는 3초 안에 200 또는 202로 답함)** · **에이전트 실행(A06) 시도 1회 30초, 재시도 1회 포함 최대 65초** | 무한 대기 방지 |
| 재시도 | 일시적 오류(시간 초과·429·5xx)만 최대 1회, **1초 뒤**(429는 `Retry-After`), 같은 멱등 키 | 무제한 재시도 금지 (FR-H02) |
| 요청 수 제한 | 귀가·가는 길 요청 IP·세션당 분당 10회, 챗봇 분당 10회(초기값, 8-4 ⑤) | 외부 쿼터·비용 보호 |
| **길찾기 일일 한도** | TMAP Free 10건(오류 포함) 도달 시 카카오 2차(하루 1,000건). 하루 비용 상한 0원. **80%: 운영 경고 + 그 공급원으로 보내는 우회 조치(`fallback_provider_switch`) 원복. 100%: 그 공급원 호출 중지**(양쪽 소진 시 `ROUTE_QUOTA_EXCEEDED`). 카운터의 현재 저장 위치와 설정 기준은 8-4 ⑤ 참조 | 확정 |
| 외부 데이터 캐시 | 날씨·도착 정보·돌발은 공급원 갱신 주기만큼 캐시(초안: 도착 30초, 돌발 1분, 날씨 10분) | 같은 화면을 여러 사람이 볼 때 외부 호출 줄이기 |
| LLM 실패 | `/api/v1/assistant/query` 실패해도 A02~A05는 독립 동작 | FR-C09, FR-H13 |
| 외부 429 | `ROUTE_UPSTREAM_ERROR` + 원본 코드 로그, 재시도는 `Retry-After` 이후 1회 | BFCL NLD-12·25 |
| 재시도하지 않는 오류 | 400·401·403·404·409·422 | 입력·권한 문제는 다시 보내도 같음(수업 가이드 S22) |
| 중복 실행 방지 | 경로 요청은 `request_id`, 복구 결정은 `Idempotency-Key`로 처음 결과를 돌려줌. 같은 사건에 실행 중인 조치가 있으면 409 | 수업 가이드 S22 |
| 실제 공급원 부하 금지 | 부하·장애 시험의 `upstream`은 `mock_adapter`만(8-1절 스키마에서 막음) | — |

위 표의 숫자는 모두 **8-4절 기준표**에서 가져온 것입니다.

### 8-4. 제한값 기준표 (단일 기준)

**이 표가 유일한 기준입니다.** 다른 절(4·5·6·7·8-3절, 04 문서 4절)에 적힌 숫자는 이 표를 가리키는 사본이고, 다르면 이 표가 맞습니다. 설정 통합 뒤 코드는 `shared/config.py`의 `Limits`에서 값을 읽고, 묶음 버전 **`LIMITS_VERSION`(초안 `lim-0.1`)** 을 부하 시험 결과 JSON(`load_simulations.result_ref`)·A18 `policy_version`·A31 응답에 함께 남깁니다(같은 시험을 같은 설정으로 다시 돌릴 수 있게). 값을 바꾸면 버전을 올리고 이 표의 '상태'를 고칩니다.

**표의 숫자는 초기값입니다.** 이 표는 각 제한의 설정 키·의미·넘었을 때의 동작·확정 방법을 정하는 계약이고, 숫자는 측정 전 출발점입니다. 부하 측정·복구 정책 등으로 확정한 실제 값은 [API 구현·검증 기록 25절](API_구현_검증기록.md#25-제한값-확정-기록-설계서-8-4의-초기값--측정-뒤-확정값)에 설정 버전(`LIMITS_VERSION`)과 함께 적고, 코드는 그 값을 설정으로 읽습니다. 이 표는 **설정 키·의미·동작이 바뀔 때만** 고칩니다(숫자만 바뀌면 설계서는 그대로).

- 상태: **확정** = 팀이 확인한 값 / **초기값** = 측정 전 출발점(확정값은 [기록 25](API_구현_검증기록.md#25-제한값-확정-기록-설계서-8-4의-초기값--측정-뒤-확정값)절) / **외부 고정** = 공급원·약관이 정한 값 / **설계 고정** = 의미상 정해진 값

**① 시간 제한(타임아웃)**

| 설정 키 | 값 | 쓰는 곳 | 이유 | 상태 |
| --- | --- | --- | --- | --- |
| `ROUTE_SYNC_WAIT_S` | 3초 | A04 동기 대기(넘으면 202) | 화면이 오래 멈추지 않게. 카카오(2차)는 이 안에서만 전달(6-7절) | 초기값 |
| `ROUTE_TOTAL_TIMEOUT_S` | 10초 | A04/A05 전체 처리(넘으면 `timed_out`) | 요청 전체 상한. 카카오 응답 전달은 동기 3초 안 | 초기값 |
| `ROUTE_ADAPTER_TIMEOUT_S`(통합 설정 예정) | TMAP 5초·카카오 3초 | 길찾기 1회 호출 | TMAP 실측 평균 응답 273ms·처리 314ms(4건) — 여유 크게 둠, 부하 시험은 모의라 W36에서 다시 봄 | 초기값 |
| `EXT_DATA_TIMEOUT_S` | 3초 | 날씨·도착·돌발·혼잡 호출 | 부가 정보라 짧게 | 초기값 |
| `TOOL_TIMEOUT_S` | 5초 | 에이전트 도구 1회(`TOOL_TIMEOUT`) | 공통 도구 실행기 기본값(`backend/agents/tools`). A04는 동기 대기 3초 뒤 202로 답하므로 5초 안에 끝남 | 초기값 |
| `AGENT_RUN_SOFT_LIMIT_S` | 30초 | A06 작업 1건(넘으면 `failed`) | 챗봇 답변은 짧아야 함 | 초기값 |
| `AGENT_RUN_HARD_LIMIT_S` | 40초 | 워커 강제 종료 | soft + 10초 | 초기값 |
| `INGEST_SCHEDULE` | 매일 06:00 (KST) | 축제 정기 수집(A23 이력) | TourAPI 하루 갱신이면 충분 | 실행기 구현 완료 |
| `COMPANION_AUTO_END_H` | 12시간 | 만남 시각 뒤 자동 동행 종료(A65) | 기획서 '정책에 따른 자동 종료' | 초기값 |
| `CHAT_RATE_USER` / `CHAT_RATE_ROOM` | 초당 5개 / 초당 20개 | WebSocket 전송 제한 | 도배 방지 | 초기값 |
| `WS_TICKET_TTL_S` | 30초 | WebSocket 연결 표 | 1회용 표 | 초기값 |
| `CHAT_REDIS_RECENT` | 방당 최근 100개(24시간) | Redis 최근 메시지 | 빠른 조회(DB 7-0) | 확정 |
| `TAG_LLM_DAILY_MAX` / `REC_WEIGHTS_VERSION` | 하루 300건 / `rec-0.1` | 축제 태그 LLM 검증 상한(7-2-1) / 추천 점수 가중치 묶음 | LLM 비용 상한 / 가중치 바꾸면 버전 올림 | 초기값 |
| `TREND_CRAWL_SCHEDULE` / `TREND_STALE_H` | 6시간마다 / 12시간 | A42 수집 주기·신선도 기준 | 실패·한도 초과·12시간 초과는 출처별로 적용. 두 출처 모두 점수를 낼 수 없으면 마지막 성공 목록을 `stale`로 표시(7-1) | 확정 |
| `TREND_SCORE_WEIGHTS` | `naver_datalab: 0.6`, `visitkorea: 0.4` | A42 최종 점수 | 두 점수가 있을 때 가중합. 한쪽만 있으면 해당 점수 그대로 사용 | 확정 |
| `TREND_MIN_RELATIVE` | 0.01 | A42 최근 7일 검색 신호 하한 | 같은 요청의 기준점('축제') 최근 7일 평균 대비 1% 미만은 `no_signal` | 확정 |
| `NAVER_API_HUB_KEY_ID` / `NAVER_API_HUB_KEY` | 서버 환경변수 | NAVER API HUB 데이터랩(A42)·검색(A81) 공용 | 인증 헤더 `X-NCP-APIGW-API-KEY-ID`·`X-NCP-APIGW-API-KEY`. 상세 명세는 [기록 13](API_구현_검증기록.md#13-외부-데이터-공급원과-지역-범위-1118-회의-반영)절 | 확정 |
| `POSTS_LIMIT` | 5건(설정 범위 3~5) | A81 최신 글 표시 | 세 출처의 필터 통과 결과를 합쳐 최대 5건 | 확정 |
| `SIM_STOP_GRACE_S` | 2초 | A21 중단 후 새 요청 멈춤 | 시연 정지 버튼 | 초기값 |
| `RECOVERY_DEFAULT_MAX_MIN` | 5분 | A19 `stop_condition` 기본값 | 5-8 재측정 한 번에 충분 | 초기값 |

**② 재시도**

| 설정 키 | 값 | 쓰는 곳 | 규칙 | 상태 |
| --- | --- | --- | --- | --- |
| `EXT_RETRY_MAX` / `EXT_RETRY_DELAY_S` | 1회 / 1초 | 외부 API 일시 오류(시간 초과·429·5xx·TAGO `99`) | 429는 `Retry-After`. 400·401·403·404·409·422는 재시도 없음 | 초기값 |
| `ROUTE_PROVIDER_FAILOVER` | 1회 | A04 요청 안 1차 → 2차 | 요청 1건에 2차는 한 번만 | 설계 고정 |
| `TOOL_ROUTE_RETRY_MAX` | 1회 | 도구 래퍼 `ROUTE_TIMEOUT` | 먼저 상태 확인 → 같은 `request_id`로만 | 설계 고정 |
| `AGENT_RUN_RETRY_MAX` / `AGENT_RUN_RETRY_DELAY_S` | 1회 / 5초 | A06 작업(LLM 429·5xx·시간 초과) | 같은 `run_id`로 `retrying`. 그 밖 오류는 즉시 `failed` | 초기값 |

**③ 상태 조회 간격(폴링)**

| 설정 키 | 값 | 쓰는 곳 | 상태 |
| --- | --- | --- | --- |
| `ROUTE_POLL_INTERVAL_S` / `ROUTE_POLL_MAX` | 2초 / 5회 | A05 화면 폴링, `get_route_request_status` | 초기값 |
| `RUN_POLL_INTERVAL_S` / `RUN_POLL_MAX` | 2초 / 20회 | A06-1 폴링(SSE 전 1단계) | 초기값 |

**④ 캐시 시간**

| 설정 키 | 값 | 쓰는 곳 | 상태 |
| --- | --- | --- | --- |
| `ROUTE_CACHE_TTL_S` | 60초 | TMAP 서버 메모리 캐시(`valid_until`), `valid_cache_serve` | 확정 |
| `EXT_CACHE_TTL_S.arrival` | 30초 | 지하철·버스 도착 | 초기값 |
| `EXT_CACHE_TTL_S.incident`·`.crowd`·`.bike` | 60초 | 돌발·혼잡·자전거 | 초기값 |
| `EXT_CACHE_TTL_S.weather` | 600초 | 기상청 | 초기값 |
| `POSTS_CACHE_TTL_S` | 600초 | A81 Redis `posts:{festival_id}` | 확정 |
| `STALE_FACTOR` | 2배 | 관측 시각이 공급원 갱신 주기의 2배 넘으면 `stale` | 초기값 |

**⑤ 동시 요청·요청 수·한도**

| 설정 키 | 값 | 쓰는 곳 | 상태 |
| --- | --- | --- | --- |
| `ROUTE_RATE_LIMIT_PER_MIN` | 10회/분 (IP·세션당) | A04·A25 (`rl:route`) — **부하 생성기는 내부 시험 경로라 적용 안 함** | 초기값 |
| `ASSISTANT_RATE_LIMIT_PER_MIN` | 10회/분 (IP·세션당) | A06 | 초기값 |
| `ROUTE_WORKER_CONCURRENCY` | 20 | 귀가 조회 동시 처리 상한(작업 풀 분리) | 초기값 |
| `ROUTE_QUEUE_MAX` | 50 (조정 범위 20~100) | 내부 대기열 상한 — `bounded_queue_adjust`는 이 범위 안에서만 | 초기값 |
| `SIM_*` 상한 | 동시 1~200, 지속 5~300초, 초당 ≤100, 지연 주입 ≤5,000ms, 반복 ≤20 | A20 (8-1절 스키마) | 초기값 |
| `RECOVERY_MAX_ACTIVE` / `RECOVERY_MAX_ATTEMPTS` | 1 / 3 | A18·A19 (5-8 순서) | 초기값 |
| `QUOTA_TMAP_FREE` / `QUOTA_KAKAO_FREE` (지금 코드: `ROUTE_TMAP_DAILY_LIMIT` / `ROUTE_KAKAO_DAILY_LIMIT`) | 10건/일 / 1,000건/일 (카카오 도보도 1,000건/일 따로) | `quota:{provider}` — **오류 응답(403 등)도 1건으로 셈**(SK 회신 없이 적용하는 확정 기준: 오류 포함 모든 요청을 1건으로 세고 매일 0시 KST 초기화로 운영) | **외부 고정**(공급원 공식 한도, `evidence/usage/API_공식한도_20261120.md`) |
| `QUOTA_DAILY_COST_KRW` | **0원/일**(무료 한도 안에서 호출) | 공급원별 비용 상한, 80% 경고·100% 중지 | 확정 |
| `TMAP_PAID_PLAN` (결정 항목 이름) | **유료 전환 안 함** | Free 10건/일(오류 포함), 한도 도달 시 카카오 2차(1,000건/일). 부하 시험은 모의 응답 | 확정 |
| 수집 공급원 하루 한도 (참고, 외부 고정) | TourAPI·서울 버스도착·서울 정류소 1,000건/일(기능별) · 서울 실시간 지하철 1,000회/일 · 기상청·TAGO·표준데이터 10,000건/일 · 서울 일반 키 제한 없음(1회 1,000건) · 카카오 장소 검색 100,000건/일 | 수집 워커·실시간 조회 | 1,000건 공급원은 **DB 적재 후 조회**(요청 때 직접 부르지 않음) |
| `AUTH_RATE_LIMIT_PER_MIN` | 10회/분 (IP당) | 로그인 A33(2-5절) | 확정 |

**동작 규칙** — A04·A25의 공개 POST는 IP와 로그인 세션별 `rl:route` 메모리 카운터를 공유합니다. 한도 초과 시 공통 `429 RATE_LIMITED`와 다음 분까지의 초를 `Retry-After`로 반환합니다. 내부 서비스 호출은 공개 라우터를 거치지 않습니다.

**⑥ 토큰·잠금·중복 실행 방지 키의 수명**

| 설정 키 | 값 | 쓰는 곳 | 상태 |
| --- | --- | --- | --- |
| `ACCESS_JWT_TTL_MIN` / `REFRESH_TTL_DAYS` | 30분 / 14일 | 2-4절 인증 | 확정 |
| `REVOKED_TTL` | Access 남은 수명 | `revoked:{jti}`. JWT의 `exp`에서 계산 | 설계 고정 |
| `JWT_SECRET` / `JWT_ISSUER` | 32바이트 이상 비밀값 / 기본 `noldaga-api` | DB 모드 HS256 서명·발급자 검증 | 구현값 |
| `ROUTE_TOKEN_TTL_MIN` / `ROUTE_REQ_TTL_MIN` | 10분 / 10분 | Redis의 `route:token`·`route:req` 예정값. 현재 DB 모드는 `submitted_at` 기준 A05 토큰 10분을 적용 | 초기값 |
| `RUN_TOKEN_TTL_MIN` | 10분 | `run_access_token`(A06-1·A06-2) | 초기값 |
| `ROUTE_INFLIGHT_TTL_S` | **12초** (= `ROUTE_TOTAL_TIMEOUT_S` + 2초) | `route:inflight`(동일 요청 병합) | 초기값(아래 대조) |
| `POLICY_ACTIVE_TTL` | `stop_condition.max_minutes` + 60초 | `policy:route:active`(켜진 조치) | 초기값(아래 대조) |
| `REFRESH_LOCK_TTL_S` | 5초 | `refresh:lock` | 초기값 |
| `WITHDRAWAL_LOG_KEEP_DAYS` | 8일 | DB 밖 탈퇴 기록(A80, DB 설계서 7-0 ⑥) | 확정 |
| `ROUTE_LABEL_TTL_H` | 24시간 | Redis `route:label:{route_request_id}` — 목적지·출발지 표시 이름(DB에는 저장하지 않음, 04 문서 7-0) | 확정 |

**⑦ 장애 감지·복구 초기 SLO**

| 항목 | 기준 | 상태 |
| --- | --- | --- |
| 장애 감지 | 귀가 조회 p95 3초 초과가 30초 지속 | 확정 |
| 복구 | 귀가 조회 p95 3초 이하가 5분 유지 | 확정 |

숫자 확정은 8-4절 규칙을 따릅니다.

**⑧ 연결·중복 판정·집계 기준**

| 항목 | 값 | 쓰는 곳 | 이유 | 상태 |
| --- | --- | --- | --- | --- |
| 정류장 연결 거리 | 30m 이내 | 귀가 경로에서 고른 후보의 버스 정류장 연결(4-3·4-4절) | 이름·거리·노선·방향이 모두 일치하는 단일 후보 연결 | 확정 |
| 교통 돌발 병합 거리 | 100m 이내 | A28 경찰청·TOPIS 돌발 병합(7-1절) | 인접하고 발생 시간이 겹치는 같은 사건을 한 건으로 집계 | 확정 |
| 같은 대상 신고 제한 | 신고자당 하루 1회 | A76 신고 등록(7-2-6절) | 같은 신고자가 동일 대상에 반복 신고하는 것을 방지 | 확정 |
| `window_at` 시간창 | 10초 | A16·`route_query_metrics` 지표 집계(DB 설계서 6절) | 같은 10초 구간의 운용·부하 지표를 묶어 비교 | 확정 |

**중복 실행 방지 키가 작업보다 먼저 만료되지 않는지 대조**

| 키 / 보관 위치 | 키 수명 | 지켜야 할 작업의 최대 시간 | 판정 |
|---|---|---|---|
| `route:inflight` | 12초 | 경로 처리 최대 10초(1차 5초 + 2차 5초) | ✅ (처리보다 먼저 만료되면 같은 요청이 또 실행돼 병합 효과가 사라지므로 처리 시간 + 2초) |
| `policy:route:active` | `max_minutes` + 60초 | 조치 최대 `max_minutes` | ✅ (정책 코드가 죽어도 조치가 영원히 켜져 있지 않게 하는 안전 TTL. 정상 원복은 코드가 함) |
| A04·A25 `request_id` / `route_requests.request_id` UNIQUE | 행 보존 30일 | 처리 10초 + 상태 조회 10분 | ✅ |
| `route:token`·`route:req` | 10분 | 처리 10초 + 폴링 10초 | ✅ (만료 뒤 `route:req`는 DB에서 읽음) |
| A06 `request_id` / `assistant_runs.request_id` UNIQUE(002) | 행 보존 30일(04 문서 7-0 보존표) | 작업 최대 30초 + 재시도 5초 + 30초 = 65초 | ✅ |
| `run_access_token` | 10분 | 65초 + 결과 조회 | ✅ |
| A06 워커 선점(claim) | DB 상태라 만료 없음 | 워커가 실행 중에 죽으면 `running`으로 남음 | ⚠ **감시 규칙 추가**: `running`이 `AGENT_RUN_HARD_LIMIT_S`+30초(=70초)를 넘으면 정리 작업이 `failed`(`AI_AGENT_FAILED`)로 바꿈 — 재전달된 작업이 선점에 막혀 영원히 멈추지 않게 |
| A19 `Idempotency-Key` / `recovery_plans.idempotency_key` UNIQUE | 영구(감사 기록) | 조치 최대 5분 | ✅ |
| A20 `Idempotency-Key` / `load_simulations.idempotency_key` UNIQUE | 영구 | 시험 최대 300초 × 3구간 | ✅ |
| `refresh:lock` | 5초 | Refresh 교체 1초 미만 | ✅ |

### 8-5. 변경 이력

| 버전 | 날짜 | 바뀐 점 | 작성 |
|---|---|---|---|
| v0.1 | 2026-11-17 | 초안 작성(A01~A24, 도구 13개) | 백엔드 |
| v0.2 | 2026-11-18 | A25~A30 추가(가는 길·대중교통 도착·교통 돌발·방문 집중 예측·데이터 지원 범위) | 백엔드 |
| v0.3 | 2026-11-19~20 | 길찾기·공공 API 실호출 필드 반영, A06 비동기 작업으로 변경, 추천·친구·동행·채팅·알림·신고·방문 코스·관리 API 상세 추가 | 백엔드 |
| v0.4 | 2026-11-23 | 정보 전달 범위(8-2) 추가, 축제 공개 범위 확정 | 백엔드 |
| v0.5 | 2026-11-24 | 필드 명세 표 전체, 제한값 기준표(8-4), 인증·추천 계약 확정 | 백엔드 |
| v0.7 | 2026-11-25 | 제출본: 학원 산출물 양식 목차로 정리, 비밀번호 변경(A82) 추가, 카카오 좌표 보정 중단(좌표 없는 축제는 마커만 제외), A10 동률 구역은 안쪽 깊이 순. 읽는 순서(개요→공통→목록→핵심 흐름→장애 대응→Tool→추가 기능→규칙)로 재배치(내용과 API 계약은 그대로이고 절 번호만 바뀜) | 백엔드 |
