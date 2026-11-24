# 03. API 설계 문서

놀다가(NOLDAGA) / 3팀 수다수다 | 문서 버전 **v0.4** | 작성 상태: **11/23 재제출본(강사 11/20 피드백 반영 — 0-A절)** | 작성 2026-11-17 · 수정 2026-11-23 · 권오현(백엔드) — AI 초안 후 본인 검토

문서명: REST API 및 Function Calling 명세서

## 문서 정보

| 항목 | 내용 |
|---|---|
| **정본(이 문서의 기준 위치)** | GitHub `yubeenjjang/Final3team` → `Docs/Step 2/API_설계문서.md`. **이 경로만 정본**이며 로컬 파일·Discord 첨부는 사본입니다. 대시보드 제출 링크도 이 경로를 씁니다 |
| 짝 문서 | `Docs/Step 2/DB_스키마_설계서.md` v0.4 (같은 ID 형식·필드↔컬럼 대응은 16절) |
| 기준 문서 | **기획서 최신본(11/19 05:18 신유빈 님 공유, v3.1 다음판 — [놀다가 기획서](../Step%201/놀다가_기획서.md) — 11/23 신유빈 님이 main 최종본으로 정리)** · 기획서 v3.1(11/19 정예진) · [WBS 128개](../Step%201/놀다가_WBS.md)(필수 118, W112~W128 신규), 결정대장 D-009~D-039(팀 회의·멘토 2차 회의·11/19 사용자 결정) + 11/20 결정(추천 취향에서 아기 동반 제외 — 반려견 동반만), 팀 자체 평가 30문항(한다영, 11/18, 이하 BFCL), 17개 시·도 데이터 조사, 강사 2차 의견(11/18)·일일 피드백(11/19), 수업 가이드 「API 설계 문서 작성법」(11/18) |
| 진행 단계 | ☑ 초안 작성(11/19) → ☑ 팀 검토 완료(11/19 신유빈·정예진) → ☑ GitHub 정본 업로드(v0.3.1, 11/19 신유빈 `91b3337`) → ☑ v0.3.2 교체·증빙 업로드(11/20 12:32 신유빈 `41c66a5`) → ☑ v0.3.3 교체·`db/`·증빙 추가 업로드(11/20 16:24 신유빈 `e8aecb4`) → ☑ v0.3.3 9-2절(운영비) 추가 → ☑ **v0.4 작성(11/23, 강사 11/20 피드백 반영)** → ☐ v0.4 GitHub 정본 교체(`ohyun` 병합) → ☐ 대시보드 링크(`Docs/Step 2/API_설계문서.md`)·제출 상태 **팀 확인 대기**. 문서에 '재제출본'이라 적은 것은 대시보드 제출·접수 완료가 아닙니다 |
| v0.4 대조 기준 | `ohyun`의 `4f8b8c2`에 있는 코드·SQL과 11/23 로컬 시험 기록. v0.4 GitHub 정본 기준 커밋은 병합 뒤 기록 |
| 범위 | **핵심 기능**(전국 축제 탐색 + AI 안심 귀가 + 귀가 조회 장애 자동 복구, 2~7절) + **기획서 필수 추가 기능**(맞춤 추천·지금 핫한 축제·친구·동행·채팅·알림·신고·마이페이지·AI 방문 코스·공지·축제 관리, A36~A80 — 6-2·6-3~6-6절). 그 밖의 새 기능은 14절 '확장 지점' 규칙으로 붙입니다 |
| 실제 호출 근거 | 서울 실시간 인구(11/16) + **11/19 한태경 님 실호출 10종**(TourAPI·기상청·TAGO·서울 지하철·주차장·TOPIS·문화행사 등, 10절). **길찾기 TMAP(1차)·카카오맵(2차)도 11/19 실호출 완료**(서울·부산 정상, 한태경). 두 공급원 원본은 24시간·저장 금지 규칙으로 지웠고, 증빙은 **호출 기록표(시각·좌표·HTTP 상태·결과 건수·오류 코드) + SK 콘솔 사용량 + 합성 예시**로 남깁니다(10절, 11/20 한태경 완료). 증빙 폴더: GitHub **`Docs/Step 2/evidence/`**(이하 `evidence/`, README·원본 54개·합성 예시 7개·키 없는 호출 스크립트) |

> **이 문서의 모든 API는 설계안입니다.** 구현·외부 공급원 연동·배포가 끝났다는 뜻이 아닙니다. 미확인 항목은 11절, 기획서와 다른 점은 15절, 바뀐 점은 맨 아래 '변경 이력'에 있습니다.

### 검토 기록

| 일자 | 검토자 | 범위 | 결과·수정 내용 |
|---|---|---|---|
| 2026-11-19 | 권오현 (AI 초안 작성) | 전체 | v0.3 작성: 강사 피드백·멘토 회의·D-033~D-036·수업 가이드 반영 |
| 2026-11-19 | AI 교차 검토(Gemini 4 Neon) | 전체 | 25건 지적 → 내부 모순·BFCL 생략 인자·오류 코드 등 반영. 남은 것(1차 필수 API 일부의 상세·필드 표, 도구 6개 JSON Schema)은 v0.4로 '상세 명세 작성 범위' 표에 기록 |
| 2026-11-19 | 신유빈(인프라·R06 검토) | 전체 | 검토 완료. 변경 이력 정리·택시 범위·추적 ID·최신 기획서 대조·신규 기능(v0.4) 표기 요청 → 반영 |
| 2026-11-19 | 정예진(기획) | 기획서와 대조 | 6건(경로 5유형 이름, 택시 범위, created, 대조표, 추적 ID, 카카오 비동기) → 반영 |
| 2026-11-20 | 팀 답변(정예진 권한 정책안 · 신유빈 보존·열람·크롤링 · 한태경 보존 검토·일정) | 6-3·A36·A42·9-1·11절 | 동행 보존 3일·친구 30일, 채팅 열람 참여자·관리자, 채팅 WebSocket·추천 신유빈(GitHub 협업 규칙), 취향 5개, **A42 지금 핫한 축제 추가**, 목적지 라벨 Redis 24시간·해시 HMAC, 태경님 남은 확인 일정(11/20·11/24·11/25) → v0.3.3 |
| 2026-11-20 | 한태경(W10 실호출·증빙) | 10·10-2·10-3·11절 | 길찾기 호출 기록·콘솔 사용량·오류 응답·이용 조건·`overview`·TAGO 서면 결과 제공 → 반영(증빙 폴더 `evidence/`) |
| 2026-11-20 | 강사(11/19 피드백 6건) · 권오현 | 전체 | 1차 반영(v0.3.2): 정본 파일명(`API_설계문서.md`), 옛 Supabase 문장, 길찾기 실호출 결과(10절), 한태경 실호출 21종 반영. **2번 반영**: 필수 도구 6개 JSON Schema·성공/실패 출력(4-6), A05 응답 필드 표, A06(비동기 작업으로 변경)·A14·A16·A18·A21 8칸 상세(7-6~7-10). **4번 반영**: 9-1절 제한값 기준표. **1·3번 반영**: 태경님 증빙(10·10-3절, `evidence/`). **2번 추가**: 나머지 API 상세(6-2)·도구 5개. **5번 반영**: 6-3 범위·순서표. 증빙 폴더 GitHub 업로드는 11/20 12:32 `41c66a5`로 끝남, 추가 기능 상세는 v0.3.3에서 작성(6-3~6-6) — 권오현 개인 정리본(공유본은 이 표) |
| 2026-11-20 | AI 교차 검토 3종(Claude Opus 5.5 · Codex gpt-6.2-sol · agy Gemini 4 Hydrogen XHigh) | 03·04 문서 전체 + `db/` | 꼭 고칠 것 중 문서 19건 + SQL 7건(마이그레이션 008, 시험 T42) 반영, 한태경 11/20 15:03 공식 한도·카카오 공식 답변·정류장, 15:48 최종 정리(`service`=0 재확인 → lane 판단, SK 문의 발송, 정류장 파일 확인, 이미지 처리안 확정) 반영. 제출 뒤 처리할 것은 11-1절(담당·날짜) → v0.3.3 |
| 2026-11-23 | 강사(11/20 API 피드백 5건) · 권오현 · AI 교차 검토 | 전체 + 실행 코드 | **v0.4**: 0-A 반영표, 17절 첫 흐름 실제 실행 기록(모의→실제), 18절 위치·대화 정보 전달 범위, 19절 결정 반영 기록, 개인 PC 경로 제거. 근거 코드·시험은 `backend/`(ohyun 브랜치). **팀 검토자: 검토 대기**(신유빈 님이 동의한 4건은 19절에 표시) |
| 2026-11-23 | AI 교차 검토 2종(Codex · Gemini) | 03·04 문서 + `backend/` 코드·시험 + `db/` | 문서와 코드가 다른 곳을 '현재 동작(코드 기준)'과 '구현 예정'으로 나눔(A05 만료, `route_key` 입력, 막차, 환경변수, 좌표 메모리 보관), 근거가 부족한 0-A 항목 🟡로 낮춤, A77 관리자 열람 범위·A02 여러 상태 규격 통일, 시험 함수명·개수 정정. 코드는 고치지 않음 |

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

## 0-A. 강사 11/20 피드백 반영표 (v0.4, 2026-11-23)

| # | 피드백 | 상태 | 반영 위치 | 근거(다시 확인하는 방법) |
|---|---|---|---|---|
| 1 | 축제 검색→상세→귀가 요청→상태 조회를 **먼저 실제로 실행**, 상태값·응답 예시, 모의/실제 구간 표시 | 🟡 일부 | **17절**(17-1·17-5), 2-2 A04·A05 | **완료** — 같은 실제 축제 ID로 A02→A03→A04 실행 및 동기 `ready` 확인, 모의 A04→A05로 처리 중·실패 상태값과 응답 증빙. 실제 A05는 A04에서 200으로 끝나 호출 생략. **남은 것** — 추천·동행·채팅 순서·담당·완료 기준 합의(1′), 화면 연결(12/8 첫 시연), 11/27 상태 전이 설계에 정상·실패·종료 경로 연결 |
| 1' | 추천·동행·채팅 첫 시연/후속 순서·담당·완료 기준 합의 | 🟡 일부 | 19절(결정 반영 기록), 12/8 시연 범위는 신유빈 11/23 공지(축제→상세→귀가) | 동행·채팅은 12월(팀 합의 대기) |
| 2 | 공급원별 저장·캐시 규칙을 **실제 처리 코드**와 맞춤, 동기 전용(카카오)·비동기 구분, 합성 예시 ≠ 실제 증거 | 🟡 일부 | **17-3절**(코드·시험 대응, 현재 동작과 예정 구분), 5절 막차 규칙, 17-4(합성 예시와 실제 호출 기록 구분) | DB 모드 A05 24시간 만료(`retryable=false`)와 요청 원문 비보관 구현 완료·**DB 시험 재실행 대기**(P18). `route_key` 추가 입력·Redis 라벨 연동은 후속(17-3) |
| 3 | 위치·대화 정보 최소 전달·열람자·로그 항목 구분, 허용/차단 시험 | 🟡 일부 | **18절** | **완료** — 백엔드 A04·A05·장소 검색·A10 로그 시험. **남은 것** — 만료·삭제 뒤 메모리·DB·Redis의 장소 원문 검사(권오현), 에이전트 도구 입력 제한 시험(한다영), A77 관리자 열람 범위·기록 시험 |
| 4 | 남은 결정을 API·도구·시험 반영 기록으로 닫기 | 🟡 일부 | **19절** | 작성자·검토자·날짜 칸. **남은 것** — 신유빈 님 동의 4건 외 검토자 확인, `yubeen`의 D1 공통 DB 연결·`RESET ALL` 병합 및 연결 시험 |
| 5 | 최신 정본 링크·제출 상태, 개인 PC 경로 제거 | 🟡 일부 | 문서 정보·전체(개인 경로 6곳 → 저장소 경로 또는 공유본 안내) | **남은 것** — 대시보드 링크·접수 상태 팀 확인, v0.4 기준 커밋(`ohyun` 병합 뒤), `origin/main` 기획서의 이전 설계서 경로·v0.3 인용을 담당자와 갱신 |

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
| **전국 공통 데이터** (정적·실시간 모두) | **전국** | 축제 검색·상세(A02·A03, TourAPI·전국문화축제표준데이터), 지도·장소 검색(카카오), 지도 시설 위치(A08), 날씨(A09, 기상청), 버스 도착(A26 버스: **서울 밖은 TAGO, 서울은 서울시 버스도착정보** — 11/19 실호출에서 TAGO 서울 0건), 교통 돌발(A28 경찰청), 길찾기 귀가·가는 길(A04·A05·A25: **1차 TMAP, 2차 카카오맵**, D-038), 방문 집중 예측·지역 수요(A29), 주변 상권(카카오 로컬), **자전거 존·택시 승강장(11/19 전국 공급원 확인 → 전국, D-036)** |
| **지역별로만 있는 데이터** | **서울만** | 혼잡 구역(A10, OA-21778 — **지도 표시 + 귀가 근거**), 지하철 실시간 도착(A26 지하철), 공영주차장 빈자리(A27), TOPIS 통제(A07·A28 보강), 서울 문화행사(A02·A03 보강), **버스 차내 혼잡(교통수단 선택 근거, D-033)** |
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
| **로그인 필요** (`user`) | 관심 축제 저장·해제·목록, 후기(Should), 취향(A36·A37), 친구(A43~A50), 동행 글 작성·신청(A58~A65), 채팅(A66~A73), 알림(A74·A75), 신고(A76), 마이페이지·탈퇴(A78~A80) — 6절 '권한' 칸이 `user`인 API 전부 |
| **운영자 이상** (`operator`·`admin`) | `/api/v1/admin/**` — 단 **A23·A24·A52~A56·A77은 `admin`만**(6절 '권한' 칸). 역할 검사는 라우터 의존성 하나(`require_role`)로 |
| **비로그인 경로 요청 보호** | 상태 조회는 로그인 여부와 관계없이 `route_request_id` + 요청 시 발급한 `route_access_token`(로그인 JWT와 별개)으로 본인만 조회. 짧은 수명 적용은 DB·Redis 연결 때 구현(2-2절). IP·세션 단위 요청 수 제한 |


### 1-1. 인증 API 상세 (A32~A35, FR-A01~A04, D-037)

공통: 경로 `/api/v1/auth/*`, 본문 JSON, 비밀번호·토큰 원문은 **로그에 남기지 않음**(04 문서 7-0 ⑤). 요청 수 제한은 IP당 분당 10회(`AUTH_RATE_LIMIT_PER_MIN`, 임시, 9-1 ⑤). 오류 형식은 6절 공통 오류 응답과 같음.

| API | 요청 | 정상 응답 | 검증·처리 규칙 | 오류 |
|---|---|---|---|---|
| **A32** `POST /auth/signup` | `{email, password, display_name, birth_year, gender}` **모두 필수**(시나리오 S03, 11/20 결정) — 이메일 형식·254자 이하, 비밀번호 8~64자(영문·숫자 포함), **닉네임(`display_name`) 2~12자·대소문자 무시 중복 불가**, 출생연도 1900~올해, 성별 `male`·`female`, 닉네임은 앞뒤 공백 제거 후 검사 | **201** `{user_id, display_name}` (로그인은 따로 A33) | 이메일은 소문자로 바꿔 비교. 비밀번호는 argon2id(또는 bcrypt)로 해시만 저장. **한 트랜잭션**에서 `users`(status `active`) + `profiles`(role `user`, 닉네임·출생연도·성별) 생성. 나이·성별은 **동행 신청 때 그 모집 글 작성자에게만** 보임(A61, DB `app_applicant_profile`) | 422 형식 / 409 `EMAIL_ALREADY_EXISTS`·`NICKNAME_TAKEN` / 429 |
| **A33** `POST /auth/login` | `{email, password}` | **200** `{access_token, token_type:"bearer", expires_in:1800, refresh_token, refresh_expires_at, user:{user_id, display_name, role}}` | 계정 `status='active'`만. 실패 이유를 구분하지 않음(이메일 존재 여부 노출 금지). 성공 시 `users.last_login_at`, `refresh_tokens`에 **해시만** 저장(14일) | 401 `INVALID_CREDENTIALS` / 403 `ACCOUNT_DISABLED` / 429 |
| **A34** `POST /auth/refresh` | `{refresh_token}` | **200** A33과 같은 토큰 묶음(새 Access + **새 Refresh**) | **교체 방식**: `refresh:lock:{token_id}`(5초)로 동시 교체 방지 → 기존 행 `revoked_at` 기록 → 새 행 추가(한 트랜잭션). **이미 폐기된 Refresh가 다시 오면 재사용으로 보고 그 사용자의 Refresh 전부 폐기** | 401 `REFRESH_INVALID`(없음·만료) / 401 `REFRESH_REUSED`(재사용 — 다시 로그인) / 409 `REFRESH_IN_PROGRESS`(잠금 중) |
| **A35** `POST /auth/logout` | 헤더 Access JWT + 본문 `{refresh_token}` | **204** | 그 Refresh 행 `revoked_at` + Access의 `jti`를 `revoked:{jti}`(남은 수명만큼)에 넣음 → 이 기기만 로그아웃. 전체 기기 로그아웃은 탈퇴(A80)와 Refresh 재사용 감지 때만 | 401 |

- **보호 API의 인증 순서:** 서명·만료·발급자 검증 → `revoked:{jti}` 확인 → 역할 확인. **Redis 장애로 `revoked` 확인이 안 되면** 읽기 API는 그대로 처리하고, 쓰기·관리자 API는 503 `AUTH_CHECK_UNAVAILABLE`(안전 쪽). 담당 권오현 · 확정 W16(11/20 초안, 구현 때 W18에서 시험).
- **탈퇴·정지 계정:** Access JWT가 남아 있어도 보호 API마다 `users.status='active'`를 확인합니다(탈퇴 직후 30분 동안 쓰는 것 방지).

---

## 2. 대표 API 상세 명세: `POST /api/v1/routes/return` (AI 안심 귀가 조회)

수업 가이드의 **상세 명세 8칸**(호출 목적·요청 헤더·경로/쿼리·요청 본문·검증/권한·정상 응답·오류 응답·실행 규칙)으로 씁니다.

| # | 칸 | 명세 |
|---|---|---|
| 1 | **호출 목적** | 축제가 끝난 뒤 축제장(또는 사용자가 바꾼 출발 위치)에서 목적지까지 돌아가는 경로를 요청 (FR-R13 · 1차 시연 필수 · D-009). 호출 주체: 귀가 화면(직접), Route Agent(도구 `request_return_route` 경유) |
| 2 | **요청 헤더** | `Content-Type: application/json`(필수) · `X-Request-ID: req_…`(선택, 없으면 서버 생성) · `Authorization`(선택, 로그인 사용자면) |
| 3 | **경로·쿼리** | 없음 |
| 4 | **요청 본문** | 아래 '요청 필드 명세'와 예시 |
| 5 | **검증·권한** | 형식은 3절 `ReturnRouteRequest`(422). 같은 `request_id`·본문이면 기존 요청으로 응답하고 본문이 다르면 409. 새 요청은 축제 존재(404) → 출발이 축제 장소면 축제 좌표 있음(400 `FESTIVAL_LOCATION_UNKNOWN`) → 목적지 해석(400 `ROUTE_INVALID`)을 검사. 인증 없음(anonymous 허용), 요청 수 제한(429) |
| 6 | **정상 응답** | `200` 제한 시간 안에 끝남(`ready` 또는 `unavailable`) / `202` 아직 처리 중(`queued`·`processing`, 상태 조회 URL·짧은 수명 `access_token` 제공) |
| 7 | **오류 응답** | 아래 '오류 응답 표' |
| 8 | **실행 규칙** | **동기 대기 3초**(넘으면 그때까지의 상태로 202 반환, 처리는 계속) · **전체 처리 제한 10초**(넘으면 `route_status=timed_out` — 202 뒤에는 A05로 확인, 3초 안에 판정되면 504) (모두 임시) · 길찾기 어댑터 1회 호출 상한 TMAP 5초·카카오 3초(9-1절) · 1차 공급원 실패 때 **2차 공급원으로 1회** — **어떤 응답을 실패로 보고 넘길지는 10-3 표가 유일한 기준**(시간 초과·429·5xx·403 키 오류·TMAP `result.status` 12~14 등). 단 카카오(2차)는 **동기 3초 안에 끝날 때만** 결과를 줄 수 있으므로, 1차가 3초 안에 실패하지 않으면(예: 5초 시간 초과) 202 뒤 `ROUTE_SECONDARY_SYNC_ONLY`로 끝냄(5절) · 우리 요청 잘못(400/404/409/422)은 재시도 없음 · 같은 `request_id`는 처음 만든 `route_request_id`를 돌려줌(멱등) · 9절 |

**처리 순서:** ① 축제 존재·좌표 확인 → ② 목적지 확인(좌표 또는 카카오 장소 검색) → ③ 경로 키(`route_key`) 계산 → ④ 켜져 있는 복구 조치(동일 요청 병합 등) 적용 → ⑤ **길찾기 어댑터 호출: 1차 TMAP 대중교통 → 실패 시 2차 카카오맵 대중교통**(개발·시험은 모의, D-038) → ⑥ 결과 검증(출처·수단·시각·확인 가능한 통제) → ⑦ 경로 근거 붙이기 → ⑧ 추천 기준으로 점수 매겨 정렬 → ⑨ 기록(`route_requests`·`route_results`·지표)

**경로 근거(evidence) — 두 가지로 나눕니다 (D-024·D-033)**

| 근거 | 무엇을 고르는 데 쓰나 | 데이터 | 지역 |
|---|---|---|---|
| `area_evidence` 지역 선택 근거 | **어느 역·지역으로 갈지** (예: 삼각지역이 붐비니 이태원역) | 서울 실시간 인구 혼잡 구역(OA-21778), 교통 돌발(경찰청 전국·TOPIS 서울) | 혼잡 = 서울만, 돌발 = 전국 |
| `mode_evidence` 교통수단 선택 근거 | **무엇을 탈지** (만석 버스 대신 지하철) | 서울 버스 차내 혼잡(서울시 버스 도착정보 15000314의 혼잡 필드). 경로 속 정류장은 TMAP `stationID`(6자리)와 서울 버스 `arsId`(5자리)가 **다른 체계**라서(11/19 실호출) **정류장 이름+거리**로 연결합니다(상·하행은 노선·방향으로 구분). 2차 카카오맵 응답에는 정류장 ID가 없어 이때는 `unsupported` | 서울만. 서울 밖이면 `unsupported`, 공급원 실호출 전이면 `unverified`(0-3절). **경로 응답의 필수 부분이 아님**(없어도 경로는 제공) |

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
| `origin` | body | object | 아니요 | `{"type":"festival"}` | `{type:"festival"}`(축제 장소) 또는 `{type:"place", query 또는 lat+lng}` — **출발 위치를 사용자가 바꿀 수 있음**(S06, 09 마이그레이션 `origin_type`) | 출발지 |
| `destination` | body | object | 예 | 불가 | `query` 또는 `lat`+`lng` 중 **하나만** (`{type:"festival"}`은 출발이 사용자 장소일 때만) | 목적지 |
| `destination.query` | body | string | 조건 | 불가 | 1~100자 | 장소명·주소 |
| `destination.lat` / `lng` | body | number | 조건 | 불가 | 위도 33~39, 경도 124~132 | 좌표 |
| `travel_mode` | body | string | 아니요 | — | `transit`·`walk`·`car`·`taxi`, 기본 `transit` | 이동 수단(공급원 지원 범위 확인 후 축소 가능) |
| `route_preference` | body | string | 아니요 | — | 위 5개 값, 기본 `fastest` | 추천 기준 |
| `user_constraints` | body | object | 아니요 | `{}` | `with_child`·`wheelchair`: bool, `max_walk_m`: 0~5000 또는 null | 이동 조건 |
| `departure` | body | string | 아니요 | — | `now`만(예약 출발은 후속) | 출발 시각 |

**정상 응답 필드 명세 (200)** — 202는 아래 '처리 중 응답' 필드만 돌려줍니다

아래 경로 상세 필드는 `ready` 기준입니다. DB 모드에서 조회 토큰 만료 후 같은 `request_id`와 본문을 보내면 기존 `route_request_id`, `route_status=unavailable`, `completed_valid_route=false`, `error`(`code`, `message`, `retryable`), `updated_at`, `is_mock`, `notices`를 반환합니다.

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `route_request_id` | string | 불가 | `rr_` + ULID |
| `route_status` | string | 불가 | `queued`·`processing`·`ready`·`unavailable`·`rejected`·`timed_out` (`ready`만 경로 제공 성공) |
| `direction` | string | 불가 | `return` |
| `origin` / `destination` | object | 불가 | 출발(축제 DB 좌표)·도착(표시 이름, 해석 방법) |
| `route_preference` | string | 불가 | 요청한 추천 기준 |
| `route_candidates[]` | array | 빈 배열 가능 | `ready`일 때만 채움. 각 후보: `candidate_id`, `summary`, `duration_min`, `distance_m`, `walk_m`, `transfers`, `fare_krw`, `legs[]`(구간마다 `mode`·`path`=**`[[위도, 경도], …]`**·`stops[]`), `service_running`(boolean 또는 null, 5절), `score`, `area_evidence`, `mode_evidence` — **공급원이 주지 않는 값은 `null`, 만들지 않음** |
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
        "bus_crowding": { "status": "unverified", "reason": "정류장 이름+거리 연결 규칙 구현 전" }
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
| 503 | `ROUTE_OVERLOADED` | 과부하 보호로 거절(`route_status=rejected`, **경로 제공 성공 아님**) | 예(잠시 뒤) |
| 503 | `ROUTE_PROVIDER_UNVERIFIED` | 공급원 미연동·미검증(지금 상태) | 아니요 |
| 504 | `ROUTE_TIMEOUT` | 제한 시간 초과(`route_status=timed_out`) | 예(같은 `request_id`로 1회) |

**규칙**
- DB 모드에서 같은 `request_id`·본문을 재전송해도 최초 접수 시각과 `route_request_id`를 유지합니다. 조회 권한이 만료되면 `ROUTE_ACCESS_EXPIRED`로 새 접수를 안내합니다. 경로를 다시 조회하려면 새 `request_id`를 보냅니다. A05는 만료된 토큰에 401을 반환합니다.
- `user_constraints`(아이 동반·휠체어 등)를 검증할 데이터가 없으면 `constraint_status`에 `not_verifiable`로 표시하고, "확실히 이용 가능"이라고 답하지 않습니다 (FR-R10, BFCL NLD-13·21).
- 혼잡 자료가 지역 단위뿐이면 "가장 덜 붐비는 경로"라고 판정하지 않습니다. `area_evidence`로 구역 혼잡만 보여 줍니다 (BFCL NLD-22).
- 목적지 원문은 DB에 저장하지 않습니다. DB에는 **서버 비밀키를 섞은 HMAC 해시**만(30일), 화면 표시 이름은 **Redis에 24시간**만 둡니다(04 문서 7-0 보존표·마이그레이션 004 — 11/20 한태경 검토 반영).
- 어떤 공급원이 답했는지(`provider`·`provider_tier`)를 항상 남깁니다. 2차 공급원으로 답했다고 해서 자동 복구로 세지 않습니다(복구 판정은 7절).

### 2-2. 상태 조회: `GET /api/v1/routes/return/{route_request_id}` (A05)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 202로 접수된 귀가 요청의 처리 상태·결과 확인 (FR-R14). 화면 폴링, Route Agent(`get_route_request_status`) |
| 2 | 요청 헤더 | `X-Request-ID`(선택) · `X-Route-Access-Token: rrt_…`(필수, 요청 때 받은 조회 토큰, DB 모드에서 접수 후 10분 유효) |
| 3 | 경로·쿼리 | `route_request_id`: string, 필수, `^rr_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 형식 오류 422 · 토큰 없음·만료 401 · 다른 요청의 토큰 403 · 없는 ID 404. `ROUTE_STORE=db`는 접수 후 10분에 만료한다. 기본 메모리 모드는 토큰 누락을 검사한다(17-3) |
| 6 | 정상 응답 | **200** — 요청 처리가 실패했어도 '조회'는 성공이므로 200. 실패는 `route_status`·`error`로 알림(수업 가이드 S29). 경로는 `ready`일 때만 `route_candidates`에 담음 |
| 7 | 오류 응답 | 401 `UNAUTHORIZED` / 403 `FORBIDDEN` / 404 `ROUTE_REQUEST_NOT_FOUND` / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회는 멱등이며 DB 모드는 조회 중 만료된 TMAP 본문을 정리할 수 있음. 폴링 간격 2초·최대 5회(임시), 그 뒤엔 '확인 불가' 안내 |

**상태별 응답 예시 (모두 200)**

```json
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "queued", "completed_valid_route": false, "retry_after_s": 2 }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "processing", "completed_valid_route": false, "retry_after_s": 2 }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "ready", "completed_valid_route": true, "route_candidates": [ "…2절과 같은 모양…" ], "provider": "tmap", "queried_at": "…" }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false, "error": { "code": "ROUTE_UPSTREAM_ERROR", "message": "길찾기 공급원 오류예요.", "retryable": true }, "notices": ["지금은 경로를 확인할 수 없어요. 공식 안내를 확인해 주세요."] }
{ "route_request_id": "rr_01JD8Q3K2M", "route_status": "unavailable", "completed_valid_route": false, "error": { "code": "ROUTE_RESULT_EXPIRED", "message": "경로가 만료됐어요. 다시 조회해 주세요.", "retryable": true } }
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
| `retry_after_s` | int | — | `queued`·`processing` | 다음 조회까지 기다릴 초(임시 2초) | 없음(설정값) |
| `direction`·`festival_id`·`travel_mode`·`route_preference` | string | 불가 | `ready` | 요청 값 그대로 | `route_requests` |
| `route_candidates[]` | array | 빈 배열 가능 | `ready` | 2절 정상 응답 필드와 같은 모양 | `route_results.candidates` (카카오는 저장 안 함 → 5절 규칙) |
| `provider`·`provider_tier`·`queried_at` | string | 불가 | `ready` | 실제로 답한 공급원·순위·조회 시각 | `route_results` |
| `verification_status`·`constraint_status` | string·object | 불가 | `ready` | 2절과 같음 | `route_results.validation_status` · `route_results.evidence` |
| `error` | object | — | `unavailable`·`rejected`·`timed_out` | `{code, message, retryable}` — `ROUTE_UPSTREAM_ERROR`·`ROUTE_QUOTA_EXCEEDED`·`ROUTE_OVERLOADED`·`ROUTE_TIMEOUT`·`ROUTE_SECONDARY_SYNC_ONLY`·`ROUTE_PROVIDER_UNVERIFIED`·`ROUTE_RESULT_EXPIRED`·`ROUTE_NO_RESULT` | `route_requests.error_code` |
| `notices[]` | array | 빈 배열 | 항상 가능 | 확인 못 한 것·대체 안내 | 계산값 |
| `is_mock` | boolean | 불가 | 항상 | 모의 응답이면 true | `route_results.is_mock` |
| `updated_at` | string | 불가 | 항상 | 상태가 마지막으로 바뀐 시각 | 계산값 `completed_at` → `started_at` → `submitted_at` 중 처음 값 |

- 화면과 Route Agent는 `completed_valid_route=true`일 때만 경로를 안내합니다.
- **`ROUTE_RESULT_EXPIRED` — 현재 동작(코드 기준, 11/23):** TMAP 경로 결과는 서버 메모리에 **60초**만 둡니다. 60초가 지나 A05로 조회하면 `route_status=unavailable`, `error.code=ROUTE_RESULT_EXPIRED`, **`retryable=true`**("경로가 만료됐어요. 다시 조회해 주세요.")입니다(`real_routes.py`, 시험 `test_P11_expiry_removes_shared_tmap_body_for_all_ids`).
- **DB 모드(011, 시험 재실행 대기):** 유효 토큰 조회 시 24시간이 지난 TMAP 후보와 근거를 정리하고 `purged_at`을 기록합니다. 정리된 결과는 `ROUTE_RESULT_EXPIRED`와 `retryable=false`로 답합니다. 정상 흐름에서는 조회 토큰이 먼저 만료됩니다. 만료 뒤에는 새 `request_id`로 경로를 요청합니다.

### 2-3. 축제 검색: `GET /api/v1/festivals` (A02) — 필드 명세

| 필드 | 위치 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|---|
| `region` | query | string | 아니요 | `ALL` | 0-1절 지역 코드 | 시·도 |
| `date_from` / `date_to` | query | string(date) | 아니요 | null | `YYYY-MM-DD`, `date_from ≤ date_to`, 최대 366일 | 기간(겹치는 축제) |
| `q` | query | string | 아니요 | null | 1~50자 | 이름·장소 키워드 |
| `status` | query | string | 아니요 | null | `upcoming`·`ongoing`·`ended`·`cancelled` 중 하나 이상, **쉼표로 여러 값**(예: `ongoing,upcoming`). 모르는 값이 하나라도 있으면 422 | 진행 상태(11/23, 시험 `backend/tests/api/test_i13_multi_status.py`) |
| `bbox` | query | string | 아니요 | null | `minLng,minLat,maxLng,maxLat` | 지도 화면 범위 |
| `sort` | query | string | 아니요 | `start_date` | `start_date`·`-start_date`·`name`·`distance`(`bbox` 있을 때만). `-`는 내림차순 | 정렬 |
| `page` / `page_size` | query | int | 아니요 | 1 / 20 | page ≥ 1, page_size 1~100 | 페이지 |

응답(200): `{ "items": [ { "festival_id", "name", "region_code", "venue_name", "lat", "lng", "start_date", "end_date", "event_status", "thumbnail_url", "image_credit", "source", "last_synced_at" } ], "total": 37, "page": 1, "page_size": 20 }` — `thumbnail_url`은 TourAPI `firstimage2`(작은 크기), 없으면 null(화면 기본 이미지), `image_credit`은 출처 문구(아래 2-4 이미지 규칙) — 요청마다 외부 API를 부르지 않고 수집된 DB에서 답합니다. 오류: 422 `VALIDATION_ERROR`.

### 2-4. 축제 상세: `GET /api/v1/festivals/{festival_id}` (A03) — 필드 명세

| 필드 | 타입 | 빈값 | 설명 |
|---|---|---|---|
| `festival_id` | string | 불가 | `fst_…` |
| `name` · `region_code` | string | 불가 | 이름·지역 |
| `venue_name` · `address` | string | null 가능 | 장소·주소(원본에 없을 수 있음, 실호출 전) |
| `lat` / `lng` | number | null 가능 | 좌표가 없으면 귀가 요청 시 400 `FESTIVAL_LOCATION_UNKNOWN` |
| `start_date` / `end_date` | string | null 가능(미확정 일정) | 기간 |
| `event_status` | string | 불가 | `upcoming`·`ongoing`·`ended`·`cancelled`·`needs_review` |
| `overview` · `fee_text` · `homepage_url` · `image_url` | string | null 가능 | 소개·입장료·홈페이지·대표 이미지(공급원에 있을 때만, D-015·D-031). 입장료 = `usetimefestival`, 소개 = `detailCommon2`의 `overview`, **대표 이미지 = `firstimage`**(모두 실호출 확인, 10절) |
| `thumbnail_url` | string | null 가능 | 목록·지도 카드용 작은 이미지 = `firstimage2` |
| `image_copyright` | object | 이미지 없으면 null | `{type: "Type1"·"Type3", credit: "한국관광공사", modify_allowed: bool}` — `cpyrhtDivCd`에서 계산(아래 규칙) |
| `source` / `source_ref` / `last_synced_at` | string | 불가 | 출처·원본 ID·마지막 수집 시각 |

오류: 404 `FESTIVAL_NOT_FOUND`, 422 `VALIDATION_ERROR`(ID 형식).

**축제 대표 이미지 규칙 (D-031 확인 완료, 2026-11-20 TourAPI 원본 대조)**

| 항목 | 내용 |
|---|---|
| 공급원 | TourAPI `searchFestival2`(목록)·`detailCommon2`(상세)의 `firstimage`(원본)·`firstimage2`(작은 크기)·`cpyrhtDivCd`(저작권 유형). 주소는 `https://tong.visitkorea.or.kr/cms/resource/…` |
| 실제 확인 | 11/19 원본: **서울 10건·부산 6건 모두 이미지 있음, 저작권 유형 모두 `Type3`**. 표본이 16건뿐이라 전국 실제 비율은 수집 뒤 다시 셈(W98). 보완 공급원 전국문화축제표준데이터에는 **이미지 칸이 없음**(원본 컬럼 확인) |
| 저장 | 이미지 **파일은 복사하지 않고 주소만** `festivals.image_url`·`thumbnail_url`에 저장(DB 마이그레이션 003). 화면은 한국관광공사 서버에서 바로 불러옴 |
| 출처 표시 | 이미지가 보이는 모든 화면(목록 카드·상세·지도 팝업)에 `image_credit`("한국관광공사") 표시 |
| 변경 금지(Type3) | `Type3`(출처 표시 + 변경 금지)은 **자르기·필터·글자 얹기를 하지 않음**. 카드 비율이 달라도 잘리지 않게 전체를 보이게(`object-fit: contain`) 표시. **목록 카드는 `firstimage2`(작은 크기), 상세는 `firstimage`를 주소 그대로 쓰고 크기는 CSS로만 조절**(파일을 줄이거나 다시 저장하지 않음, 11/20 한태경). `Type1`만 잘라 쓰기 허용(`modify_allowed: true`). 화면 표기는 **"출처: 한국관광공사"**. 관광공사 문의는 하지 않기로 하고 이 처리안으로 확정(11/20 한태경) |
| 없을 때 | `image_url`·`thumbnail_url`이 비면 null로 주고 화면이 **기본 이미지**를 보여 줌(다른 축제·다른 출처 이미지로 채우지 않음) |
| 추가 사진 | 사진 여러 장(`detailImage2`)은 1차에서 쓰지 않음 |

### 2-5. 축제 가는 길: `POST /api/v1/routes/visit` (D-015)

귀가 API와 **같은 처리·검증·기록**을 쓰고 출발과 도착만 바꿉니다. `route_requests.direction='visit'`으로 기록합니다.

| 항목 | 귀가 (`/api/v1/routes/return`) | 가는 길 (`/api/v1/routes/visit`) |
|---|---|---|
| 출발 | **기본 축제장**(축제 DB 좌표), 사용자가 바꿀 수 있음 `origin` | 사용자가 입력한 장소 `origin: {query \| lat,lng}` |
| 도착 | 사용자가 입력한 목적지 `destination` | **기본 축제장**, 사용자가 바꿀 수 있음 `destination` |
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

RunStatus = Literal["queued", "running", "retrying", "succeeded", "failed"]   # 챗봇 작업 상태(7-6), RouteStatus와 별개

class AssistantContext(BaseModel):
    festival_id: str | None = Field(default=None, pattern=FESTIVAL_ID)
    route_request_id: str | None = Field(default=None, pattern=r"^rr_[0-9A-Za-z]{6,26}$")

class AssistantQueryRequest(BaseModel):                         # A06 (7-6)
    request_id: str = Field(min_length=8, max_length=64)       # 멱등 키
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(default=None, pattern=r"^cv_[0-9A-Za-z]{6,26}$")
    context: AssistantContext = AssistantContext()
    reference_date: str | None = None                          # YYYY-MM-DD, 없으면 서버 KST 오늘
```

- `RouteLoadSimulationRequest.upstream`에는 일부러 **시험용 어댑터만** 둡니다. 외부 길찾기 API에 부하를 거는 요청은 스키마 단계에서 막힙니다. **길찾기 무료 한도(TMAP 하루 10건, 카카오맵 하루 1,000건 — 11/19 한태경 조사)** 때문에도 부하 시험은 모의 응답으로만 합니다 (D-012, 회의록 ⚠8).
- `cache_state`·`repeat_group`·`run_index`는 강사 2차 의견("요청량·중복 비율·캐시 준비 상태·실행 횟수를 남겨야 같은 조건으로 다시 확인할 수 있어요")에 따라 넣었습니다.
- 숫자 상한(동시 요청 200, 지속 300초 등)은 **임시값**이며 9-1절 ⑤의 확정 시험(W96 → 12/04)에서 정합니다.
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

**JSON Schema와 출력 예시 — 필수 도구 6개 (v0.3.2, 강사 11/19 피드백 2)**

아래 6개는 BFCL 정답 이름·인자와 같습니다(4-7). 성공·실패 출력은 모두 4-5절 공통 형식이고, `data`는 감싸는 API의 응답 본문입니다. 도구 래퍼는 LLM이 만든 인자를 이 스키마로 한 번 더 검사하고, 어긋나면 API를 부르지 않고 `VALIDATION_ERROR`(retryable=false)를 돌려줍니다.

- **ID 형식(`fst_…`·`rr_…`·`inc_…`·`sim_…`)은 도구 스키마에 `pattern`으로 넣지 않습니다.** BFCL 평가는 가상 ID(`F01`·`RR02`·`INC-010`)를 쓰므로(4-7) 스키마에 넣으면 정답 호출이 막힙니다. 형식 검사는 감싸는 API의 Pydantic 검증(422 → 도구 출력 `VALIDATION_ERROR`)이 합니다.

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
- 실패 코드: `FESTIVAL_NOT_FOUND`(검색 단계로 돌아감) / `VALIDATION_ERROR` / `TOOL_TIMEOUT`.

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
- 폴링 상한: 2초 간격·최대 5회(9절 제한값). 넘으면 "확인 불가"로 답합니다.
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

- 숫자는 모양을 보이기 위한 가상 값입니다. 필드 뜻은 7-2절 표와 같습니다.
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
            "series": [ "…시간창마다 같은 모양(7-7절)…" ],
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

- `allowed`가 비어 있으면 Recovery는 `propose_recovery_action(decision="defer")`로 보류를 기록합니다(7-5 '허용 조치가 없음').
- 이 결과는 **조회 시점의 판단**입니다. 실제 실행 전에 정책 코드(`policy_gate`)가 A19에서 같은 규칙으로 다시 검사합니다(그 사이 상태가 바뀔 수 있음).
- 실패 코드: `INCIDENT_NOT_FOUND` / `INCIDENT_CLOSED` / `FORBIDDEN` / `TOOL_TIMEOUT`.


**JSON Schema와 출력 예시 — 최종 범위 도구 5개 (v0.3.2)**

성공·실패 출력은 6개와 같은 공통 형식이고, `data`는 감싸는 API(6-2절)의 응답 본문입니다. 외부 데이터가 '미지원·확인 불가'인 것은 **도구 실패가 아니라 `ok:true` + `data.status`** 로 옵니다(에이전트는 그대로 안내).

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

13개 도구 모두 JSON Schema가 있습니다(4-2절 추가 후보 5개는 BFCL 밖이라 문항을 늘릴 때 같이 씀). 구현할 때는 FastAPI·Pydantic 모델에서 생성한 스키마와 이 문서를 대조합니다.

### 4-7. BFCL 30문항과의 대조 (강사 일일 피드백 5)

**대조 기준:** BFCL 문서 = 팀 자체 평가 30문항(한다영, 2026-11-18 11:16 팀 문서함 공유본 — 저장소에는 없음, **API 설계 v0.1 기준**) ↔ 이 문서 v0.3. **합의 버전: 아직 없음** — 아래 '다름'을 한태경·한다영 님과 맞춘 뒤 "BFCL vX ↔ API v0.3"으로 이 칸에 기록합니다.

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
사용자 → POST /api/v1/assistant/query → 202 + run_id (작업 등록, 7-6) → 워커가 실행
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
- **막차:** TMAP 응답의 `service`(1 운행 중 / 0 운행 종료)로 `service_running`을 정합니다. **구간마다 대표 노선 `service`와 대체 노선 `lane[].service` 중 하나라도 1이면 그 구간은 운행 중**으로 보고, 응답 `legs[].line`에 확인된 운행 중 노선 이름(lane 포함, 예: '수도권1호선(급행)')을 보여 줍니다(11/20 한태경 재확인: 광화문→서울역 17시 경로2의 대표 노선 `수도권1호선`=0, 같은 구간 lane `수도권1호선(급행)`=1 — 시간대 문제가 아니라 재현됨). 모두 0인 구간이 있으면 `notices`에 '운행이 끝난 구간이 있어요'를 넣습니다. **그런 구간이 있는 후보는 유효 경로로 세지 않습니다** — 남은 후보가 없으면 `route_status=unavailable`, `ROUTE_NO_RESULT`('지금은 대중교통으로 갈 수 없어요'), `completed_valid_route=false`. 운행 정보가 없는 공급원(카카오)은 `service_running: null`로 두고 '막차 확인 불가'를 표시합니다.
  - **코드 반영(11/23, W36 일부):** TMAP 후보가 모두 운행 종료로 제외되면 카카오로 전환하지 않고 HTTP 200, `unavailable`, `ROUTE_NO_RESULT`, `retryable=false`로 반환합니다. TMAP 운행 정보가 누락되거나 해석할 수 없으면 종료가 확인된 구간이 없는 후보를 유지하고 `service_running=null`로 표시합니다. 대체 노선 키·노선명의 원본 필드는 [SPEC P13](../../backend/Doc/route-providers/SPEC.md#p13-tmap-후보-판정)에 확인 필요로 기록했습니다.
- **TMAP 약관 — 받은 데이터는 저장 후 24시간 넘게 쓸 수 없음:** 서버 메모리 캐시는 60초입니다(`valid_until`). 011 DB 모드는 TMAP 요약에 **24시간 안에 지우는** 정책을 적용합니다(DB 설계서 7-0절). Redis 연결과 주기 정리 실행 주체는 확인 중입니다. 원본 JSON 근거 파일도 24시간 안에 필드만 확인하고 지우며, 강사님 제출용 근거는 **키·좌표를 바꾼 합성 예시와 메타데이터**로 남깁니다.
- **카카오맵 결과는 A04의 동기 응답(3초 안)에서만 전달합니다.** 카카오 개발자 답변상 임시 캐싱도 허용되지 않아, 이미 202로 접수한 요청의 결과를 나중에 A05로 돌려줄 수 없습니다. 그래서 202 이후 1차(TMAP)가 실패하면 A05는 `route_status=unavailable`, 오류 `ROUTE_SECONDARY_SYNC_ONLY`('다시 조회해 주세요')로 답하고 사용자가 새로 요청하면 2차를 동기로 부릅니다. **이 문제가 풀리기 전에는 2차 공급원을 쓴 비동기 복구를 '복구 완료'로 세지 않습니다**(11/19 정예진 님 피드백).
- **카카오맵 응답은 저장·캐시하지 않습니다** — **카카오 공식 답변(데브톡 6/29, 11/20 한태경 확인): 다른 회사 지도 위 표시는 가능, 단 실시간 호출만·저장 불가.** 그래서 Redis 60초 캐시에도 카카오 결과는 넣지 않습니다(04 문서 7-0 ①). 011 DB 모드에서는 `route_requests`의 상태와 오류 코드만 기록하고 `route_results` 행은 만들지 않습니다(DB 설계서 6-1). 카카오 장소 검색 결과(이름·좌표)도 같은 규칙 — 목적지 라벨 `route:label`에는 **사용자가 입력한 문자열만** 넣습니다.
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
| A06 | POST | `/api/v1/assistant/query` (+ `GET /api/v1/assistant/runs/{run_id}`, `…/events` SSE) | 없음(선택 로그인) | 챗봇 질문을 **작업으로 등록 → 202 + `run_id`**, 워커가 에이전트 실행. 결과(`answer`·사용한 도구·근거)는 상태 조회로 (7-6) | FR-C01~C09, D-012, 강사 11/19 워커 구조 | 귀가 안내 한정 |
| A07 | GET | `/api/v1/festivals/{festival_id}/notices` | 없음 | 공식 운영 공지·교통통제(무정차·우회 등). `type` 필터 | FR-F05/F13 | 최종 |
| A08 | GET | `/api/v1/festivals/{festival_id}/facilities` | 없음 | **지도 표시용 주변 시설**(`categories` 여러 개, `radius_m`). **1차 10종**: 화장실·주차장 위치·병원·응급실·지하철역·버스 정류장·자전거 존·택시 승강장(**둘 다** 전국 통합 공급원·좌표가 확인되면 전국, 없으면 검증된 서울 공급원으로, **위치 안내만** — 실시간 대여 가능 수·택시 호출 제외)·맛집·주변 관광지 (**보류**: 물품보관함¹·약국²). 공급원 미확인 항목은 `status:"unverified"`(0-3절) | FR-F04/F11, **D-014** | 최종 |
| A09 | GET | `/api/v1/festivals/{festival_id}/weather` | 없음 | 축제 위치 날씨·예보(발표 시각 포함, 기상청 전국) | FR-F09, D-012 | 최종 |
| A10 | GET | `/api/v1/festivals/{festival_id}/crowd` | 없음 | 축제에 연결이 승인된 서울시 공식 구역 중 1km 이내 최대 3곳의 주변 지역 혼잡 | FR-F02/F14, D-010 | 보조(서울만) |
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
| **A32** | POST | `/api/v1/auth/signup` | 없음 | 회원 가입(이메일·비밀번호·닉네임·출생연도·성별, 1-1절) → `users`·`profiles` 생성 | FR-A(회원), D-037 | 최종 |
| **A33** | POST | `/api/v1/auth/login` | 없음 | 로그인 → Access JWT + Refresh Token (1절) | D-037 | 최종 |
| **A34** | POST | `/api/v1/auth/refresh` | Refresh Token | 토큰 갱신(교체 방식) | D-037 | 최종 |
| **A35** | POST | `/api/v1/auth/logout` | user | 로그아웃(Refresh 폐기, `jti` 차단) | D-037 | 최종 |
| **A36** | GET | `/api/v1/me/festival-preferences` | user | 내 축제 취향·온보딩 상태 조회. 취향 값 5개(11/20 팀장): `family_relaxed`(가족 + 한가로운) · `friends_activity`(친구 + 액티비티) · `couple_photo`(연인 + 포토존) · `pet`(반려견과 함께하는 축제 — 11/20 기획서 수정으로 아기 동반은 뺌) · `solo`(혼자 즐기기), 복수 선택 | 기획서 최신본 5.18 (신규 필수: 맞춤 추천) | 최종 — 상세 작성(6-4-2) |
| **A37** | PUT | `/api/v1/me/festival-preferences` | user | 취향 선택·변경·건너뛰기 저장 (6-4-2) | 〃 | 최종 — 상세 작성 |
| **A38** | GET | `/api/v1/festivals/recommended` | 선택(취향 계정 기준) | 맞춤 추천(필터·페이지·`recommendation_reason`, **규칙 기반**, 실제 축제 DB에 있는 것만) | 〃 | 설계안 |
| **A39** | GET | `/api/v1/festivals/popular` | 없음 | 실제 참여 지표(상세 조회·관심 추가) 기반 인기 | 〃 | 설계안 |
| **A43~A50** | — | `/api/v1/users/search`, `/api/v1/friend-requests`(+`/{id}/{action}`), `/api/v1/me/friend-requests`, `/api/v1/me/friends`(+`/{user_id}`), `/api/v1/me/blocks/{user_id}` | user | **친구 검색(닉네임 정확히 일치, 친구 코드 없음)·신청·수락·거절·취소·목록·삭제·차단·차단 해제** (6-4-3) | FR-COM12~14 | 최종 — 담당 권오현 |
| **A51** | POST | `/api/v1/assistant/visit-course` (결과는 A06-1) | 없음(선택 로그인) | **AI 방문 코스**: 동행 유형·시간에 맞춘 축제 안 코스, 코드가 실존·운영 시각·동선 검증 (6-6) | FR-P01·P03 | 최종 — 권오현(API)·한다영(에이전트) |
| **A52~A54** | POST/PATCH/POST | `/api/v1/admin/notices`, `/{notice_id}`, `/{notice_id}/review` | admin | 공식 공지 등록·수정·승인/반려, 이력 추가만 (6-6) | FR-O06·D05 | 최종(적용 시) — 신유빈 |
| **A55~A56** | POST/PATCH | `/api/v1/admin/festivals`, `/{festival_id}` | admin | 축제 직접 등록·수정·게시, 변경 이력 (6-6) | FR-D12·O10 | 최종 — 권오현 |
| **A57~A65** | — | `/api/v1/festivals/{id}/companion-posts`, `/api/v1/companion-posts`(+`/{id}`, `/applications`, `/meeting-place`, `/{action}`), `/api/v1/companion-applications/{id}/{action}` | 공개·user | **동행**: 모집 목록·작성·신청·승인(정원 잠금)·만남 장소·종료/취소 (6-4-4) | FR-COM01~11·18·19 | 최종 — 권오현 |
| **A66~A73·WS** | — | `/api/v1/me/chat-rooms`, `/api/v1/chat-rooms`(+`/invitations`, `/{action}`, `/messages`, `/read`), `/api/v1/ws-tickets`, `WS /api/v1/ws/chat` | user | **채팅**: 방 목록·1:1·단체방·초대·수락·퇴장·방장 승계·메시지 이력·읽음, WebSocket 전송(DB 저장 뒤 ACK) (6-4-5) | FR-COM09·15~17·20 | 최종 — 권오현 |
| **A74~A80** | — | `/api/v1/me/notifications`(+`/read`), `/api/v1/reports`, `/api/v1/admin/reports`, `/api/v1/me/profile`, `/api/v1/me/companion-activity`, `DELETE /api/v1/me` | user·admin | **알림·신고·마이페이지·탈퇴** (6-4-6) | FR-COM21~24 | 최종 — 권오현 |
| **A42** | GET | `/api/v1/festivals/trending` | 없음 | **지금 핫한 축제**: 외부 사이트 크롤링 순위·언급 수(LLM 없음), 우리 축제와 규칙으로 연결된 것만 (6-2) | 11/20 팀장 결정(기획서 FR 추가 필요) | 최종 — 담당 신유빈 |
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
- **동행·채팅(신규 필수):** A57~A73으로 상세 작성(6-4-4·6-4-5, 채팅은 WebSocket), 권한은 11/20 권한 기준안(04 문서 7-1). **채팅 경로 규칙:** `/chat-rooms/{room_id}/invitations`·`/read`·`/messages`를 `/{action}`(A69)보다 **먼저 등록**하고, `action`은 `accept`·`decline`·`leave`만 받음(그 밖은 404). **친구는 A43~A50으로 상세 작성(6-4-3).** 친구 검색은 **닉네임 정확히 일치**(닉네임은 겹치지 않음, 친구 코드 없음, 이메일·전화번호 검색 안 함 — 11/20 결정, 009).

¹·² 물품보관함·약국: **보류**(D-021, 11/18). 11/18 회의 지도 목록에 없어 넣지 않기로 함. 다만 BFCL `get_facilities`의 `category` 값(`locker`·`pharmacy`)에는 이미 들어 있어서, 평가 기준을 바꾸지 않도록 값은 남기고 호출되면 `status:"unsupported"`로 응답합니다.

**상세 명세 작성 범위 (v0.3, 11/20 제출본)**

| 수준 | API | 상태 |
|---|---|---|
| 8칸 상세 + 필드 명세 + 예시 | A04(2절), A05(2-2), **A06(7-6)**, **A14(7-7)**, **A16(7-8)**, **A18(7-9)**, A19(7-4), **A21(7-10)** | 작성 (v0.3.2에서 굵은 5개 추가) |
| 필드 명세 표 | A02(2-3), A03(2-4), A15(7-2), A20(7-1) | 작성 |
| 표 형식 상세(요청·응답·규칙·오류) | **A32~A35 인증(1-1절)** | 작성 (v0.3.3 교차 검토 반영) |
| 8칸(공통 규칙 + API별 차이) + 응답 필드·원본 필드 표 | **A07~A13, A17, A22~A31 (6-2절, v0.3.2 추가)** | 작성 — A17은 후속(구현 전 501) |
| A01 상태 | `GET /api/v1/health` → 200 `{status, db, redis, version}` (하나라도 실패면 503) | 작성 |
| 표 형식 상세(요청·응답·권한·규칙·오류) | **A36~A41 추천(6-4-2), A42 핫한 축제(6-2), A43~A50 친구(6-4-3), A51~A56 방문 코스·공지·축제 관리(6-6)** | 작성 (v0.3.3) |
| 표 형식 상세 | **A57~A80 동행·채팅·알림·신고·마이페이지·탈퇴(6-4-4~6-4-6)** | 작성 (v0.3.3) |

수업 가이드는 "최종 제출에는 구현하기로 확정한 API 전체의 명세"를 요구합니다. **v0.3.2에서 채운 것**(강사 11/19 피드백 2): 1차 필수 A06·A14·A16·A18·A21의 8칸 상세와 필드 표, A05 응답 필드 표, 필수 도구 6개(`search_festivals`·`get_festival`·`get_route_request_status`·`get_incident`·`get_route_metrics`·`list_allowed_actions`)의 JSON Schema와 성공·실패 출력(4-6). 그리고 A07~A13·A17·A22~A31 상세(6-2절)와 최종 범위 도구 5개 JSON Schema(4-6 ⑦~⑪)도 채웠습니다. **v0.3.3에서 채운 것**: 인증 A32~A35(1-1), 추천·핫한 축제·친구·동행·채팅·알림·신고·마이페이지·방문 코스·공지·축제 관리 A36~A80(6-2·6-4·6-6). **남은 것**: A17은 후속 기능이라 구현 전 501, 실제 코드·화면 연결은 구현 단계(6-5절 실행 범위 A~D).

**공통 오류 코드**

| 코드 | HTTP | 의미 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 입력 형식 오류(Pydantic) |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 | 인증 없음·만료 / 권한 부족·타인 자원 |
| `RATE_LIMITED` | 429 | 요청 수 제한 초과 |
| `FESTIVAL_NOT_FOUND` | 404 | 없는 축제 ID |
| `FESTIVAL_LOCATION_UNKNOWN` | 400 | 출발 또는 도착이 축제 장소인데 축제 좌표가 없음 |
| `NICKNAME_TAKEN` | 409 | 닉네임이 이미 있음(대소문자 무시, A32·A78 — DB `uq_profiles_nickname`) |
| `IDEMPOTENCY_CONFLICT` | 409 | 같은 `request_id`에 다른 본문 |
| `ROUTE_INVALID` | 400 | 목적지 해석 실패·지원하지 않는 수단 |
| `ROUTE_PROVIDER_UNVERIFIED` | 503 | 경로 공급원 미연동·미검증(현재 상태) |
| `ROUTE_TIMEOUT` | 504 | 경로 조회 제한 시간 초과 |
| `ROUTE_UPSTREAM_ERROR` | 502 | 외부 길찾기 API 오류(429·5xx 포함, 원본 코드는 로그에) |
| `ROUTE_QUOTA_EXCEEDED` | 503 | 길찾기 공급원 일일 한도 소진(1차·2차 모두) — 경로 확인 불가 + 공식 안내 |
| `ROUTE_QUEUE_TIMEOUT` | 504 | 내부 대기열에서 제한 시간 초과 |
| `ROUTE_OVERLOADED` | 503 | 과부하 보호로 거절(`route_status=rejected`, 경로 제공 성공 아님) |
| `ROUTE_REQUEST_NOT_FOUND` | 404 | 없는 `route_request_id` (A05) |
| `MEET_AT_INVALID` | 400 | 동행 만남 시각이 축제 기간 밖이거나 과거 (A58) |
| `OWN_POST` / `APPLICATION_EXISTS` / `POST_CLOSED` / `CAPACITY_FULL` / `APPLICATION_NOT_PENDING` | 403 / 409 / 409 / 409 / 409 | 동행 신청·승인 (A60·A62) |
| `NOT_FRIENDS` | 403 | 친구가 아닌 사람과 채팅방 (A67·A68) |
| `ROOM_READ_ONLY` / `STORE_FAILED` | WS `error` | 종료된 방에 전송 / DB 저장 실패(ACK 없음) |
| `COURSE_OUT_OF_PERIOD` | 400 | 방문 코스 시작 시각이 축제 기간 밖 (A51) |
| `DUPLICATE_FESTIVAL` | 409 | 같은 이름·기간·장소 축제가 이미 있음 → 검토 대기열로 (A55) |
| `NOT_IMPLEMENTED` | 501 | 아직 구현하지 않은 후속 기능 (A17) |
| `QUEUE_ITEM_NOT_FOUND` / `ALREADY_REVIEWED` | 404 / 409 | 없는 검토 항목 / 이미 처리한 검토 항목 (A24) |
| `ALREADY_FRIENDS` / `REQUEST_PENDING` / `BLOCKED` / `REQUEST_NOT_PENDING` | 409 | 친구 API(A44·A46): 이미 친구 / 대기 중 신청 있음 / 차단 관계 / 이미 처리된 신청 |
| `ROUTE_NO_RESULT` | 200 (A04·A05의 `error`, `route_status=unavailable`) | 공급원이 "경로 없음"으로 답함(TMAP `result.status` 11~14, 카카오 `NO_RESULTS` 등 — 10-3)이거나 TMAP 후보가 모두 운행 종료로 제외됨(5절). `retryable=false` |
| `INCIDENT_NOT_FOUND` / `INCIDENT_CLOSED` | 404 / 409 | 없는 사건 / 이미 닫힌 사건에 결정 기록 (A19) |
| `DUPLICATE_PLAN` | 409 | 같은 사건에 실행 중인 조치가 있음 (A19) |
| `SIMULATION_RUNNING` | 409 | 이미 실행 중인 부하 시험 (A20) |
| `SIMULATION_NOT_FOUND` | 404 | 없는 `simulation_id` (A16·A21·A31) |
| `RUN_NOT_FOUND` | 404 | 없는 챗봇 작업 `run_id` (A06-1·A06-2) |
| `ROUTE_RESULT_EXPIRED` | 200 (A05의 `error`) | **현재:** 메모리 60초 캐시 만료, `retryable=true` → 다시 조회. **DB 모드:** 24시간 정리된 TMAP 결과는 `retryable=false`(2-2) |
| `ROUTE_ACCESS_EXPIRED` | 200 (A04·A25 POST의 `error`) | DB 모드에서 접수 10분 이후 동일 요청 재전송. 기존 `route_request_id`를 반환, `retryable=false`(2절) |
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
| 웹 크롤링 | ⚠ **A42 '지금 핫한 축제'에만** 사용(11/20 팀장 결정) | 축제 기본 정보·경로·실시간 정보는 계속 공식 API·공공데이터만. 크롤링은 약관·`robots.txt`가 허용하는 사이트의 이름·순위만(6-2 A42) |
| SNS 후기 현장 요약 | ⏸ 2차(나중에) | 메인 기능 아님 |
| 정류장 눌러 버스 혼잡 보기, 자전거 추가 기능(따릉이 실시간 등) | ⏸ 나중에 | D-011, 회의록 ⚠9 |
| 물품보관함·약국 지도 표시 | ⏸ 보류 | D-021 (회의 지도 목록 밖) |

### 6-2. 나머지 API 상세 명세 (v0.3.2 — 11/19~20 실호출 필드 기준)

1차 필수가 아닌 API도 **구현하기로 정한 범위 전체**를 여기서 정합니다(수업 가이드 "구현하기로 확정한 API 전체의 명세"). 원본 필드 이름은 한태경 님 정리표(키가 들어 있어 비공개 — 공유본 `Docs/Step 2/evidence/README.md`, 11/20)와 `evidence/` 원본 기준입니다.

#### 6-2-0. 외부 데이터 조회 API 공통 규칙 (A07~A10, A26~A30)

같은 모양을 반복하지 않도록 공통 8칸을 한 번만 적습니다. API별 표에는 **다른 점만** 적습니다.

| # | 칸 | 공통 명세 |
|---|---|---|
| 1 | 호출 목적 | 축제 화면·지도·에이전트 도구가 축제 주변 정보를 봄 |
| 2 | 요청 헤더 | `X-Request-ID`(선택). 인증 없음(공개) |
| 3 | 경로·쿼리 | `festival_id`: 필수, `^fst_[0-9A-Za-z]{6,26}$`. 쿼리는 API별 표 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 형식 422 → 축제 없음 404 `FESTIVAL_NOT_FOUND` → 축제 좌표가 필요한 API인데 없으면 **200 + `status:"unavailable"`, `FESTIVAL_LOCATION_UNKNOWN`**(화면 전체를 오류로 만들지 않음) → 그 지역에 공급원이 없으면 **200 + `status:"unsupported"`** (0-2·0-3절) |
| 6 | 정상 응답 | **200** `{festival_id, status, coverage, source, observed_at, is_mock, items[] 또는 data}`. `status`: `ok`·`stale`·`unavailable`·`unsupported`·`unverified` (0-3절) |
| 7 | 오류 응답 | 404 `FESTIVAL_NOT_FOUND` · 422 `VALIDATION_ERROR` · 429 `RATE_LIMITED`. **외부 공급원 오류는 HTTP 오류로 돌려주지 않고** 200 + `status:"unavailable"` + `error{code:SOURCE_HTTP_ERROR·SOURCE_RESULT_ERROR, retryable}` |
| 8 | 실행 규칙 | 실시간 값은 Redis `ext:*` 캐시 먼저(9-1 ④), 없으면 공급원 1회 호출(시간 제한 3초, 일시 오류 1회 재시도 — 9-1). **HTTP 200이라도 본문 결과 코드를 확인**(서울 `RESULT.CODE`, 경찰청 `resultCode`, TAGO `resultCode` 99, 지하철 `status`). XML 공급원(경찰청·응급실·TOPIS)은 어댑터가 JSON으로 바꿈. 관측 시각이 갱신 주기 ×2보다 오래면 `stale`. 정적 데이터(시설 위치)는 수집된 DB에서만 답함 |

#### A07. 공식 공지·교통 통제 `GET /api/v1/festivals/{festival_id}/notices`

| 항목 | 명세 |
|---|---|
| 쿼리 | `type`: 선택, `operation`·`traffic_control`·`no_stop`·`bus_detour`·`road_closure` / `active_only`: bool, 기본 true(지금 효력 있는 것만) |
| 출처 | 운영자가 등록·승인한 공지 + 서울 TOPIS 통제(10번, 서울만) |
| 규칙 | `approval_status='approved'`만 보여 줌(미승인은 경로 차단에도 안 씀). 축제 공지가 없어도 `status:"ok"`, `items:[]` — "확인할 수 있는 공지 자료가 없어요" |

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
| 쿼리 | `categories`: 선택, 쉼표 구분, 기본 1차 10종 전부(`toilet,parking,hospital,emergency,subway_station,bus_stop,bike_zone,taxi_stand,food,attraction`). `locker`·`pharmacy`는 허용값이지만 항상 `unsupported`(D-021) / `radius_m`: 100~3000, 기본 1000 / `limit_per_category`: 1~50, 기본 20 |
| 규칙 | 축제 좌표 필요. 거리순 정렬. **카테고리마다 상태를 따로** `categories_status`로 줌(한 공급원이 실패해도 나머지는 보여 줌). 카카오 로컬(`food`·`attraction`)은 **저장 조건 미확인이라 DB에 넣지 않고 요청 때 중계**만 함(11절) |

| 카테고리 | 공급원 (11/19 실호출) | 위치 필드 | 추가로 보여 주는 값 | 상태 |
|---|---|---|---|---|
| `toilet` | 행정안전부 공중화장실 15155058 | 응답 위경도 필드 이름 **확인 필요**(주소 `LCTN_ROAD_NM_ADDR`는 확인) | 개방 시간 `OPN_HR`, 관리 기관 `MNG_INST_NM` | 위경도 확인 전 `unverified` |
| `parking` | 전국주차장정보표준데이터 | `latitude`·`longitude`(비어 있으면 제외) | 공영/민영 `prkplceSe`, 면수 `prkcmprt`, 관리번호 `prkplceNo`(A27 연결용) | ok |
| `hospital`·`emergency` | 국립중앙의료원 `getEgytLcinfoInqire`(XML) | `latitude`·`longitude` | 기관 `dutyName`, 구분 `dutyDivName`, 기관 ID `hpid` | ok |
| `subway_station` | 카카오 로컬 `SW8`(중계, 11/19 호출은 `FD6`만 — `SW8`은 문서 기준) | `x`·`y` | 역 이름 | 카카오 저장 조건 확인 전 중계만 |
| `bus_stop` | 서울 밖 TAGO 정류소(`nodeid`·`citycode`) / 서울은 **서울시 버스정류소 위치정보 파일(OA-15067)을 DB에 적재**(1순위 — ✅ 11/20 확인: 11,236곳, 좌표 WGS84 경위도라 변환 없음, `NODE_ID` 9자리 → `source_item_id`, `ARS_ID` 5자리(앞 0 유지, 문자로 저장), 서울 버스도착 API 104건과 번호 모두 일치, 공공누리 1유형), 실시간 보완은 서울 정류소정보조회 `getStaionsByPosList`(승인됨, 1,000건/일, 2순위) — 11/20 한태경 | TAGO `gpslati`·`gpslong`(문서 기준 — 11/19 호출은 `nodeid`·`citycode`만 기록) | 정류소 ID(A26 연결용) | 서울 `unverified` |
| `bike_zone` | 행안부 전국 공영자전거 대여소 15126639 | `lat`·`lot` | 대여소 이름 | ok (실시간 대수는 제외 — 6-1) |
| `taxi_stand` | 전국택시승강장표준데이터 15139230 | **위경도 없음** → 주소 `lctnRoadNmAddr`를 좌표로 바꿔 적재 | 정차면수 `taxExclsScplcCnt`, 상세 위치 `dtlPstn` | 변환 방법 확정 전 `unverified`(11절) |
| `food`·`attraction` | 카카오 로컬 `FD6`(11/19 확인: 광화문 1km 1,961건)·`AT4`(문서 기준)(중계) | `x`·`y` | 장소 이름·분류 | 중계만 |

| 응답 필드 | 타입 | 설명 | DB |
|---|---|---|---|
| `categories_status` | object | 카테고리별 `ok`·`unverified`·`unsupported`·`unavailable` | — |
| `items[]` | array | `{facility_id, category, name, lat, lng, distance_m, address, source, ref_code, extra}` | `facilities`(카카오 중계분은 DB 없음, `facility_id`=`kakao:<id>`) |

#### A09. 날씨 `GET /api/v1/festivals/{festival_id}/weather`

| 항목 | 명세 |
|---|---|
| 쿼리 | 없음 |
| 규칙 | 축제 좌표 → **기상청 격자(nx, ny)로 변환**(변환식은 기상청 참고문서, 11/19 서울 60,127·부산 97,74로 확인). `base_time`은 1시간 전 정시. 캐시 10분 |
| 지금 범위 | **초단기실황(현재 날씨)만 실호출 확인.** 예보(`forecast`)는 단기예보 API를 아직 부르지 않아 `unverified` — 담당 한태경, W36 전(11/26) |

| 응답 필드 | 타입 | 원본(기상청) | 설명 |
|---|---|---|---|
| `observed_at` | string | `baseDate`+`baseTime` | 발표 시각 |
| `temperature_c` | number | `T1H` | 기온 |
| `precipitation_mm` | number | `RN1` | 1시간 강수량 |
| `precipitation_type` | string | `PTY` 0~7 | `none`·`rain`·`rain_snow`·`snow`·`drizzle`·`drizzle_snow`·`snow_flurry`(코드 0·1·2·3·5·6·7) |
| `grid` | object | `nx`·`ny` | 변환 결과 |
| `forecast` | object | — | `{status:"unverified"}` (위 '지금 범위') |

#### A10. 혼잡 구역 `GET /api/v1/festivals/{festival_id}/crowd` (서울만)

| 항목 | 현재 동작 |
|---|---|
| 쿼리 | 없음 |
| 실제/모의 | 기본 `mock`은 저장된 모의 자료와 `X-Mock`을 사용합니다. `CROWD_PROVIDER=real`은 `is_mock:false`를 반환하며 승인된 매핑만 서울시 `citydata_ppltn`에 요청합니다. |
| 반경 | 승인된 공식 구역 경계까지 최단거리를 잽니다. 구역 안과 경계 위는 0m입니다. 1km 이내에서 가까운 순으로 최대 3곳을 선택하며, 동률이면 구역 코드순입니다. |
| 미지원 | 서울 밖·좌표 없음·승인 매핑 없음·반경 내 승인 구역 없음은 각각 `outside_seoul`·`missing_coordinates`·`no_approved_mapping`·`no_nearby_areas`를 `unsupported_reason`에 넣고 `status:"unsupported"`를 반환합니다. |
| 구역 실패 | 일부가 실패하면 `nearby_areas`에 실패 상태와 오류를 남기고 관측값이 있는 구역을 제공합니다. 모두 실패하면 200 `unavailable` 및 `SOURCE_RESULT_ERROR`입니다. HTTP 200 본문 오류, 요청 구역 불일치, 형식 오류, 공급원 대체 평균도 조회 실패로 처리합니다. |
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

`notices`는 관측값을 **주변 지역 혼잡(서울시 실시간 도시데이터)**으로 안내하고 구역 이름·축제에서의 거리·기준 시각·출처와 **“행사장 안 혼잡과 다를 수 있어요”**를 제공합니다. 공급원의 4주 대체 평균은 응답과 캐시에서 제외합니다. 성별·연령 비율도 응답과 저장에서 제외합니다. 시연 후보와 실연동 승인 절차는 [W89 명세](../../backend/Doc/seoul-crowd/SPEC.md)에 있습니다.

#### A11~A13. 관심 축제 (로그인 필요)

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
| `festival_id`·`name`·`region_code`·`start_date`·`end_date`·`event_status`·`thumbnail_url` | string | `festivals` |
| `saved_at` | string | `favorites.created_at` |

#### A17. 지연 위험 예측 `GET /api/v1/admin/route-metrics/risk` — **후속(FR-H19), 1차 구현 안 함**

| 항목 | 명세 |
|---|---|
| 권한 | operator·service |
| 쿼리 | `window`: `5m`·`15m`(기본)·`1h` / `horizon`: `5m`(기본)·`15m` |
| 지금 동작 | 구현 전에는 **501 `NOT_IMPLEMENTED`**("예측 기능은 아직 없어요"). 도구 `predict_route_delay_risk`도 이 응답을 그대로 안내(BFCL NLD-03) |
| 구현 시 응답(계획) | `{risk_level: low·medium·high, method: "trend", horizon, signals[] {metric, value, threshold}, evidence_refs[] (rqm_…)}` — 추세 규칙(예: 대기열 4배 증가 → high)이며 학습 모델 아님 |
| 담당·날짜 | 신유빈 · W48 정책 확정 뒤(12/04) 구현 여부 결정 |

#### A22. 혼잡 공급원 장애 모의 `POST /api/v1/admin/simulations/crowd` (보조)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 목적 | 서울 혼잡 API(A10) 장애를 **모의 어댑터로** 재현해, 혼잡이 없어도 축제·귀가 기능이 유지되는지 시험(FR-H20) |
| 2 | 헤더 | `Authorization: Bearer <operator 이상>` · `Idempotency-Key`(필수) |
| 4 | 본문 | `{mode: "http_500"·"stale"·"body_error", duration_s: 5~300}` |
| 5 | 검증·권한 | 401 / 403 / 운영 환경 403 `SIMULATION_DISABLED` / 이미 켜져 있으면 409 `SIMULATION_RUNNING` / 422 |
| 6 | 정상 | 202 `{fault_id, mode, ends_at}` |
| 8 | 실행 규칙 | 실제 서울시 API에는 아무것도 안 함 — A10 어댑터가 Redis `fault:crowd`(TTL = `duration_s`)를 보고 모의 응답을 냄. 감지되면 `failure_domain=crowd_upstream` 사건으로 기록. **귀가 부하 시험(A20)과 별개**이고 대표 시연 아님 |

#### A23. 축제 수집 작업 이력 `GET /api/v1/admin/ingestion-jobs`

| 항목 | 명세 |
|---|---|
| 권한 | admin만(401/403) |
| 쿼리 | `source_id`, `status`(`running`·`success`·`partial`·`failed`), `from`·`to`(기본 최근 7일), `page`·`page_size` |
| 응답 `items[]` | `{job_id, source_id, status, started_at, ended_at, scanned, inserted, updated, rejected, error}` — DB `ingestion_jobs` 그대로. `error`는 페이지별 오류 요약(키 값 없음) |
| 규칙 | 조회만. 수집 실행은 API가 아니라 정기 작업(워커 주기 실행, 매일 06:00 임시)이 함 |

#### A24. 중복·충돌 축제 검토 `GET`·`POST /api/v1/admin/festivals/review-queue`

| 항목 | GET (목록) | POST (처리) |
|---|---|---|
| 권한 | admin | admin |
| 입력 | 쿼리 `approval_status`(기본 `pending`)·`reason`(`duplicate`·`conflict`·`missing_location`·`date_unclear`)·`page` | 본문 `{queue_id: int, decision: "approve"·"reject", value?: object, note?: string≤200}` |
| 응답 | 200 `{items[] {queue_id, festival_id, festival_name, reason, proposed_value, approval_status, created_at}, total, …}` | 200 `{queue_id, approval_status, applied: bool}` |
| 오류 | 401 / 403 / 422 | 401 / 403 / 404 `QUEUE_ITEM_NOT_FOUND` / 409 `ALREADY_REVIEWED` / 422 |
| 처리 규칙 | — | `approve`면 `value`(없으면 `proposed_value`)를 `festivals`에 반영하고 `festival_change_history`(`actor='admin'`)에 한 줄. `reject`면 축제는 그대로. 처리자·시각을 `reviewer`·`reviewed_at`에 기록. 축제를 물리 삭제하지 않음(숨김은 `review_status='hidden'`) |

#### A25. 축제 가는 길 `POST /api/v1/routes/visit` + `GET /api/v1/routes/visit/{route_request_id}`

**A04·A05와 8칸이 같고 아래만 다릅니다**(2-5절 표).

| 항목 | A04 귀가와 다른 점 |
|---|---|
| 요청 본문 | **`origin`(필수)**: 사용자 출발지(`{query}` 또는 `{lat, lng}`, 3절 `VisitRouteRequest`). **`destination`(선택)**: 기본은 축제 장소 `{type:"festival"}`, 입구·주차장 등으로 바꿀 수 있음(S06). 출발·도착이 둘 다 축제 장소일 수는 없음(DB CHECK, T43g) |
| 처리 | 같은 어댑터(TMAP → 카카오)·검증·기록. `route_requests.direction='visit'` |
| 출발 시각 | `now`만 (축제 시작 시각 맞춤 출발은 후속) |
| 복구·부하 | **부하 시험 대상 아님**(대표 시연은 귀가만). 단 같은 작업 풀을 쓰므로 귀가 부하 때 같이 느려질 수 있고, 그 지표는 `direction`으로 나눠 봄 |
| 상태 조회 | `GET /api/v1/routes/visit/{id}` — A05와 같은 응답(2-2절)·같은 토큰 규칙 |
| 오류 | A04와 같음. 출발지를 못 찾으면 400 `ROUTE_INVALID` |

#### A26. 주변 대중교통 실시간 도착 `GET /api/v1/festivals/{festival_id}/transit`

| 항목 | 명세 |
|---|---|
| 쿼리 | `mode`: `all`(기본)·`subway`·`bus` / `radius_m`: 100~1000, 기본 500 / `limit`: 정류장·역 최대 10 |
| 공급원 | 지하철: 서울 지하철 실시간(서울만) / 버스: **서울 = 서울시 버스도착정보 15000314, 서울 밖 = TAGO** |
| 규칙 | 주변 역·정류장 목록은 A08 위치 데이터에서 찾고, 도착 정보만 실시간으로 부름. 지하철 `barvlDt`가 0이어도 도착 전일 수 있어 **`arvlMsg2` 문구를 함께** 줌. 서울 버스 `itemCount`는 0으로 와서 **건수로 쓰지 않음**. TAGO `resultCode` 99는 일시 오류로 재시도. 캐시 30초 |

| 응답 `stations[]` | 타입 | 원본 | 설명 |
|---|---|---|---|
| `type`·`station_id`·`name`·`lat`·`lng`·`distance_m` | — | A08 위치 | 역·정류장 |
| `status` | string | — | 역·정류장마다 `ok`·`unsupported`(서울 밖 지하철)·`unavailable` |
| `arrivals[].line` | string | 지하철 `subwayId`·`trainLineNm` / 서울 버스 `rtNm` / TAGO `routeno` | 노선 |
| `arrivals[].direction` | string | 지하철 `updnLine` | 상·하행 |
| `arrivals[].eta_s` | int | 지하철 `barvlDt` / TAGO `arrtime` / 서울 버스는 `arrmsg1` 문구에서 계산(못 하면 null) | 도착까지 초 |
| `arrivals[].message` | string | 지하철 `arvlMsg2` / 서울 버스 `arrmsg1` | 공급원 문구 그대로 |
| `arrivals[].remaining_stops` | int | TAGO `arrprevstationcnt` | 남은 정류장 |
| `arrivals[].crowding` | string | 서울 버스 `reride_Num1`(`rerdie_Div1`=4일 때: 3 `여유`·4 `보통`·5 `혼잡`) | **서울 버스만**, 교통수단 선택 근거(D-033). 나머지 null |
| `observed_at` | string | 지하철 `recptnDt` / 수신 시각 | |

- 수도권 노선(인천·경기 역) 포함 여부는 미확인(부평 미호출) → 서울 역만 `ok`로 표시, 담당 한태경 · W36 전(11/26).
- 서울 버스 정류장 **위치**: TAGO는 서울 0건이라 쓰지 않고, **1순위 서울시 버스정류소 위치정보 파일(OA-15067)을 `facilities`(`category=bus_stop`)에 적재**, 2순위 서울 정류소정보조회 `getStaionsByPosList`(좌표 근접, 이미 승인, 1,000건/일)로 정했습니다. **파일 확인 ✅(11/20 한태경, `evidence/usage/서울정류장파일_확인_20261120.md`)**: 11,236곳, WGS84 경위도(변환 불필요), `NODE_ID` 9자리·`ARS_ID` 5자리(앞자리 0 유지), 서울 버스도착 API `arsId`·`stId` 104건 모두 일치 → '파일로 가까운 정류장 찾기 → 같은 `ARS_ID`로 실시간 도착 조회'가 성립. 적재 전에는 서울 버스 도착을 `unverified`로 — 적재는 수집 구현 때(한태경).

#### A27. 공영주차장 빈자리 `GET /api/v1/festivals/{festival_id}/parking` (서울만)

| 항목 | 명세 |
|---|---|
| 쿼리 | `radius_m`: 300~3000, 기본 1000 |
| 규칙 | 서울 시영주차장 실시간(122곳)만. **응답에 위경도가 없어** 전국주차장표준데이터와 주차장 이름·주소로 연결한 것만 거리 계산·지도 표시. 연결 안 된 곳은 `lat`·`lng` null, 목록 뒤쪽에 "위치 미확인"으로. 서울 밖 → `unsupported`(위치만 A08 `parking`). 캐시 1분 |

| 응답 `items[]` | 타입 | 원본 | 설명 |
|---|---|---|---|
| `name`·`address` | string | `PKLT_NM`·`ADDR` | |
| `total_spaces`·`parked` | int | `TPKCT`·`NOW_PRK_VHCL_CNT` | |
| `available` | int | 계산 `TPKCT − NOW_PRK_VHCL_CNT`(음수면 0) | 빈자리 |
| `updated_at` | string | `NOW_PRK_VHCL_UPDT_TM` | 공급원 갱신 시각 |
| `lat`·`lng`·`distance_m` | number | 연결된 `facilities`(전국주차장표준 `prkplceNo`) | 연결 안 되면 null |

#### A28. 주변 교통 돌발 `GET /api/v1/festivals/{festival_id}/traffic-incidents`

| 항목 | 명세 |
|---|---|
| 쿼리 | `radius_m`: 500~10000, 기본 2000 / `type`: 선택 `accident`·`construction`·`event`·`control` |
| 공급원 | 경찰청 교통돌발(UTIC, 전국, XML) + 서울 TOPIS(서울 보강, XML) |
| 규칙 | 경찰청은 지역 필터 없이 **전국 전체가 와서 서버가 반경으로 거름**(11/19: 전국 118건). 날짜가 "2026년 11월 19일 16시 22분" 문자열이라 어댑터가 ISO 시각으로 바꿈. TOPIS 좌표 `grs80tm_x/y`는 GRS80 TM → 위경도 변환. 두 공급원에 같은 사건이 있으면 위치 100m·시간 겹침으로 하나로 합침(임시). 캐시 1분. 경로 근거(`area_evidence.traffic_incidents`)도 이 데이터를 씀 |

| 응답 `items[]` | 타입 | 원본 | 설명 |
|---|---|---|---|
| `type` | string | 경찰청 `incidenteTypeCd`(1 사고 `accident`·2 공사 `construction`·3 행사 `event`·5 통제 `control`) / TOPIS `acc_type` | |
| `title` | string | 경찰청 `incidentTitle` / TOPIS `acc_info` | |
| `lat`·`lng`·`distance_m` | number | 경찰청 `locationDataY`·`locationDataX` / TOPIS 변환값 | |
| `start_at`·`end_at` | string | 경찰청 `startDate`·`endDate` / TOPIS `occr_*`·`exp_clr_*` | null 가능 |
| `source` | string | `police_incident`·`seoul_topis` | |

#### A29. 방문 집중 예측 `GET /api/v1/festivals/{festival_id}/visit-forecast`

| 항목 | 명세 |
|---|---|
| 쿼리 | `days`: 1~30, 기본 7 |
| 공급원 | 한국관광공사 관광지 집중률 예측 15128555 + 지역별 관광 수요 강도 15151868 |
| 규칙 | **실시간 혼잡이 아니라 상대값(0~100) 예측**이므로 다른 이름·색으로 표시(D-018). 축제 장소와 이름이 맞는 관광지(`tAtsNm`)가 있을 때만 `forecast`를 주고, 없으면 `forecast.status:"unsupported"`("이 축제 장소의 예측 자료가 없어요"). 관광 수요 강도는 **시군구 코드와 지표 코드를 함께 넣어야** 값이 옴(문서엔 선택값, 11/19 확인). 하루 1회 수집해 `realtime_snapshots`(`visit_forecast`·`region_demand`)에 저장 |

| 응답 필드 | 타입 | 원본 | 설명 |
|---|---|---|---|
| `forecast.attraction` | string | `tAtsNm` | 연결된 관광지 이름 |
| `forecast.days[]` | array | `baseYmd`·`cnctrRate` | `{date, rate}` rate는 0~100 상대값 |
| `region_demand` | object | `tarSjrnDsIxCd`·`tarSjrnDsIxNm`·`tarSjrnDsIxVal`·`baseYm`·`signguNm` | `{indicator, value, base_month, area_name}` 월 1회 갱신(지난달까지) |

#### A42. 지금 핫한 축제 `GET /api/v1/festivals/trending` (11/20 팀장 결정 — 크롤링, LLM 사용 안 함)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 지금 외부에서 화제가 되는 축제를 보여 줌(축제 탭 '지금 핫한 축제'). **A39 인기(우리 서비스 안 조회·관심 수)와 다름** — A42는 외부 사이트의 순위·언급 수 |
| 2 | 요청 헤더 | `X-Request-ID`(선택). 인증 없음 |
| 3 | 경로·쿼리 | `region`: 선택(0-1절 코드, 기본 `ALL`) / `limit`: 1~20, 기본 10 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 형식 422. 공개 |
| 6 | 정상 응답 | 200 `{items[], crawled_at, source, status}`. 크롤링이 한 번도 성공하지 않았으면 `status:"unavailable"`, `items:[]`. 마지막 성공이 12시간보다 오래면 `status:"stale"`(목록은 그대로 보여 줌) |
| 7 | 오류 응답 | 422 `VALIDATION_ERROR` / 429 `RATE_LIMITED` (크롤링 실패는 HTTP 오류가 아니라 `status`로 알림) |
| 8 | 실행 규칙 | 요청 때 크롤링하지 않고 **수집된 DB(`festival_trends`)에서만** 답함. 우리 축제와 **규칙으로 연결된 것만**(`match_status='matched'`), 게시된·안 끝난 축제만. 정렬: 최근 크롤링의 `source_rank` 오름차순 → 없으면 `mention_count` 내림차순 |

**수집(크롤링) 규칙**

| 항목 | 내용 |
|---|---|
| 주기 | `TREND_CRAWL_SCHEDULE` 6시간마다(임시, 9-1) — 워커 주기 작업, 이력은 A23 `ingestion_jobs`에 같이 남김 |
| 대상 사이트 | **미정** — 축제 순위·인기 목록을 공개하는 사이트 후보 중 **이용약관·`robots.txt`가 수집을 허용하는 곳만**. 담당 신유빈(추천 담당) · 확정 11/25(제안, 담당 확인 필요) |
| 가져오는 것 | 축제 이름·순위·언급 수·페이지 주소만. **본문·이미지·작성자·댓글은 저장하지 않음** |
| 예의 | 요청 간격 1초 이상, 한 번에 목록 페이지 몇 개만, 서비스 이름을 밝힌 User-Agent, 실패 시 재시도 1회(9-1 ②) 후 다음 주기 |
| 우리 축제와 연결(LLM 없음) | 이름 정규화(공백·괄호·"제n회" 제거) 후 `festivals.title`과 일치 + 축제 기간이 크롤링 시점과 겹침 → `matched`. 후보가 2개 이상이면 `ambiguous`, 없으면 `unmatched` — 둘 다 화면에 안 나옴. 연결 규칙 이름을 `match_rule`에 남김 |
| 보존 | `festival_trends` 30일(04 문서 7-0) |
| 기획서 | 기획서·WBS에 아직 없는 기능 → 정예진(기획서 FR 추가)·신유빈(WBS 작업 추가) 반영 필요 |

| 응답 `items[]` | 타입 | 빈값 | DB |
|---|---|---|---|
| `rank` | int | 불가 | 응답 안 순서(1부터) |
| `festival_id`·`name`·`region_code`·`start_date`·`end_date`·`thumbnail_url`·`image_credit` | — | thumbnail null 가능 | `festivals` |
| `source_rank`·`mention_count` | int | 둘 중 하나 null 가능 | `festival_trends` |
| `crawled_at`·`source_url` | string | 불가 | `festival_trends` |

#### A30. 데이터 공급원 상태 `GET /api/v1/data-sources`

| 항목 | 명세 |
|---|---|
| 권한 | 공개(화면의 '미지원' 안내용). 키 정보는 절대 안 보여 줌 |
| 쿼리 | `region_code`: 선택 — 주면 그 지역에서 켜진 공급원만 |
| 응답 `items[]` | `{source_id, name, scope, enabled_region_codes[], is_realtime, refresh_s, status, last_success_at}` — DB `data_sources`(`key_site`·`notes`는 빼고) |
| 규칙 | `status`가 `verified`가 아니면 화면은 그 정보를 '준비 중'으로. 조회만, 캐시 10분 |

#### A31. 부하 시험 상태 `GET /api/v1/admin/simulations/{simulation_id}`

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
| `scenario`·`comparison_arm`·`concurrency`·`offered_rps`·`duration_s`·`unique_route_keys`·`cache_state`·`fault`·`seed`·`repeat_group`·`run_index`·`upstream` | — | null 가능 | 같은 이름 |
| `limits_version`·`code_version` | string | 불가 | 결과 JSON·`code_version` (9-1) |
| `phases[]` | array | 빈 배열 | `{phase, offered_requests, valid_route_rate, error_rate, p50_ms, p95_ms}` — `route_query_metrics` 구간별 |
| `incidents[]` | array | 빈 배열 | `{incident_id, detected_at, final_mode}` — `incident_logs`·`incident_outcomes` |
| `started_at`·`ended_at` | string | ended null 가능 | |
| `result_ref`·`report_ref` | string | null | 결과 JSON·보고서 위치(GitHub) |
| `error` | object | null | `failed`일 때 `{code, message}` |


### 6-3. 추가 기능 범위·작업 순서 (강사 11/19 피드백 5)

최신 기획서가 **필수(Must)** 로 정한 추가 기능(맞춤 추천, 동행·친구·채팅)은 그대로 존중합니다. 다만 **API 목록만 있는 것과 상세 계약이 끝난 것을 나누고**, 핵심 귀가·자동 복구 일정과 같은 표에 놓아 겹치는 곳을 보입니다. 날짜·담당은 WBS(GitHub main, 11/20) 그대로입니다.

**① 추가 기능별 계약 상태와 일정**

| 기능 | 기획 FR | API | 계약 상태(11/20) | 명세 확정 | DB | 구현 (담당) | 검증 |
|---|---|---|---|---|---|---|---|
| 맞춤 추천(취향·추천·인기·둘러보기·최신) | FR-REC01~16 | A36~A41 | **상세 작성**(6-4: 분류 규칙·점수·A36~A41) | W112 · 11/20 → 남은 상세는 W123 전(11/30) | **DDL·시험 완료**(005 `user_festival_preferences`·`festival_tags`·`festival_engagement_daily`, T29~T31) | **신유빈**(11/20 GitHub 협업 규칙 `recommendations.py` 담당) — WBS W124·W125는 아직 R03이라 수정 필요 | W128 12/17–18 |
| **지금 핫한 축제(새)** | 기획서에 없음(추가 필요) | **A42** | **상세 작성**(6-2) | 11/20 | `festival_trends`(04 문서 마이그레이션 004, 시험 T27) | 신유빈(제안 — 추천 담당) · WBS 작업 추가 필요 | W128 |
| 동행 모집·신청·승인·만남 장소·종료 | FR-COM01~11·18~19 | **A57~A65** | **상세 작성**(6-4-4, 정원 잠금 승인·재신청 규칙) | 11/20 | **DDL·시험 완료**(007 `companion_posts`·`companion_applications`·`meeting_places`, T36·T37) | W115 12/03–07, W117 12/09–10 (R03) | W128 |
| 친구 검색·신청·삭제·차단 | FR-COM12~14 | **A43~A50** | **상세 작성**(6-4-3). 친구 추천은 범위 밖(후보) | 11/20 | **DDL·시험 완료**(005 `friend_requests`·`friendships`·`user_blocks`, 닉네임 중복 금지 009, T32~T33·T43) | W118 12/03–04 (R03) | W128 |
| 채팅(동행방·1:1·단체)·채팅 탭 | FR-COM09·15~17·20 | **A66~A73 + WebSocket** | **상세 작성**(6-4-5) · 전송 방식 = WebSocket(11/20 협업 규칙) | 11/20 | **DDL·시험 완료**(007 `chat_rooms`·`chat_members`·`chat_messages`, T37·T38·T41) | W116 12/03–08 (R03 권오현 — 협업 규칙도 권오현), W119 12/09–10 (R03) | W128 |
| 알림·프로필·신고·탈퇴 | FR-COM21~24 | **A74~A80** | **상세 작성**(6-4-6) | 11/20 | **DDL·시험 완료**(007 `notifications`·`reports`·`chat_admin_access`, T39·T40) | W122 12/15–16 (R03) | W128 |
| 화면 | — | — | — | — | — | W120 12/11–14, W121 12/15–16, W126 12/07–08, W127 12/09–11 (R05 이수언) | — |

**② 아직 정하지 않은 기술·숫자와 결정 시점**

| 미정 항목 | 선택지 | 결정할 사람 | 결정 시점(제안) | 이유 |
|---|---|---|---|---|
| 채팅 전송 방식 | ✅ **WebSocket으로 결정**(11/20 GitHub 협업 규칙, 강사 자료 9쪽 '주고받기가 잦으면 WebSocket'과 같음) | 권오현 | 결정됨 | — |
| 채팅·동행 보존 기간 숫자 | ✅ **동행 종료 뒤 3일, 친구 채팅 30일**(11/20 팀장 답. 정예진 안 7일보다 나중 결정) | 신유빈 | 결정됨 | 04 문서 7-0 ⑤ |
| 추천 점수 규칙 | ✅ **초안 작성**(6-4-1 ③, `rec-0.1`: 태그 0.5·날짜 0.2·완성도 0.2·관심 0.1) + 분류 = 규칙 후보 → LLM 검증(11/20 사용자 결정) | 신유빈(추천 담당)·정예진 | 가중치 확정 W124 전(12/02) | W124 입력 |
| 신규 13개 테이블 권한(위치·친구 관계·채팅 열람, 차단·탈퇴 뒤 처리) | ✅ **기준안 합의**(11/20 정예진 권한 정책안 + 팀장 답: 채팅은 **참여자·관리자**가 봄, 친구는 친구 추가 기능으로) — 04 문서 7-1 | 권오현(DDL)·한태경(시험) | ✅ DDL·시험 완료(005·007, 11/20) | 강사 DB 피드백 5 |

**③ 핵심 일정과 겹치는 곳 (WBS 날짜 그대로 놓았을 때)**

| 기간 | 핵심 귀가·자동 복구 | 추가 기능 | 겹침 |
|---|---|---|---|
| 11/26–12/02 | W36 귀가 API(11/26–27, R03·R06), W41 관심(11/27–12/02, R03), W101(11/27–12/02, R03), W90 시설(11/27–12/03, R06) | W114·W123 DB(12/01–02, R03) | R03 3~4개 |
| **12/03–12/08** | W102 축제 관리 API(12/03–07, R03), W82(12/04–08, R03), W28(~12/03, R03) / **W96 계측·W48 정책 확정(~12/04, R06)** | **W115·W116·W118·W124·W125 (모두 R03)** | **R03 동시 7~8개 — 현실적으로 어려움** |
| 12/09–12/14 | W49 감지·W50 복구 구현(12/09–14, R06), W65 AWS(12/07–10, R06) | W117·W119(12/09–10, R03) | R06은 핵심에 집중 필요 |
| 12/15–12/18 | W51 B0/B1/A1 비교(12/15–17), W52 결과서(12/16–18) | W122(12/15–16), W128 E2E(12/17–18) | 검증 주간이 겹침 |

**④ 제안 — 팀 결정 필요 (확정 아님)**

1. **순서는 핵심 먼저**: 귀가 API(W36) → 계측(W96)·정책(W48)이 12/04에 끝난 뒤 추가 기능 구현을 본격 시작. 추가 기능 안에서는 **추천(규칙 기반, 외부 의존 없음) → 친구 → 동행 → 채팅** 순으로 위험이 낮은 것부터.
2. **R03 집중 해소**: 추천(W124·W125) → 신유빈은 **11/20 GitHub 협업 규칙에서 이미 반영됨**(WBS 수정만 남음). 남은 R03 집중(W115·W116·W118·W102·W82, 12/03–08)은 그대로라 채팅 W116에 R06 보조를 실제 배정하는 것을 계속 제안. R06은 같은 기간 W48·W96이 있어 12/05 이후 조건.
3. 채팅 전송 방식(WebSocket)·보존 숫자(3일·30일)는 11/20에 정해졌고, 추가 기능 DB는 005·007로 설계·시험까지 끝냈습니다. WBS의 W114·W123(DB 적용)은 실제 개발 DB에 마이그레이션을 적용하는 일로 남습니다.
4. 이 제안은 PM(정예진)·WBS 담당(신유빈)과 W112에서 확정하고, 결정 결과를 WBS와 이 표에 반영합니다.


### 6-4. 맞춤 추천과 친구 — 상세 명세 (v0.3.3, 11/20)

기획서 FR-REC01~16·FR-COM12~14와 11/20 팀 결정(취향 5개, 권한 기준안)을 기준으로 합니다. DB는 04 문서 마이그레이션 005(시험 T29~T33).

#### 6-4-1. 축제를 5가지 취향으로 분류하는 방법 (규칙 후보 → LLM 검증)

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

- **LLM 비용 상한:** 새로 들어오거나 바뀐 축제만, 하루 최대 300건(임시 `TAG_LLM_DAILY_MAX`, 9-1). 축제당 후보만 보내므로 전국 첫 분류도 며칠에 나눠 처리. 모델은 팀 LLM 결정(W27 전, 11/25)을 따르고 `model`·`prompt_version`을 행마다 남깁니다.
- **LLM이 실패하면**(시간 초과·형식 오류) 후보는 `candidate`로 남고 추천에 쓰지 않습니다 — 추천이 줄어들 뿐 틀린 추천은 나오지 않습니다.
- **원문이 짧아 근거가 없는 축제가 많으면** 그 취향 추천이 비어 보일 수 있습니다 → 화면은 '전체 축제 보기'로 안내(FR-REC15). 실제 비율은 수집 뒤 확인(W123, 12/01–02).

**③ 점수 (A38, FR-REC08)** — 가중치는 임시값 `REC_WEIGHTS_VERSION = rec-0.1`

`점수 = 0.5 × 태그 일치 + 0.2 × 날짜 적합 + 0.2 × 정보 완성도 + 0.1 × 관심 저장 보정`

| 항목 | 계산 (0~1) |
|---|---|
| 태그 일치 | 고른 취향마다 필요한 태그를 모두 가진 비율(여러 취향을 고르면 가장 높은 값). 취향 `pet`(반려견과 함께하는 축제)을 고르면 그 취향 점수는 `pet_allowed`가 검증된 축제만 1, 없으면 0 — 반려견은 **별도 칸 없이 취향 값 하나**(기획서 FR-REC03, 11/20 15:32 main) |
| 날짜 적합 | 진행 중 1.0, 14일 안 시작 0.7, 30일 안 0.4, 그 뒤 0.1. 종료·취소·비공개는 **후보에서 제외** |
| 정보 완성도 | 대표 이미지·소개·장소 좌표·입장료 중 있는 비율 |
| 관심 저장 보정 | 최근 7일 관심 추가 수의 순위 백분위 |

동점이면 시작일 → `festival_id` 순으로 고정합니다(같은 요청이면 같은 순서).

#### 6-4-2. 추천 API (A36~A41) — 담당 신유빈(11/20 GitHub 협업 규칙)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A36** `GET /api/v1/me/festival-preferences` | — | `{scenarios[], onboarding_status, updated_at}` (행이 없으면 `onboarding_status:"pending"`) | user, 본인만(RLS, T29e) | 401 |
| **A37** `PUT /api/v1/me/festival-preferences` | `{scenarios: [5개 중 0~5개], skip: bool}` — 반려견은 `scenarios`에 `pet`으로 | 200 A36과 같은 모양 | user. `skip=true` 또는 빈 배열 → `skipped`(FR-REC04), 1개 이상 → `completed`. 바꾸면 다음 A38부터 다시 계산(FR-REC05) | 401 / 422(모르는 값 — DB도 거부, T29a) |
| **A38** `GET /api/v1/festivals/recommended` | 쿼리 `scenarios`(비로그인일 때 쉼표 구분, 로그인이면 저장된 취향이 기본) · `region` · `date_from`·`date_to` · `page`·`page_size`(≤50) | `{items[] {festival_id, name, region_code, start_date, end_date, event_status, thumbnail_url, image_credit, score, applied_tags[], recommendation_reason[]}, score_version, total, page, page_size, fallback}` | 선택 로그인. `recommendation_reason`은 **검증된 태그의 근거 문장으로 만든 고정 문구**(요청 때 LLM 안 씀). 예: "공식 안내에 '야간 포토존 운영'이 있어요". 일치 축제가 없으면 `items:[]`, `fallback:"all_festivals"`(FR-REC15). 추천됐다고 관심 저장하지 않음(FR-REC14) | 422 |
| **A39** `GET /api/v1/festivals/popular` | `region` · `page` | `{items[] {…카드 필드, views_7d, favorites_7d}, window:"7d", fallback}` | 공개. 최근 7일 `festival_engagement_daily` 합. **사람 1명 하루 1회**만 셈(Redis `eng:{festival_id}:{day}`에 세션 HMAC 집합 → 하루 끝에 숫자만 DB로, 테스트·봇 User-Agent 제외). 지표가 20건 미만이면 `fallback:"recent"`로 A41 목록 | 422 |
| **A40** `GET /api/v1/festivals/discover` | `region` · `page` · `seed`(선택) | `{items[], seed, page}` | 공개. 섞는 순서 = `hash(seed, festival_id)`. `seed` 없으면 서버가 `날짜+세션`으로 만들어 돌려줌 → 같은 seed면 페이지를 넘겨도 순서 고정(FR-REC11) | 422 |
| **A41** `GET /api/v1/festivals/recent` | `region` · `page` | `{items[] {…, published_at}}` | 공개. `festivals.published_at` 최신순. 재수집해도 최초 공개일 유지(FR-REC13) | 422 |

- 모든 목록은 승인·게시된 예정/진행 축제만(종료·취소·비공개 제외), 없는 축제를 만들지 않음. A36~A41 고정 경로는 `/festivals/{festival_id}`보다 먼저 등록(6절 라우터 규칙).

#### 6-4-3. 친구 API (A43~A50) — 담당 권오현(11/20 GitHub 협업 규칙 `community/friends.py`)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A43** `GET /api/v1/users/search` | 쿼리 `nickname`(2~12자) — **정확히 일치만**(대소문자 무시, 일부만 치면 0건) | `{items[] {user_id, display_name, friendship_status: none·pending_sent·pending_received·friends}}` 최대 1건(닉네임은 겹치지 않음) | user. **친구 코드 없음, 닉네임으로 검색**(11/20 결정, DB `app_find_user_by_nickname` T43d·e). 나이·성별은 돌려주지 않음. 이메일·전화번호로는 검색 안 됨. 나를 차단한 사람·내가 차단한 사람은 안 나옴 | 401 / 422 / 429(분당 20회) |
| **A44** `POST /api/v1/friend-requests` | `{to_user_id}` | 201 `{request_id: "frq_…", status:"pending"}` | user. 나 자신(DB 거부, T32c)·이미 친구·차단 관계면 거부. 반대 방향으로 대기 중 신청이 있으면 **그 신청을 바로 수락으로 처리**(중복 신청 대신) | 401 / 404 / 409 `ALREADY_FRIENDS`·`REQUEST_PENDING`·`BLOCKED` |
| **A45** `GET /api/v1/me/friend-requests` | 쿼리 `box`: `received`(기본)·`sent` | `{items[] {request_id, user_id, display_name, status, created_at}}` | user, 당사자만(RLS, T33c) | 401 |
| **A46** `POST /api/v1/friend-requests/{request_id}/{action}` | `action`: `accept`·`reject`(받은 사람) / `cancel`(보낸 사람) | 200 `{request_id, status}` | 정해진 사람만. `accept`는 **한 트랜잭션**으로 신청 상태 변경 + `friendships` 1행(작은 ID가 `user_a`) | 401 / 403 / 404 / 409 `REQUEST_NOT_PENDING` |
| **A47** `GET /api/v1/me/friends` | `page` | `{items[] {user_id, display_name, since}}` | user, 당사자만 | 401 |
| **A48** `DELETE /api/v1/me/friends/{user_id}` | — | 204 (친구가 아니어도 204, 멱등) | user | 401 |
| **A49** `PUT /api/v1/me/blocks/{user_id}` | — | 200 `{blocked: true}` | user. **한 트랜잭션**: 차단 추가 + 친구 관계 삭제 + 대기 중 신청 `cancelled`. 차단당한 사람은 차단 사실을 볼 수 없음(T33d). 두 사람의 1:1 방은 `closed`, 공동 단체방·동행방은 남음(서로의 메시지 숨김은 범위 밖) | 401 / 422(자기 자신) |
| **A50** `DELETE /api/v1/me/blocks/{user_id}` | — | 204 | user. 차단을 풀어도 **친구 관계는 자동 복원 안 함**(권한 기준안) | 401 |

- 쓰기는 두 사람의 행이 함께 바뀌므로 API 서버가 `noldaga_service` 역할로 한 트랜잭션에서 처리하고(앱 역할은 조회만 — T33b), 그 전에 FastAPI가 소유권·차단 상태를 검사합니다(04 문서 3절).
- 동행 승인은 친구 추가로 이어지지 않습니다(친구 추가 API로만).
- **친구 추천**(같이 동행한 사람, 취향이 비슷한 사람 등)은 기획서에 없어 **이번 범위에서 뺍니다.** 후보로만 남기고 넣을지는 정예진(기획)이 정합니다 — 넣으면 개인정보 노출(누가 누구와 동행했는지) 검토가 먼저 필요합니다.



#### 6-4-4. 동행 API (A57~A65) — 담당 권오현(`community/companions.py`), 화면 `companions/`(정예진)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A57** `GET /api/v1/festivals/{festival_id}/companion-posts` | `status`(기본 `open`)·`page` | `{items[] {post_id, author_display_name, meet_at, capacity, approved_count, age_pref, gender_pref, memo, status}}` | 공개. **정확한 만남 장소는 안 줌**(FR-COM01·08) | 404 / 422 |
| **A58** `POST /api/v1/companion-posts` | `{festival_id, meet_at, capacity(1~10, 작성자 제외), age_pref?, gender_pref?, memo?(≤500)}` | 201 `{post_id, room_id}` | user. `meet_at`은 **축제 기간 안의 미래 시각만**(400 `MEET_AT_INVALID`, FR-COM03). 한 트랜잭션: 동행방(`companion`) 만들기 + 작성자 방장 입장 + 글 저장, 만남 장소는 처음 '미정'(FR-COM04) | 401 / 400 / 404 / 422 |
| **A59** `GET /api/v1/companion-posts/{post_id}` | — | A57 한 건 + `my_application_status` | 공개 | 404 |
| **A60** `POST /api/v1/companion-posts/{post_id}/applications` | `{message?(≤200)}` | 201 `{application_id, status:"pending"}` | user. 본인 글·마감·종료 글 거부, **대기·승인·거절 기록이 있으면 재신청 불가, 취소했으면 재신청 가능**(DB 부분 UNIQUE, T36a). 작성자에게 알림 | 401 / 403 `OWN_POST` / 409 `APPLICATION_EXISTS`·`POST_CLOSED` |
| **A61** `GET /api/v1/companion-posts/{post_id}/applications` | `status` | `{items[] {application_id, applicant_display_name, applicant_age, applicant_gender, message, status, created_at}}` — `applicant_age`는 서버가 출생연도로 계산한 나이(올해 − 출생연도), 출생연도 자체는 보내지 않음. 대기·승인 중인 신청만, 탈퇴자는 '알 수 없음' — 신청 화면에서 '닉네임·나이·성별이 작성자에게 보여요'를 미리 알림(S07) | **작성자만**(나이·성별은 DB `app_applicant_profile`, T43b·c)(신청자는 A59의 자기 상태만, RLS T37c) | 401 / 403 |
| **A62** `POST /api/v1/companion-applications/{application_id}/{action}` | `action`: `approve`·`reject`(작성자) / `cancel`(신청자, 승인 전만) | 200 `{application_id, status, post_status}` | `approve`는 **한 트랜잭션**: `SELECT … FOR UPDATE`로 글을 잠그고 정원 확인 → 신청 승인 → `approved_count+1`(정원 넘으면 DB가 거부, T36c) → 방 멤버 입장 → 시스템 메시지 → 정원이 차면 `full`(FR-COM06·07). 승인·거절 알림. **친구는 자동 추가 안 함**(FR-COM13) | 401 / 403 / 404 / 409 `CAPACITY_FULL`·`APPLICATION_NOT_PENDING` |
| **A63** `PUT /api/v1/companion-posts/{post_id}/meeting-place` | `{name, address?, lat?, lng?, guide?}` (좌표 없이 이름·주소만도 가능 — 지도 오류 시 텍스트) | 200 `{post_id, updated_at}` | **작성자만**. 바꾸면 시스템 메시지 + 참여자 알림 `meeting_place_changed`(FR-COM10·11) | 401 / 403 / 422 |
| **A64** `GET /api/v1/companion-posts/{post_id}/meeting-place` | — | `{name, address, lat, lng, guide, updated_at}` 없으면 `{status:"undecided"}` | **작성자·승인 참여자만**(RLS, T37a·f) | 401 / 403 |
| **A65** `POST /api/v1/companion-posts/{post_id}/{action}` | `action`: `end`(종료)·`cancel`(사전 취소) | 200 `{post_id, status}` | 작성자만. 만남 시각 + 12시간(임시 `COMPANION_AUTO_END_H`)이 지나면 자동 `end`. 종료·취소 → 동행방 **읽기 전용**(`read_only_at`) → '지난 동행'(FR-COM18·19) → 3일 뒤 메시지 정리(04 문서 7-0) | 401 / 403 / 409 |

#### 6-4-5. 채팅 API (A66~A73 + WebSocket) — 담당 권오현(`community/chat.py`, `realtime/chat_socket.py`), 화면 `chats/[roomId]/`·`friends/`(정예진)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A66** `GET /api/v1/me/chat-rooms` | `filter`: `all`·`companion`·`friend`·`past` | `{items[] {room_id, room_type, name, status, last_message_at, unread_count, my_status}}` — 없으면 `items:[]` + `empty_hint`("동행을 찾거나 친구를 추가해 보세요", FR-COM20) | user, 내가 `invited`·`joined`인 방만(RLS) | 401 |
| **A67** `POST /api/v1/chat-rooms` | 1:1 `{type:"direct", friend_id}` / 단체 `{type:"friend_group", name(1~40), invitee_ids[2~19]}` | 201 `{room_id}` (1:1 방이 이미 있으면 **200 + 기존 `room_id`**, `direct_key` UNIQUE — T38d) | user. **실제 친구만**(`friendships`), 차단 관계 제외(FR-COM14·15). 단체방은 만든 사람이 방장, 나머지는 `invited` | 401 / 403 `NOT_FRIENDS`·`BLOCKED` / 422 |
| **A68** `POST /api/v1/chat-rooms/{room_id}/invitations` | `{invitee_ids[]}` | 200 | 단체방 **방장만**, 친구만, 동행방에는 초대 불가(FR-COM08). 초대 알림 | 401 / 403 / 409 |
| **A69** `POST /api/v1/chat-rooms/{room_id}/{action}` | `accept`·`decline`(초대받은 사람) / `leave`(멤버) | 200 `{room_id, my_status}` | `accept` 하면 그때부터(`joined_at`) 메시지가 보임 — **이전 메시지는 안 보임**(FR-COM16, T38f). 방장이 나가면 **가장 먼저 들어온 멤버가 방장**(FR-COM17). 동행방은 `leave` 대신 신청 취소·종료 흐름 | 401 / 403 / 409 |
| **A70** `PATCH /api/v1/chat-rooms/{room_id}` | `{name}` | 200 | 단체방 방장만(FR-COM17) | 401 / 403 / 422 |
| **A71** `GET /api/v1/chat-rooms/{room_id}/messages` | `after_seq`(재접속: 마지막으로 받은 순서 이후) · `before_seq`(위로 스크롤) · `limit`(≤100) | `{items[] {message_id, seq, sender_id, sender_display_name, msg_type, body, created_at}, has_more}` | `joined` 멤버만, **입장 뒤 메시지만**(RLS, T37g). 최근 100개는 Redis에서, 없으면 DB(Redis 장애여도 DB로 답함). **Redis에서 읽어도 서버가 DB와 같은 규칙으로 거름**: 지금 `joined`인지, 내 `joined_at` 이후인지, 숨김(`deleted_at`) 아닌지, 차단한 사람 메시지인지. 메시지 숨김(A77)·보존 정리·방 종료 때 `chat:recent:{room_id}`에서도 지움 | 401 / 403 |
| **A72** `POST /api/v1/chat-rooms/{room_id}/read` | `{seq}` | 204 | 내 `last_read_seq`만 앞으로(뒤로 안 감) → `unread_count` | 401 / 403 |
| **A73** `POST /api/v1/ws-tickets` | `{}` | 201 `{ticket, expires_in: 30}` | user. 브라우저 WebSocket은 헤더를 못 붙이므로 **30초짜리 1회용 표**(Redis `ws:ticket:{hash}`)로 연결 | 401 |
| **WS** `GET /api/v1/ws/chat?ticket=…` | 아래 메시지 형식 | 아래 | 연결·구독·전송마다 **현재 멤버·입장 시각·차단·방 상태**를 다시 확인(5.20). 서버 여러 대면 Redis Pub/Sub `chat:{room_id}`로 전달하되 **Pub/Sub은 저장·수신 보장이 아님**(놓친 것은 A71로) | 연결 거부 4401(표 없음·만료) / 4403(권한) |

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

- **전송 처리 순서(W116):** ① 멤버·차단·방 상태 확인 → ② 한 트랜잭션에서 `chat_rooms.last_seq + 1`로 순서 발급 + `chat_messages` 저장 → ③ commit 성공 뒤 `ack` → ④ Redis 최근 메시지 갱신·Pub/Sub 발행. 같은 `client_message_id` 재전송은 DB UNIQUE(T38b)로 **처음 저장된 메시지의 `ack`를 다시** 보냄(중복 저장 없음). Redis 실패는 전송 성공에 영향 없음(읽을 때 DB로).
- 전송 제한: 사람당 초당 5개·방당 초당 20개(임시, 9-1). 사용자 대화는 AI·RAG에 넣지 않음(5.20).

#### 6-4-6. 알림·신고·마이페이지·탈퇴 (A74~A80)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A74** `GET /api/v1/me/notifications` | `unread_only`·`page` | `{items[] {notification_id, type, ref_type, ref_id, created_at, read_at}, unread_count}` | user, 본인 것만(RLS, T39c). **앱 안 알림만**(외부 푸시는 범위 밖, FR-COM21). 화면은 WebSocket 연결 중이면 `notification` 이벤트로도 받음 | 401 |
| **A75** `POST /api/v1/me/notifications/read` | `{ids[]}` 또는 `{all: true}` | 204 | 읽음 칸만 바꿈(T39a·b) | 401 |
| **A76** `POST /api/v1/reports` | `{target_type: companion_post·chat_message·chat_room·user, target_id, reason(6종), detail?}` | 201 `{report_id}` | user. 같은 대상 하루 1회(임시). 신고자는 자기 신고만 봄(T40d) | 401 / 404 / 409 |
| **A77** `GET`·`POST /api/v1/admin/reports` | GET `status`·`page` / POST `{report_id, action: dismiss·hide_message·hide_post·close_room·block_user, note}` (`close_room` = 신고된 채팅방을 `read_only`로) | 200 | admin. 관리자 열람 범위는 **신고된 메시지만**입니다: 메시지 신고(`chat_message`)는 그 메시지 1건만 보여 주고, 방 신고(`chat_room`)는 메시지 원문을 열지 않고 방 정보·신고 사유만 보고 처리(`close_room` 등)합니다. 열람할 때마다 **`chat_admin_access`에 이유와 함께 기록한 뒤** 보여 줌(11/20 '채팅 열람 = 참여자·관리자', 기록은 수정·삭제 불가 T40c). 서버의 열람 범위 검사와 그 시험은 **구현 예정**(W128 권한 검증, 12/17–18. T40c는 기록 삭제 차단만 확인, 18-2). 메시지 숨김은 `chat_messages.deleted_at`(+ Redis 최근 목록에서 삭제), 글 숨김은 `companion_posts.hidden_at`·`hidden_by`(마이그레이션 008, T42d~f — 작성자 외에는 안 보임) | 401 / 403 / 404 |
| **A78** `GET`·`PATCH /api/v1/me/profile` | PATCH `{display_name?}` (닉네임 변경 가능, 2~12자·중복 검사) | `{user_id, display_name, birth_year, gender, onboarding_status}` (출생연도·성별은 본인 화면용. 다른 사람에게는 **동행 신청 때 그 글 작성자에게만 나이·성별**이 보임 — A61) | user, 본인만. 이메일·전화번호·나이·성별은 다른 사람에게 보이지 않음(FR-COM22) | 401 / 409 `NICKNAME_TAKEN` / 422 |
| **A79** `GET /api/v1/me/companion-activity` | `type`: `posts`·`applications` | 내 모집 글 / 내 신청 내역 | user | 401 |
| **A80** `DELETE /api/v1/me` (탈퇴) | `{password}` 재확인 | 204 | user. **DB 한 트랜잭션**(04 문서 7-0 ② '계정·프로필'과 같은 목록): Refresh 토큰 전부 폐기 → 진행 중 동행 글 `cancelled`·신청 `cancelled` → 친구 관계·신청·차단 삭제 → 방 멤버 `left`(방장이면 가장 먼저 들어온 멤버가 방장, FR-COM17) → 관심 축제(`favorites`)·취향(`user_festival_preferences`)·알림 삭제 → 챗봇 질문·답변(`assistant_runs`) 즉시 삭제 → `profiles` 닉네임·출생연도·성별 NULL → `users`는 행을 지우지 않고(감사 기록 FK) **이메일을 `deleted+<user_id>@invalid`, 비밀번호 해시를 `'!'`(로그인 불가)로 덮어쓰고 `status='deleted'`**(DDL NOT NULL 유지, 시험 T42l). **커밋 뒤**: `revoked:{jti}` 등록, 열린 WebSocket 끊기, LangGraph 체크포인트(`thread_id`) 삭제 — 실패하면 워커가 재시도. 다른 사람에게는 "알 수 없음"으로 표시(`app_public_display_name`이 NULL). 메시지 본문은 방 보존 정책대로 지워짐(FR-COM24). 백업(7일)에서 복원하면 탈퇴 목록으로 다시 지움 | 401 / 403(비밀번호 불일치) |

### 6-5. 기능 연결표 — 요구사항 → 화면 → API → 도구 → DB → 시험 (강사 11/20 자료 「설계서 한 줄을 실제 동작으로 연결하기」)

같은 사용자 작업을 모든 문서가 같은 이름으로 가리키는지 한 줄로 확인하는 표입니다. 화면 경로·담당은 **GitHub main 협업 규칙(11/20 신유빈)**, 시험 ID는 04 문서 10절(T…)·BFCL(NLD-…)·기획서 수용 시험(…-TC)입니다.

**실행 범위 표기(자료 07쪽):** A = 화면↔모의 응답 / B = API↔시험 DB / C = 어댑터↔실제 외부 API / D = LLM↔도구↔결과. 11/20 현재 코드는 뼈대(주석)뿐이라 **A·D는 전부 미구현**, B는 DB만 로컬 시험, C는 외부 API 실호출만 확인했습니다. 모의·로컬 성공을 실제 연동 성공으로 쓰지 않습니다.

| 사용자 작업 | 요구사항 | 화면 (`frontend/src/app/`, 담당) | API (담당 파일) | 도구 | DB | 시험 | 실행 범위 (11/20) |
|---|---|---|---|---|---|---|---|
| 축제 찾기·상세 보기 | FR-F01·F10·F15, D-015 | `festivals/`, `festivals/[festivalId]/` (이수언) | A02·A03 (`festivals/catalog.py`, 권오현) | `search_festivals`, `get_festival` | `festivals`·`festival_sources` | T17, BFCL NLD-01·02 | C ✅ TourAPI 실호출 / B 🔶 T17만 / A·D ⬜ |
| **귀갓길 조회 (대표)** | FR-R13~R17 | `routes/return/` (이수언) | A04·A05 (`routes/routes.py`, 권오현) / 공급원 `providers/tmap.py`·`kakao.py`(권오현) | `request_return_route`, `get_route_request_status` | `route_requests`·`route_results`·`route_query_metrics` + Redis `route:*` | T18~T20·T25·T28, BFCL NLD-04·11·13~22, RETURN-TC | C ✅ TMAP·카카오 실호출 / B ✅ 저장 규칙 / A·D ⬜ |
| 축제 가는 길 | FR-R12 | `routes/visit/` (이수언) | A25 (`routes/routes.py`, 권오현) | (4-2 후보 `request_visit_route`) | `route_requests`(`direction='visit'`) | RETURN-TC | C ✅ / A·B·D ⬜ |
| 축제 주변 정보 | FR-F02·F04·F05·F09·F11·F13 | `festivals/[festivalId]/` live-info (이수언) | A07~A10·A26~A30 (`festivals/info.py` 권오현, `facilities.py`·`data_sources.py` 신유빈) | `get_official_notices`, `get_facilities`, `get_crowd` | `official_notices`·`facilities`·`realtime_snapshots`·`festival_population_links` | BFCL NLD-07·08·28 | C ✅ 21종 실호출 / A·B·D ⬜ |
| 챗봇에게 묻기 | FR-C01~C09 | `assistant/` (이수언) | A06·A06-1·A06-2 (`assistant/chatbot.py`·`agent_jobs.py`, `realtime/job_events.py` 권오현) → 워커 (`agents/tasks.py` 한다영) | 13개 중 대화용 9개 | `assistant_runs`(002)·`agent_runs` + 체크포인트 | T24, BFCL 30문항 | B ✅ T24 / A·C·D ⬜ (BFCL은 판단 평가만) |
| 귀가 조회 장애 감지·복구 | FR-H01~H27, FR-O01~O03 | `admin/operations/` (이수언) | A14~A21·A31 (`admin/operations.py`, `api/healing/` 신유빈) | `get_incident`, `get_route_metrics`, `list_allowed_actions`, `propose_recovery_action` | `incident_*`·`recovery_*`·`load_simulations`·`route_query_metrics` | T3~T9·T13~T15, BFCL NLD-10·23~26, DEMO-TC | B ✅ / A·C(모의만 허용)·D ⬜ |
| 관심 축제 저장 | FR-A08 | `favorites/` (정예진) | A11~A13 (`accounts/favorites.py`, 권오현) | `save_favorite` | `favorites` | T1·T2·T21~T23 | B ✅ / A·D ⬜ |
| 회원가입·로그인 | FR-A, D-037 | `auth/`, `me/` (정예진) | A32~A35 (`accounts/auth.py`·`users.py`, 권오현) | — | `users`·`profiles`·`refresh_tokens` + Redis `revoked:*` | T12·T16·T21 | B 🔶 권한만 / A ⬜ |
| 취향 고르기·맞춤 추천 | FR-REC01~16 | `onboarding/`, `recommendations/` (정예진) | A36~A41 (`festivals/recommendations.py`, 신유빈) | — | `user_festival_preferences`·`festival_tags`·`festival_engagement_daily`(005) | T29~T31, REC-TC-01~07 | B ✅ / A·C·D(태그 LLM 검증) ⬜ |
| 지금 핫한 축제 | (기획서 추가 필요) | `recommendations/` (정예진) | A42 (`festivals/recommendations.py`, 신유빈 — 제안) | — | `festival_trends`(004) | T27 | B ✅ / C(크롤링 대상 미정) ⬜ |
| 친구 추가·차단 | FR-COM12~14 | `friends/` (정예진) | A43~A50 (`community/friends.py`, 권오현) | — | `friend_requests`·`friendships`·`user_blocks`(005) | T32·T33, COM-TC | B ✅ / A ⬜ |
| AI 방문 코스 | FR-P01·P03 | `assistant/` 방문 코스 (이수언) | A51 → A06-1 (`assistant/chatbot.py` 권오현) → Festival 에이전트(한다영) | `get_festival`·`get_facilities`·`get_official_notices`·`get_crowd` | `assistant_runs`(`run_kind`·`result`, 006) | T34 | B ✅ / A·D ⬜ |
| 공지·축제 관리(관리자) | FR-O06·D05·D12·O10 | `admin/operations/`(이수언), `admin/festival-management/`(정예진) | A52~A56, A23·A24 | — | `official_notices`·`notice_events`(006)·`festival_change_history`·`festival_review_queue` | T35, T6·T15(이력 추가만) | B ✅ / A ⬜ |
| 동행·채팅·알림·신고 | FR-COM01~11·15~24 | `companions/`, `chats/[roomId]/`, `notifications/`, `me/` (정예진) | A57~A80 + WS (`community/companions.py`·`chat.py`·`notifications.py`, `realtime/chat_socket.py`, `accounts/users.py`, 권오현) | — | 9개 테이블(007) | T36~T41, COM-TC (W128) | B ✅ / A ⬜ |

**계약 담당과 인계(자료 02·08쪽)**

| 계약 | 작성 | 검토 | 사용 | 인계 |
|---|---|---|---|---|
| API 요청·응답(이 문서) | 권오현 | 신유빈·정예진(11/19), 강사(11/19) | 화면 이수언·정예진, 에이전트 한다영 | v0.3.3 · 11/20 (GitHub `Docs/Step 2/`) |
| 도구 JSON Schema(4-6) | 권오현 | 한다영·한태경(BFCL 대조) | 한다영(`agents/tools/`) | v0.3.3 · 11/20 |
| DB DDL·마이그레이션(04 문서) | 권오현 | 신유빈(`shared/db/` 취합), 한태경(시험) | 전원 | 001~009 · 11/20 → `backend/shared/db/migrations/`(W17) |
| 공통 형식(`shared/contracts/`) | 신유빈(취합) | 권오현·한다영 | 전원 | 구현 시작 때 |
- 계약을 바꾸면 이 문서의 예시·모의 응답과 04 문서 시험도 같이 고치고 변경 이력에 버전을 올립니다(협업 규칙 3절 "API 형식을 바꾸면 API 문서도 함께 수정").


### 6-6. 필수 기능 보완 — AI 방문 코스·공지 관리·축제 관리 (v0.3.3, 11/20 기획서 필수 기능 대조로 찾음)

#### A51. AI 방문 코스 만들기 `POST /api/v1/assistant/visit-course` (FR-P01·P03, Must 최종)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 고른 축제에서 **무엇을 어떤 순서로 할지** 동행 유형·시간에 맞춰 코스를 만듦(맞춤 추천 A38은 '어느 축제를 갈지', A51은 '그 축제에서 무엇을 할지'). 화면 `assistant/` 방문 코스(이수언), API `assistant/chatbot.py`(권오현), 에이전트 Festival(한다영, WBS W37) |
| 2 | 요청 헤더 | A06과 같음 (`Authorization` 선택) |
| 3 | 경로·쿼리 | 없음 |
| 4 | 요청 본문 | `{request_id(8~64), festival_id, companion: family_relaxed·friends_activity·couple_photo·pet·solo, start_at(축제 기간 안 ISO 시각), duration_min: 60~480, constraints: {wheelchair}}` |
| 5 | 검증·권한 | 형식 422 → 축제 없음 404 → `start_at`이 축제 기간 밖이면 400 `COURSE_OUT_OF_PERIOD` → 요청 수 제한 429(A06과 같은 한도) → 같은 `request_id`는 처음 `run_id`(멱등) |
| 6 | 정상 응답 | **202** `{run_id, run_kind:"visit_course", run_status:"queued", status_url, events_url, run_access_token}` — A06과 같은 작업 방식, 결과는 **A06-1**(`result`)·진행은 **A06-2**로 |
| 7 | 오류 응답 | 400 `COURSE_OUT_OF_PERIOD` / 404 `FESTIVAL_NOT_FOUND` / 409 `IDEMPOTENCY_CONFLICT` / 422 / 429 / 503 `AI_AGENT_FAILED` |
| 8 | 실행 규칙 | 워커의 Festival 에이전트가 `get_festival`·`get_facilities`·`get_official_notices`·`get_crowd`만 써서 후보를 고르고, **코드가 검증한 뒤** 결과를 저장(아래). 전체 제한 30초·재시도 1회(A06과 같음, 9-1) |

**코스 검증 규칙 (FR-P03 — 실존·운영 시각·동선)**

| 검증 | 통과 조건 | 못 통과하면 |
|---|---|---|
| 실제 장소 | 모든 지점이 `festival_id`(축제 프로그램·장소) 또는 `facilities.facility_id`, 또는 카카오 장소 검색 결과의 장소 ID | 그 지점을 빼고 `unverified[]`에 "확인할 수 없는 장소"로 |
| 날짜·운영 시각 | 지점 시간이 축제 기간 안이고, 운영 시각(`playtime`·시설 개방 시간)이 있으면 그 안 | 운영 시각 정보가 없으면 `verified:false` + "운영 시간 확인 필요" |
| 동선 | 지점 사이 직선거리 ÷ 걸음 속도(분당 67m, 임시)로 이동 시간을 **추정**하고 합계가 `duration_min` 안 | 넘으면 뒤쪽 지점부터 뺌. 이동 시간은 '추정'으로 표시(길찾기 API는 쓰지 않음) |
| 조건 | `companion=pet`이면 `pet_allowed` 검증 태그, `wheelchair`는 검증된 시설 정보가 있을 때만 "가능"으로 | 근거 없으면 `constraint_status: not_verifiable`(추측 금지, FR-REC09·R10과 같음) |
| 저장 | `assistant_runs.result`(마이그레이션 006, 시험 T34)에 **장소 ID·순서·시간·검증 여부만** 저장. 카카오 장소의 이름·좌표는 **저장 불가(카카오 공식 답변, 11/20 한태경)**라 저장하지 않고, 화면이 결과를 열 때 **지점 좌표 주변 카카오 장소 검색을 실시간으로 다시 불러** 이름을 보여 줌(장소 ID 단건 조회 API는 없음) | — |

```json
{ "run_id": "run_01JDC1…", "run_kind": "visit_course", "run_status": "succeeded", "answer": "가족과 2시간 코스를 만들었어요. 운영 시간이 확인 안 된 곳이 1곳 있어요.",
  "result": { "festival_id": "fst_01JD7Z…", "companion": "family_relaxed", "start_at": "2026-11-21T15:00:00+09:00", "duration_min": 120,
              "stops": [ { "order": 1, "type": "festival", "ref_id": "fst_01JD7Z…", "name": "어린이 만들기 체험", "start": "15:00", "end": "15:40", "reason_tag": "family_program", "verified": true },
                         { "order": 2, "type": "facility", "ref_id": "fac_…", "name": "공중화장실", "start": "15:45", "end": "15:50", "verified": true },
                         { "order": 3, "type": "place", "ref_id": "kakao:12345678", "name": null, "start": "16:00", "end": "16:50", "verified": false, "note": "운영 시간 확인 필요" } ],
              "walk_min_estimated": 14, "constraint_status": { "pet": "not_verifiable" }, "unverified": [ "운영 시간 확인 필요: 3번" ] },
  "is_mock": true }
```

- 코스 수정·재추천(FR-P02)은 Should라 이번 범위 밖입니다(같은 요청을 조건만 바꿔 새로 보내면 됨).

#### A52~A54. 공식 공지 관리 (FR-O06 등록·수정, FR-D05 승인 — 둘 다 "적용 시" Must)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A52** `POST /api/v1/admin/notices` | `{festival_id?, type(5종, A07), title(1~200), content, effective_from, effective_to, source_url?}` | 201 `{notice_id, approval_status:"pending"}` | admin. 등록만으로는 **공개·경로 차단에 쓰지 않음**(승인 전 `pending`, RLS로 공개 조회 안 됨 — T35e). `notice_events`에 `create` 1줄 | 401 / 403 / 404(축제) / 422 |
| **A53** `PATCH /api/v1/admin/notices/{notice_id}` | 바꿀 칸만 | 200 `{notice_id, approval_status}` | admin. 승인된 공지를 고치면 **다시 `pending`**(재승인 필요). 바뀌기 전·후 값을 `notice_events`(`update`)에 | 401 / 403 / 404 / 422 |
| **A54** `POST /api/v1/admin/notices/{notice_id}/review` | `{decision: "approve"·"reject", reason}` (반려는 이유 필수 — DB도 거부, T35b) | 200 `{notice_id, approval_status, control_version}` | admin, **등록한 사람과 다른 관리자 권장**(2인 확인, 팀 인원상 필수는 아님). 승인되면 `control_version`이 바뀌어 그 축제의 경로 캐시를 무효화(04 문서 7절) → 귀가 경로가 통제를 반영(FR-R06·R09) | 401 / 403 / 404 / 409 `ALREADY_REVIEWED` |

- 이력(`notice_events`)은 추가만 가능하고 수정·삭제할 수 없습니다(트리거, T35c). AI가 공지를 구조화하는 기능(FR-D04·O07)은 Should라 범위 밖 — 들어오면 같은 승인 흐름을 탑니다.
- 담당: `admin/operations.py` 쪽 운영 기능이라 신유빈(협업 규칙) — 공지 화면은 `admin/operations/`(이수언).

#### A55~A56. 축제 직접 등록·수정 (FR-D12·O10 관리자 보완·승인)

| API | 요청 | 응답 | 권한·규칙 | 오류 |
|---|---|---|---|---|
| **A55** `POST /api/v1/admin/festivals` | A03 필드(이름·기간·장소·좌표·지역 필수) + `reason` | 201 `{festival_id, review_status:"pending"}` | admin. 공급원에 없는 축제를 직접 넣을 때. `data_sources`의 `admin_manual` 출처로 기록, 게시는 A56으로 | 401 / 403 / 409 `DUPLICATE_FESTIVAL`(이름·기간·장소가 같은 축제가 있으면 A24 검토 대기열로) / 422 |
| **A56** `PATCH /api/v1/admin/festivals/{festival_id}` | 바꿀 칸 + `reason`, 게시 여부 `published: bool` | 200 `{festival_id, review_status, published_at}` | admin. 칸마다 바뀌기 전·후 값을 `festival_change_history`(`actor='admin'`)에. 공급원 재수집이 관리자 수정을 덮지 않음(바뀐 칸은 A24 충돌 대기열 — FR-D14). 삭제 대신 `review_status='hidden'`(FR-D10) | 401 / 403 / 404 / 422 |

- 담당: `admin/festival_review.py`(권오현, 협업 규칙). 화면 `admin/festival-management/`(정예진).

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
| `singleflight_enable` | 같은 `route_key`로 진행 중인 조회 결과를 공유 | 동일 키 중복률 근거 + 17-3절의 추가 키 입력 반영 후(조건·통제 버전·공급원, W48) | 같은 부하에서 유효 경로 완료율이 오르지 않거나 거절·시간초과 증가 |
| `bounded_queue_adjust` | 내부 대기열 길이·대기 제한 조정(상한 안에서) | 내부 대기열 증가가 주원인이고 외부 지연이 정상 | 거절률이 기준 이상 증가 |
| `valid_cache_serve` | 조건이 같은 **유효** 캐시 경로 제공 | 캐시 `valid_until` 안 + 통제 버전 일치 + `verified_at` 있음. **목적지가 다른 요청에 비슷한 캐시를 주지 않음** | 통제 버전 변경·TTL 만료 |
| `fallback_provider_switch` | 길찾기 1차(TMAP)를 잠시 건너뛰고 2차(카카오맵)로 바로 보냄 | `failure_domain=route_upstream` + 1차 오류 근거 + **2차 공급원 키·응답 확인 완료** + 2차 일일 한도 여유 | 1차 정상 응답 회복, 또는 2차 한도 80% 도달(9절 규칙) |
| `safe_degrade` | 경로 대신 '확인 불가 + 공식 안내' 제공, 축제 기능 유지 | 다른 조치가 없거나 효과 없음 | 정상 지표 연속 회복 |
| `rollback` | 켜 둔 조치를 끄고 원래 정책으로 복귀 | 효과 미달·부작용 근거 | — |

이 목록에 없는 조치(새 공급원 전환, 무제한 재시도, 복구 정책 끄기 등)는 `ACTION_NOT_ALLOWED`입니다. `fallback_provider_switch`는 **2차 공급원(카카오맵)을 실제 호출로 확인한 뒤에만** 켤 수 있습니다(**활성 조건 충족, 11/20**: 같은 좌표 쌍 광화문→서울역·부산역→서면역에서 TMAP 3경로·카카오 15경로 모두 HTTP 200 — `evidence/길찾기_호출기록.md`, 키 오류 응답 확인 — 10-3. 단 카카오 결과는 A04 동기 응답 안에서만 전달되므로(5절) 이 조치가 켜진 동안 202로 넘어간 요청은 `ROUTE_SECONDARY_SYNC_ONLY`가 될 수 있고, 그 요청은 복구 성공으로 세지 않음). 켜는 동안 버스 혼잡 근거는 `unsupported`가 되고 경로는 캐시하지 않습니다. **목적지가 모두 다른 요청(고유 키)에서는 병합 효과가 없으므로** Recovery는 `singleflight_enable`을 기각하고 다른 조치나 보류를 고릅니다 (강사 2차 의견 3, BFCL NLD-24).


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

- **캐시·대체 경로 유효성 검사 규칙:** 복구 정책의 캐시·대체 경로는 17-3절의 추가 키 입력(조건·통제 버전·공급원)을 반영한 뒤 같은 `route_key`에만 씁니다. **목적지가 다른 요청에 비슷한 캐시를 주지 않습니다.** 검사 결과(통과/실패와 이유)를 `route_results.validity_check`에 남깁니다.
- 기준 숫자(유효 경로 제공률·p95)는 평소 구간(`baseline`) 시험 뒤 정합니다(12절 3번).

### 7-6. 챗봇 질문: `POST /api/v1/assistant/query` (A06) — v0.3.2에서 **비동기 작업**으로 변경

**왜 바꿨나:** 강사 11/19 자료 「API 서버 + 백그라운드 워커로 멀티에이전트 운영하기」는 *멀티에이전트를 HTTP 요청 안에서 기다리지 말고, API는 작업만 등록하고 202 + 작업 ID를 바로 돌려주라*고 정합니다(타임아웃·새로고침 유실·서버 막힘 방지). v0.3의 A06은 응답 안에서 `answer`를 기다리는 방식(최대 30초)이라 이 기준에 맞춰 **접수(A06) → 상태·결과 조회(A06-1) → 진행 이벤트(A06-2)** 세 개로 나눴습니다. 워커 구현 방식(Celery 또는 직접 만든 worker)은 팀 결정 대상이고(`Docs/3team/GitHub_협업_규칙_및_디렉터리.md`), 이 API 계약은 둘 중 무엇이든 같습니다.

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 사용자의 자연어 질문(축제 찾기·귀가 안내)을 받아 Supervisor → Festival/Route 에이전트 실행을 **작업으로 등록** (FR-C01~C09). 호출 주체: 챗봇 화면 |
| 2 | 요청 헤더 | `Content-Type: application/json`(필수) · `X-Request-ID`(선택) · `Authorization: Bearer`(선택, 로그인 사용자면 — `save_favorite` 같은 본인 도구는 이때만 허용) |
| 3 | 경로·쿼리 | 없음 |
| 4 | 요청 본문 | 아래 필드 명세 |
| 5 | 검증·권한 | 형식 422 → 요청 수 제한 429 → 같은 `request_id`면 처음 만든 `run_id`, 본문이 다르면 409 `IDEMPOTENCY_CONFLICT` → `conversation_id`가 있으면 그 대화의 주인인지(로그인: JWT `sub`, 비로그인: `X-Run-Access-Token`) 확인, 아니면 403. **질문 안의 "나는 관리자"는 권한이 아님**(1절) — 운영 도구(`get_incident` 등)는 이 API로 실행된 에이전트에게 주지 않음 |
| 6 | 정상 응답 | **202** `{run_id, run_status:"queued", status_url, events_url, run_access_token, retry_after_s}` — 답변은 아직 없음 |
| 7 | 오류 응답 | 401(토큰이 왔는데 무효) / 403 `FORBIDDEN`(남의 대화) / 409 `IDEMPOTENCY_CONFLICT` / 422 `VALIDATION_ERROR` / 429 `RATE_LIMITED` / 503 `AI_AGENT_FAILED`(작업 등록 자체 실패 — 큐·DB 장애. 이때도 A02~A05는 독립 동작) |
| 8 | 실행 규칙 | API는 **작업 기록(DB) + 큐 등록만** 하고 바로 응답(수 ms~수십 ms). 큐에는 `run_id`만 넣고 질문 원문은 넣지 않음(워커가 DB에서 읽음). 워커는 작업을 **선점(claim)** 한 뒤 실행(같은 작업 두 번 실행 방지). 전체 실행 제한 30초(임시) — 넘으면 `failed`·`AI_AGENT_FAILED`. LLM 429·5xx·시간 초과만 **같은 `run_id`로 1회** 재시도(`retrying`, 5초 뒤), 나머지는 재시도 없음. 워커가 실행 중에 죽어 `running`이 70초를 넘으면 정리 작업이 `failed`로 바꿈. 숫자는 모두 9-1절 기준표 |

**요청 필드 명세**

| 필드 | 타입 | 필수 | 빈값 | 제약 | 설명 |
|---|---|---|---|---|---|
| `request_id` | string | 예 | 불가 | 8~64자, UUID 권장 | 멱등 키(같은 질문 두 번 전송 방지) |
| `message` | string | 예 | 불가 | 1~500자 | 사용자 질문 |
| `conversation_id` | string | 아니요 | null | `^cv_[0-9A-Za-z]{6,26}$` | 이어지는 대화면 이전 `conversation_id`. 없으면 서버가 새로 만듦 |
| `context.festival_id` | string | 아니요 | null | `^fst_…` | 화면에서 이미 고른 축제 |
| `context.route_request_id` | string | 아니요 | null | `^rr_…` | 화면에서 이미 요청한 경로(본인 것만, 토큰 확인) |
| `reference_date` | string(date) | 아니요 | 서버 KST 오늘 | `YYYY-MM-DD` | "이번 주말" 같은 상대 날짜의 기준일(BFCL 평가에서는 고정값) |

**작업 상태(`run_status`)** — 강사 자료의 상태 머신을 따릅니다. 경로 상태(`route_status`)와 이름이 섞이지 않게 따로 둡니다.

| 값 | 뜻 | 다음 |
|---|---|---|
| `queued` | 접수됨, 워커 대기 | `running` |
| `running` | 워커가 선점해 실행 중 | `succeeded`·`retrying`·`failed` |
| `retrying` | LLM 일시 오류로 잠시 뒤 다시 실행(1회) | `running` |
| `succeeded` | 답변 완성 | 끝 |
| `failed` | 재시도 소진·시간 초과·복구 불가 오류 | 끝 (같은 질문은 **새 `request_id`로 새 작업**) |

**재시도와 새 작업의 차이:** 재시도는 같은 `run_id` 안에서 서버가 하는 것이고(사용자에게 새 ID 없음), 새 작업은 사용자가 다시 질문해 새 `request_id` → 새 `run_id`가 생기는 것입니다. 같은 `request_id`로 다시 보내면 새 작업이 아니라 **기존 작업 상태**를 돌려줍니다.

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
| `result` | object | null | `visit_course`이고 `succeeded` | A51 코스 결과(6-6, `assistant_runs.result`) |
| `route_request_id` | string | null | 경로를 요청했으면 | 화면은 경로 내용을 **A05로** 받아 지도에 그림 |
| `route_access_token` | string | null | 경로를 요청했고 아직 유효(10분) | A05의 `X-Route-Access-Token`으로 씀. 이 작업을 볼 권한(로그인 본인 또는 `X-Run-Access-Token`)이 있을 때만 줌. 만료 뒤에는 null → 화면이 귀가 조회를 새로 요청 |
| `error` | object | null | `failed` | `{code, message, retryable}` — `AI_AGENT_FAILED`·`TOOL_TIMEOUT` 등 |
| `queued_at`·`started_at`·`ended_at` | string | null 가능 | | |
| `is_mock` | boolean | 불가 | 항상 | 모의 LLM·모의 도구면 true |

- **경로 내용 보존 규칙(5절, 04 문서 7-0)과의 관계:** `answer`는 30일 저장되므로 **어떤 공급원이든(TMAP 24시간 제한·카카오 저장 금지)** 경로 구간·정류장 내용을 `answer`에 쓰지 않습니다. **에이전트 입출력 기록 파일(`agent_runs.input_ref`·`output_ref`, 30일)도 같음** — Route 도구 결과는 `route_request_id`·`provider`·`route_status`만 남기고 `route_candidates`는 넣지 않습니다(04 문서 7-0 ②). `answer`는 "경로를 찾았어요 — 귀가 화면에서 확인하세요" 수준의 요약으로 두고, 경로는 `route_request_id`로 A05에서 받습니다. 같은 이유로 Route 도구 결과를 대화 상태(체크포인트, 7일)에 넣을 때도 `route_candidates`는 빼고 `route_request_id`·`provider`·`route_status`만 넣습니다.

**A06-1 모의 응답 3가지 (화면 연결용 — 자료 03·05쪽: 진행 중·완료·실패)** — `is_mock: true`, 계약 버전 v0.3.3

```json
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "running", "answer": null, "used_tools": [ { "tool": "search_festivals", "ok": true, "error_code": null } ], "evidence": [], "route_request_id": null, "error": null, "queued_at": "…", "started_at": "…", "ended_at": null, "is_mock": true }
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "succeeded", "answer": "광화문에서 서울역까지 경로를 찾았어요. 귀가 화면에서 확인하세요.", "used_tools": [ { "tool": "get_festival", "ok": true, "error_code": null }, { "tool": "request_return_route", "ok": true, "error_code": null } ], "evidence": [ { "type": "route", "ref": "rr_01JD8Q3K2M", "provider": "mock_adapter", "queried_at": "…" } ], "route_request_id": "rr_01JD8Q3K2M", "error": null, "queued_at": "…", "started_at": "…", "ended_at": "…", "is_mock": true }
{ "run_id": "run_01JDB0…", "conversation_id": "cv_01JDB0…", "run_status": "failed", "answer": null, "used_tools": [ { "tool": "request_return_route", "ok": false, "error_code": "TOOL_TIMEOUT" } ], "evidence": [], "route_request_id": null, "error": { "code": "AI_AGENT_FAILED", "message": "답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요.", "retryable": true }, "queued_at": "…", "started_at": "…", "ended_at": "…", "is_mock": true }
```

- 화면은 `running`을 성공처럼 보여 주지 않고, `failed`면 `error.message`와 "다시 묻기"(새 `request_id` = 새 작업)를 보여 줍니다. 같은 `run_id`를 다시 **조회**하는 것과 실패한 일을 **새로 실행**하는 것은 다릅니다(7-6 '재시도와 새 작업의 차이').
- 남의 작업 조회는 403입니다. 강사 자료 05쪽은 '없거나 조회가 허용되지 않는 작업'을 404로 묶는 방식도 소개하는데, 우리는 `run_id`가 추측하기 어려운 ULID이고 토큰 만료 안내(401)와 구분하려고 403을 유지합니다.

#### A06-2. `GET /api/v1/assistant/runs/{run_id}/events` — 진행 이벤트(SSE)

- `text/event-stream`. 워커가 노드가 끝날 때마다 발행한 이벤트를 API가 중계합니다(에이전트 사고 과정 가시화).
- 이벤트 4종: `{"type":"step","node":"supervisor"}` · `{"type":"token","text":"…"}`(선택) · `{"type":"done"}` · `{"type":"failed","code":"AI_AGENT_FAILED"}`. `done`·`failed` 뒤 연결을 닫습니다.
- 이벤트는 저장되지 않으므로(구독 전 이벤트 없음) 화면은 **먼저 A06-1로 현재 상태를 그린 뒤** 구독합니다. 브라우저 `EventSource`는 헤더를 못 붙이므로 fetch 기반 SSE로 `X-Run-Access-Token`을 보냅니다.
- 구현 순서(강사 자료 25쪽): ① 폴링(A06-1, 2초)으로 먼저 완성 → ② SSE로 교체.

**DB:** 작업 상태·결과의 기준은 DB입니다. `agent_runs`(에이전트 1회 실행 기록)와 별도로 **작업 1건 = 1행**인 `assistant_runs`(`run_id`·`request_id` UNIQUE·`conversation_id`·`user_id`/`run_token_hash`·`run_status`·`attempt`·`message`·`answer`·`error_code`·`route_request_id`·시각)를 **04 문서 마이그레이션 002로 추가하고 시험했습니다**(11/20, T24: 같은 `request_id` 거부, 두 워커 선점 시 1명만, 70초 넘은 `running` 정리, 본인 작업만 조회).

### 7-7. 사건 목록: `GET /api/v1/admin/incidents` (A14)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 운영 화면의 사건 목록(필터·페이지). 사건 하나는 A15로 상세 조회 (FR-O02) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 이상>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | 아래 필드 명세 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 401 / operator·admin이 아니면 403(service도 목록은 불가 — 에이전트는 사건 ID로 A15만) / 형식 422 |
| 6 | 정상 응답 | 200 `{items[], total, page, page_size}` (0건이면 빈 배열) |
| 7 | 오류 응답 | 401 `UNAUTHORIZED` / 403 `FORBIDDEN` / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회만(멱등). 기본 최근 7일, 최대 조회 범위 31일(임시). 정렬 기본 `-detected_at` |

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

### 7-8. 경로 조회 지표: `GET /api/v1/admin/route-metrics` (A16)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 귀가 조회의 시간창별 지표. 운영 화면 그래프, Diagnosis(`get_route_metrics`)의 원인 구분 근거 (FR-O01, H01) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 또는 service>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | 아래 표 |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 401 / 403 / 형식 422 / `incident_id`·`simulation_id`가 없는 ID면 404 |
| 6 | 정상 응답 | 200 `{window, from, to, filter, summary, series[], evidence_refs[]}` — 데이터가 없으면 `series:[]`, `summary`의 숫자는 null |
| 7 | 오류 응답 | 401 / 403 / 404 `INCIDENT_NOT_FOUND`·`SIMULATION_NOT_FOUND` / 422 `VALIDATION_ERROR` |
| 8 | 실행 규칙 | 조회만(멱등). DB `route_query_metrics`(10초 단위 행)를 `window` 단위로 묶음. **p95는 행끼리 평균 낼 수 없어** 묶을 때는 각 창 p95의 최댓값을 쓰고 `p95_aggregation:"max_of_windows"`로 표시. 최대 범위 24시간(임시) |

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

### 7-9. 허용 조치 조회: `GET /api/v1/admin/incidents/{incident_id}/allowed-actions` (A18)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 이 사건에서 **지금** 허용되는 복구 조치·상한·켜져 있는 조치를 보여 줌. Recovery(`list_allowed_actions`)가 결정 전에 반드시 부름 (FR-H04/H05) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 또는 service>`(필수) · `X-Request-ID` |
| 3 | 경로·쿼리 | `incident_id`: string, 필수, `^inc_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 없음 |
| 5 | 검증·권한 | 401 / 403 / 422 / 404 / 사건이 `closed`면 409 `INCIDENT_CLOSED` |
| 6 | 정상 응답 | 200 — 위 4-6 ⑥의 `data`와 같은 모양 |
| 7 | 오류 응답 | 401 / 403 `FORBIDDEN` / 404 `INCIDENT_NOT_FOUND` / 409 `INCIDENT_CLOSED` / 422 |
| 8 | 실행 규칙 | 조회만(멱등). 판정은 7-3 allowlist와 **같은 코드 상수 하나**(정책 코드 `policy_gate`가 쓰는 것과 동일)로 계산 — 문서·API·실행이 다른 목록을 쓰지 않게 함. 조회 결과는 참고용이고 A19에서 다시 검사 |

| 응답 필드 | 타입 | 빈값 | 설명 | 출처 |
|---|---|---|---|---|
| `incident_id`·`failure_domain` | string | 불가 | | `incident_logs` |
| `policy_version` | string | 불가 | allowlist·상한 설정 버전(복구 시험 기록에 같이 남김 — 강사 피드백 4) | 설정 |
| `evaluated_at` | string | 불가 | 판정 시각 | 계산 |
| `active_actions[]` | array | 빈 배열 | `{action, attempt_id, enabled_at, expires_at}` 지금 켜진 조치 | `recovery_attempts`(`action_disabled_at IS NULL`), Redis `policy:route:active` |
| `allowed[]` | array | 빈 배열 | `{action, preconditions, limits, rollback_if}` 지금 쓸 수 있는 조치 | 7-3 규칙 + 지표 |
| `not_allowed[]` | array | 빈 배열 | `{action, reason}` 지금 못 쓰는 조치와 이유(에이전트가 기각 이유로 씀) | 같음 |
| `limits` | object | 불가 | `max_active_actions`(1, 임시)·`max_attempts_per_incident`(3, 임시 — 7-5: 조치 → 다른 조치 1회 → `safe_degrade`)·`attempts_used` | 설정·`recovery_attempts` 수 |

### 7-10. 부하 시험 중단: `POST /api/v1/admin/simulations/{simulation_id}/stop` (A21)

| # | 칸 | 명세 |
|---|---|---|
| 1 | 호출 목적 | 실행 중인 부하 시험을 즉시 멈춤 — 시연 중 문제가 생겼을 때 운영자가 누르는 정지 버튼 (FR-O03) |
| 2 | 요청 헤더 | `Authorization: Bearer <operator 이상>`(필수, service 불가 — 에이전트는 시험을 멈추거나 시작하지 않음) · `X-Request-ID` |
| 3 | 경로·쿼리 | `simulation_id`: string, 필수, `^sim_[0-9A-Za-z]{6,26}$` |
| 4 | 요청 본문 | 선택 `{ "reason": "시연 중 화면 멈춤" }` (≤200자) |
| 5 | 검증·권한 | 401 / 403 / 422 / 404 `SIMULATION_NOT_FOUND` / 운영 환경 403 `SIMULATION_DISABLED` |
| 6 | 정상 응답 | **200** `{simulation_id, status, stop_requested_at, stopped_at, affected_incidents[]}` — `status`는 `stopping`(정리 중) 또는 `stopped`. 이미 `stopped`·`finished`·`failed`면 **같은 200으로 현재 상태**를 돌려줌(여러 번 눌러도 안전 = 멱등) |
| 7 | 오류 응답 | 401 / 403 `FORBIDDEN`·`SIMULATION_DISABLED` / 404 `SIMULATION_NOT_FOUND` / 422 |
| 8 | 실행 규칙 | ① 부하 생성기에 중지 신호 → 2초 안(임시) 새 요청 중단 ② `load_simulations.status='stopped'`, `ended_at`, `offered_requests`(지금까지 보낸 수) 기록 ③ 이 시험에서 생긴 **열린 사건**은 켜진 조치를 정책 코드가 원복(`rollback_reason='simulation_stopped'`)하고 `final_mode='unresolved'`로 닫음 — 중단된 시험을 복구 성공으로 세지 않음 ④ 결과는 A31로 확인 |

```json
{ "simulation_id": "sim_01JD8P…", "status": "stopping", "stop_requested_at": "2026-11-20T14:06:00+09:00", "stopped_at": null,
  "affected_incidents": [ { "incident_id": "inc_01JD8Q3K2X", "action_rolled_back": "singleflight_enable", "final_mode": "unresolved" } ] }
```

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
| `get_route_metrics` | `incident_id?: str, simulation_id?: str, window?: enum[10s,1m,5m,15m]="5m"` | 진단 시작 시 필수 |
| `predict_route_delay_risk` | `window: str="15m", horizon: str="5m"` | 후속 구현. 구현 전에는 관측 추세만 설명하고 "예측 기능 미구현"으로 답 (BFCL NLD-03) |
| `list_allowed_actions` | `incident_id: str` | Recovery 판단 전 필수 |
| `propose_recovery_action` | `incident_id: str, decision: enum[select,reject,defer,rollback], action?: str, reasons: list[str], rejected_actions?: list, stop_condition?: obj, evidence_refs: list[str]≥1` | `list_allowed_actions` 결과 안의 action만. 근거 ID 없으면 호출 불가 |

**호출하지 않는 것이 정답인 요청** — 도구가 없거나 정책상 막힘 (BFCL 기준): 정보 부족 되묻기(NLD-19·20), 접근성 보장 확인(NLD-21), 지역 혼잡만으로 가장 한산한 경로 판정(NLD-22), 대기열 접수를 성공으로 집계(NLD-17), 일반 사용자의 장애 주입 요청(NLD-27), 행사장 내부 실시간 인원(NLD-28), 오래된 경로를 안전하다고 표시(NLD-29), 문서 속 지시로 정책 끄기(NLD-30, 프롬프트 인젝션).

30문항별 정답 호출은 **BFCL 문서(한다영 님 BFCL 30문항(Discord 공유본 — 대조 결과는 4-7절))를 기준**으로 합니다(v0.1의 부록 A는 삭제).

---

## 9. 장애 격리·호출 제한 (API 쪽 장치)

| 장치 | 설정(초안) | 이유 |
|---|---|---|
| 작업 풀 분리 | 귀가 조회 처리와 축제 검색·상세를 서로 다른 동시성 한도로 처리 | 귀가 부하가 검색을 멈추지 않게 (FR-H18, BFCL NLD-06) |
| 타임아웃 | 길찾기 어댑터 TMAP 5초·카카오 3초 · 그 밖의 외부 데이터 3초 · **도구 호출 15초(`TOOL_TIMEOUT`)** · **에이전트 실행 전체(A06) 30초** (모두 임시) | 무한 대기 방지 |
| 재시도 | 일시적 오류(시간 초과·429·5xx)만 최대 1회, **1초 뒤**(429는 `Retry-After`), 같은 멱등 키 | 무제한 재시도 금지 (FR-H02) |
| 요청 수 제한 | 귀가·가는 길 요청 IP·세션당 분당 10회, 챗봇 분당 10회(임시, 9-1 ⑤) | 외부 쿼터·비용 보호 |
| **길찾기 일일 한도** | TMAP(1차: **무료 10건만 — 종량제 결제 미등록**, 11/20 한태경)·카카오맵(2차: 무료 1,000건, 결제 미설정) 호출 수와 **하루 비용 상한(지금 결제 수단이 없어 0원)**을 공급원별로 Redis에서 셈. **80%: 운영 경고 + 그 공급원으로 보내는 우회 조치(`fallback_provider_switch`) 원복. 100%: 그 공급원 호출 중지**(남은 공급원도 없으면 `ROUTE_QUOTA_EXCEEDED`) | 11/19 한태경 조사(공식 문서 기준, 실호출로 재확인) |
| 외부 데이터 캐시 | 날씨·도착 정보·주차·돌발은 공급원 갱신 주기만큼 캐시(초안: 도착 30초, 주차 1분, 돌발 1분, 날씨 10분) | 같은 화면을 여러 사람이 볼 때 외부 호출 줄이기 |
| LLM 실패 | `/api/v1/assistant/query` 실패해도 A02~A05는 독립 동작 | FR-C09, FR-H13 |
| 외부 429 | `ROUTE_UPSTREAM_ERROR` + 원본 코드 로그, 재시도는 `Retry-After` 이후 1회 | BFCL NLD-12·25 |
| 재시도하지 않는 오류 | 400·401·403·404·409·422 | 입력·권한 문제는 다시 보내도 같음(수업 가이드 S22) |
| 중복 실행 방지 | 경로 요청은 `request_id`, 복구 결정은 `Idempotency-Key`로 처음 결과를 돌려줌. 같은 사건에 실행 중인 조치가 있으면 409 | 수업 가이드 S22 |
| 실제 공급원 부하 금지 | 부하·장애 시험의 `upstream`은 `mock_adapter`만(3절 스키마에서 막음) | 강사 일일 피드백 2 |

위 표의 숫자는 모두 **9-1절 기준표**에서 가져온 것입니다.

### 9-1. 제한값 기준표 (단일 기준 — 강사 11/19 피드백 4)

**이 표가 유일한 기준입니다.** 다른 절(2·4·7·8·9절, 04 문서 4절)에 적힌 숫자는 이 표를 가리키는 사본이고, 다르면 이 표가 맞습니다. 설정 통합 뒤 코드는 `shared/config.py`의 `Limits`에서 값을 읽고, 묶음 버전 **`LIMITS_VERSION`(초안 `lim-0.1`)** 을 부하 시험 결과 JSON(`load_simulations.result_ref`)·A18 `policy_version`·A31 응답에 함께 남깁니다(같은 시험을 같은 설정으로 다시 돌릴 수 있게). 값을 바꾸면 버전을 올리고 이 표의 '상태'를 고칩니다.

> **현재 코드 기준(11/23, 교차 검토로 확인):** `backend/shared/config.py`는 아직 비어 있어 `Limits`·`LIMITS_VERSION`은 **구현 전**입니다. 지금 경로 코드는 아래처럼 **코드 상수와 다른 이름의 환경변수**를 씁니다. 설정 한 곳으로 모으는 일은 아래 표 각 행의 담당·확정 시험 때 합니다.
>
> | 이 표의 설정 키 | 지금 코드 | 기본값 |
> |---|---|---|
> | `ROUTE_SYNC_WAIT_S` / `ROUTE_TOTAL_TIMEOUT_S` | `real_routes.py` 상수 `_SYNC_WAIT_S` / `_REQUEST_LIMIT_S`(같은 경로 병합 대기 `_FLIGHT_LIMIT_S`) | 3초 / 10초(12초) |
> | `ROUTE_ADAPTER_TIMEOUT_S` | `tmap.py`·`kakao.py`의 `_timeout` 상수 | TMAP 5초 · 카카오 3초 |
> | `ROUTE_CACHE_TTL_S` | `real_routes.py` 상수 `_CACHE_TTL_S`, **Redis가 아니라 서버 메모리** | 60초 |
> | `QUOTA_TMAP_FREE` / `QUOTA_KAKAO_FREE` | 환경변수 **`ROUTE_TMAP_DAILY_LIMIT`** / **`ROUTE_KAKAO_DAILY_LIMIT`**, 장소 검색 **`ROUTE_KAKAO_LOCAL_DAILY_LIMIT`**(`providers/quota.py`). 센 횟수는 파일 `ROUTE_QUOTA_FILE`(Redis `quota:*`는 예정) | 10 / 1,000 / 1,000 (장소 검색 1,000은 공급원 한도 100,000건/일보다 낮게 둔 우리 보호값) |
> | (route_key 비밀키) | 환경변수 `ROUTE_KEY_SECRET` — **없으면 서버가 켜질 때 임의 키를 만듦**(재시작하면 키가 바뀌어 캐시 키도 바뀜) | 없음 |
> | `TMAP_PAID_PLAN` | **코드가 읽는 환경변수가 아님** — 유료 전환 결정 항목의 이름 | — |

- 상태: **임시** = 숫자를 정했지만 시험으로 확인 전 / **외부 고정** = 공급원·약관이 정한 값 / **설계 고정** = 의미상 정해진 값
- 확정 시험: **W96**(내부 귀가 부하 계측, 신유빈·한태경, 11/19~12/04) → **W48**(복구 정책·비교 기준 확정, 신유빈·권오현, 12/04) / **W16**(인증·보존 정책, 한태경·권오현, 11/20) / **W36**(귀가 조회 구현, 권오현·신유빈, 11/27)

**① 시간 제한(타임아웃)**

| 설정 키 | 값 | 쓰는 곳 | 이유 | 상태 | 확정 시험·날짜 | 담당 |
|---|---|---|---|---|---|---|
| `ROUTE_SYNC_WAIT_S` | 3초 | A04 동기 대기(넘으면 202) | 화면이 오래 멈추지 않게. 카카오(2차)는 이 안에서만 전달(5절) | 임시 | W96 · 12/04 | 권오현 |
| `ROUTE_TOTAL_TIMEOUT_S` | 10초 | A04/A05 전체 처리(넘으면 `timed_out`) | 요청 전체 상한. 카카오 응답 전달은 동기 3초 안 | 임시 | W96 · 12/04 | 권오현 |
| `ROUTE_ADAPTER_TIMEOUT_S`(통합 설정 예정) | TMAP 5초·카카오 3초 | 길찾기 1회 호출 | TMAP 실측 평균 응답 273ms·처리 314ms(11/19 콘솔, 4건) — 여유 크게 둠, 부하 시험은 모의라 W36에서 다시 봄 | 임시 | W36 실측 · 11/27 | 권오현 |
| `EXT_DATA_TIMEOUT_S` | 3초 | 날씨·도착·주차·돌발·혼잡 호출 | 부가 정보라 짧게 | 임시 | W36 · 11/27 | 권오현 |
| `TOOL_TIMEOUT_S` | 15초 | 에이전트 도구 1회(`TOOL_TIMEOUT`) | 경로 전체 10초 + 여유 | 임시 | W96 · 12/04 | 한다영 |
| `AGENT_RUN_SOFT_LIMIT_S` | 30초 | A06 작업 1건(넘으면 `failed`) | 강사 자료 예시는 9분이지만 챗봇 답변은 짧아야 함 | 임시 | W96 · 12/04 | 한다영 |
| `AGENT_RUN_HARD_LIMIT_S` | 40초 | 워커 강제 종료 | soft + 10초 | 임시 | 같음 | 신유빈 |
| `INGEST_SCHEDULE` | 매일 06:00 (KST) | 축제 정기 수집(A23 이력) | TourAPI 하루 갱신이면 충분 | 임시 | W98 수집 구현 때 | 권오현 |
| `COMPANION_AUTO_END_H` | 12시간 | 만남 시각 뒤 자동 동행 종료(A65) | 기획서 '정책에 따른 자동 종료' | 임시 | W115 구현 때(12/03) | 권오현 |
| `CHAT_RATE_USER` / `CHAT_RATE_ROOM` | 초당 5개 / 초당 20개 | WebSocket 전송 제한 | 도배 방지 | 임시 | W116(12/08) | 권오현 |
| `WS_TICKET_TTL_S` / `CHAT_REDIS_RECENT` | 30초 / 방당 최근 100개(24시간) | WebSocket 연결 표 / Redis 최근 메시지 | 1회용 표, 빠른 조회 | 임시 | W116(12/08) | 권오현 |
| `TAG_LLM_DAILY_MAX` / `REC_WEIGHTS_VERSION` | 하루 300건 / `rec-0.1` | 축제 태그 LLM 검증 상한(6-4-1) / 추천 점수 가중치 묶음 | LLM 비용 상한 / 가중치 바꾸면 버전 올림 | 임시 | W27 모델 결정(11/25)·W124(12/02) | 신유빈 |
| `TREND_CRAWL_SCHEDULE` / `TREND_STALE_H` | 6시간마다 / 12시간 | A42 크롤링 주기 / 이보다 오래되면 `stale` | 대상 사이트 부담 최소 | 임시 | 대상 사이트 확정 때(11/25 제안) | 신유빈 |
| `SIM_STOP_GRACE_S` | 2초 | A21 중단 후 새 요청 멈춤 | 시연 정지 버튼 | 임시 | W96 · 12/04 | 신유빈 |
| `RECOVERY_DEFAULT_MAX_MIN` | 5분 | A19 `stop_condition` 기본값 | 7-5 재측정 한 번에 충분 | 임시 | W48 · 12/04 | 신유빈 |

**② 재시도**

| 설정 키 | 값 | 쓰는 곳 | 규칙 | 상태 | 확정 | 담당 |
|---|---|---|---|---|---|---|
| `EXT_RETRY_MAX` / `EXT_RETRY_DELAY_S` | 1회 / 1초 | 외부 API 일시 오류(시간 초과·429·5xx·TAGO `99`) | 429는 `Retry-After`. 400·401·403·404·409·422는 재시도 없음 | 임시 | W36 · 11/27 | 권오현 |
| `ROUTE_PROVIDER_FAILOVER` | 1회 | A04 요청 안 1차 → 2차 | 요청 1건에 2차는 한 번만 | 설계 고정 | — | 권오현 |
| `TOOL_ROUTE_RETRY_MAX` | 1회 | 도구 래퍼 `ROUTE_TIMEOUT` | 먼저 상태 확인 → 같은 `request_id`로만 | 설계 고정 | — | 한다영 |
| `AGENT_RUN_RETRY_MAX` / `AGENT_RUN_RETRY_DELAY_S` | 1회 / 5초 | A06 작업(LLM 429·5xx·시간 초과) | 같은 `run_id`로 `retrying`. 그 밖 오류는 즉시 `failed` | 임시 | W96 · 12/04 | 한다영 |

**③ 상태 조회 간격(폴링)**

| 설정 키 | 값 | 쓰는 곳 | 상태 | 확정 | 담당 |
|---|---|---|---|---|---|
| `ROUTE_POLL_INTERVAL_S` / `ROUTE_POLL_MAX` | 2초 / 5회 | A05 화면 폴링, `get_route_request_status` | 임시 | W96 · 12/04 | 권오현 |
| `RUN_POLL_INTERVAL_S` / `RUN_POLL_MAX` | 2초 / 20회 | A06-1 폴링(SSE 전 1단계) | 임시 | W96 · 12/04 | 이수언(화면)·권오현 |

**④ 캐시 시간**

| 설정 키 | 값 | 쓰는 곳 | 상태 | 확정 | 담당 |
|---|---|---|---|---|---|
| `ROUTE_CACHE_TTL_S` | 60초 | Redis `route:cache`(= `valid_until`), `valid_cache_serve` | 임시 (TMAP 24시간 제한 안, 카카오는 캐시 안 함 — 외부 고정) | W96 · 12/04 | 신유빈 |
| `EXT_CACHE_TTL_S.arrival` | 30초 | 지하철·버스 도착 | 임시 | W36 · 11/27 | 권오현 |
| `EXT_CACHE_TTL_S.parking`·`.incident`·`.crowd`·`.bike` | 60초 | 주차·돌발·혼잡·자전거 | 임시 | 같음 | 권오현 |
| `EXT_CACHE_TTL_S.weather` | 600초 | 기상청 | 임시 | 같음 | 권오현 |
| `STALE_FACTOR` | 2배 | 관측 시각이 공급원 갱신 주기의 2배 넘으면 `stale` | 임시 | 같음 | 권오현 |

**⑤ 동시 요청·요청 수·한도**

| 설정 키 | 값 | 쓰는 곳 | 상태 | 확정 | 담당 |
|---|---|---|---|---|---|
| `ROUTE_RATE_LIMIT_PER_MIN` | 10회/분 (IP·세션당) | A04·A25 (`rl:route`) — **부하 생성기는 내부 시험 경로라 적용 안 함** | 임시 (v0.3까지 'N 미정') | W96 · 12/04 | 권오현 |
| `ASSISTANT_RATE_LIMIT_PER_MIN` | 10회/분 (IP·세션당) | A06 | 임시 | W96 · 12/04 | 권오현 |
| `ROUTE_WORKER_CONCURRENCY` | 20 | 귀가 조회 동시 처리 상한(작업 풀 분리) | 임시 | W96 · 12/04 | 신유빈 |
| `ROUTE_QUEUE_MAX` | 50 (조정 범위 20~100) | 내부 대기열 상한 — `bounded_queue_adjust`는 이 범위 안에서만 | 임시 | W48 · 12/04 | 신유빈 |
| `SIM_*` 상한 | 동시 1~200, 지속 5~300초, 초당 ≤100, 지연 주입 ≤5,000ms, 반복 ≤20 | A20 (3절 스키마) | 임시 | W96 · 12/04 | 신유빈 |
| `RECOVERY_MAX_ACTIVE` / `RECOVERY_MAX_ATTEMPTS` | 1 / 3 | A18·A19 (7-5 순서) | 임시 | W48 · 12/04 | 신유빈 |
| `QUOTA_TMAP_FREE` / `QUOTA_KAKAO_FREE` (지금 코드: `ROUTE_TMAP_DAILY_LIMIT` / `ROUTE_KAKAO_DAILY_LIMIT`) | 10건/일 / 1,000건/일 (카카오 도보도 1,000건/일 따로) | `quota:{provider}` — **오류 응답(403 등)도 1건으로 셈**(SK 회신 전까지, 11/20 문의 발송) | **외부 고정**(공급원, 11/20 콘솔 확인 `evidence/usage/API_공식한도_20261120.md`) | — | 한태경 |
| `QUOTA_DAILY_COST_KRW` | **0원/일**(결제 미등록 — 무료 한도 안에서만 호출) | 공급원별 비용 상한, 80% 경고·100% 중지 | 임시 — 종량제를 등록하면 팀 합의로 올림(비용 부담: 한태경, 11/20) | W36 착수 전 팀 합의 · 11/26 | 한태경 |
| `TMAP_PAID_PLAN` (결정 항목 이름 — 환경변수 아님) | 없음(Free만) | 유료 전환 여부 | **Free 상품은 해지해도 그 달이 지나야 같은 앱에서 유료 구매 가능** → 시연 전에 유료가 필요하면 **새 앱 신청**(팀 결정) | W36 착수 전 · 11/26 | 한태경 |
| 수집 공급원 하루 한도 (참고, 외부 고정) | TourAPI·서울 버스도착·서울 정류소 1,000건/일(기능별) · 서울 실시간 지하철 1,000회/일 · 기상청·TAGO·표준데이터 10,000건/일 · 서울 일반 키 제한 없음(1회 1,000건) · 카카오 장소 검색 100,000건/일 | 수집 워커·실시간 조회 | 1,000건 공급원은 **DB 적재 후 조회**(요청 때 직접 부르지 않음) | 11/20 확인 | 한태경 |
| `AUTH_RATE_LIMIT_PER_MIN` | 10회/분 (IP당) | A32~A35 (1-1절) | 임시 | W16 · 11/20 | 권오현 |

**⑥ 토큰·잠금·중복 실행 방지 키의 수명**

| 설정 키 | 값 | 쓰는 곳 | 상태 | 확정 | 담당 |
|---|---|---|---|---|---|
| `ACCESS_JWT_TTL_MIN` / `REFRESH_TTL_DAYS` | 30분 / 14일 | 1절 인증 | 임시 | W16 · 11/20 | 한태경·권오현 |
| `REVOKED_TTL` | Access 남은 수명 | `revoked:{jti}` | 설계 고정 | — | 권오현 |
| `ROUTE_TOKEN_TTL_MIN` / `ROUTE_REQ_TTL_MIN` | 10분 / 10분 | Redis의 `route:token`·`route:req` 예정값. 현재 DB 모드는 `submitted_at` 기준 A05 토큰 10분을 적용 | 임시 | W16 · 11/20 | 권오현 |
| `RUN_TOKEN_TTL_MIN` | 10분 | `run_access_token`(A06-1·A06-2) | 임시 | W16 · 11/20 | 권오현 |
| `ROUTE_INFLIGHT_TTL_S` | **12초** (= `ROUTE_TOTAL_TIMEOUT_S` + 2초) | `route:inflight`(동일 요청 병합) | 임시 — **v0.3의 5초에서 고침**(아래 대조) | W96 · 12/04 | 신유빈 |
| `POLICY_ACTIVE_TTL` | `stop_condition.max_minutes` + 60초 | `policy:route:active`(켜진 조치) | 임시 — **v0.3 '없음'에서 고침**(아래 대조) | W48 · 12/04 | 신유빈 |
| `REFRESH_LOCK_TTL_S` | 5초 | `refresh:lock` | 임시 | W16 · 11/20 | 권오현 |
| `ROUTE_LABEL_TTL_H` | 24시간 | Redis `route:label:{route_request_id}` — 목적지·출발지 표시 이름(**DB에 저장 안 함**, 04 문서 004) | 임시 | W16 · 11/20 (한태경 확인) | 권오현 |

**중복 실행 방지 키가 작업보다 먼저 만료되지 않는지 대조**

| 키 / 보관 위치 | 키 수명 | 지켜야 할 작업의 최대 시간 | 판정 |
|---|---|---|---|
| `route:inflight` | v0.3 **5초** | 경로 처리 최대 10초(1차 5초 + 2차 5초) | ❌ **먼저 만료** → 5초 뒤 같은 요청이 또 실행돼 병합 조치(`singleflight_enable`) 효과가 사라짐 → **12초로 고침** |
| `policy:route:active` | v0.3 **없음**(직접 지울 때까지) | 조치 최대 `max_minutes` | ⚠ 반대 문제: 정책 코드가 죽으면 조치가 영원히 켜져 있음 → **`max_minutes`+60초 안전 TTL**. 정상 원복은 지금처럼 코드가 함 |
| A04·A25 `request_id` / `route_requests.request_id` UNIQUE | 행 보존 30일 | 처리 10초 + 상태 조회 10분 | ✅ |
| `route:token`·`route:req` | 10분 | 처리 10초 + 폴링 10초 | ✅ (만료 뒤 `route:req`는 DB에서 읽음) |
| A06 `request_id` / `assistant_runs.request_id` UNIQUE(002) | 행 보존 30일(임시, 04 문서 7-0 보존표) | 작업 최대 30초 + 재시도 5초 + 30초 = 65초 | ✅ |
| `run_access_token` | 10분 | 65초 + 결과 조회 | ✅ |
| A06 워커 선점(claim) | DB 상태라 만료 없음 | 워커가 실행 중에 죽으면 `running`으로 남음 | ⚠ **감시 규칙 추가**: `running`이 `AGENT_RUN_HARD_LIMIT_S`+30초(=70초)를 넘으면 정리 작업이 `failed`(`AI_AGENT_FAILED`)로 바꿈 — 재전달된 작업이 선점에 막혀 영원히 멈추지 않게 |
| A19 `Idempotency-Key` / `recovery_plans.idempotency_key` UNIQUE | 영구(감사 기록) | 조치 최대 5분 | ✅ |
| A20 `Idempotency-Key` / `load_simulations.idempotency_key` UNIQUE | 영구 | 시험 최대 300초 × 3구간 | ✅ |
| `refresh:lock` | 5초 | Refresh 교체 1초 미만 | ✅ |

### 9-2. 경로 1회 비용과 예상 운영비 (강사 요청, 11/20)

수업 자료 「모델·도구·서비스 평가」 07 규칙대로 **실제 사용량으로 잰 값(실측)과 단가·사용자 수를 가정해 계산한 값(예상)을 섞지 않습니다.** 아래는 모두 **예상 비용**이고, 실측은 부하 시험(W51)과 운영 로그(`quota:{provider}`·`agent_runs` 토큰·비용 칸)로 채웁니다.

**① 귀가 조회 1회에 드는 외부 비용 (A04·A25)**

| 항목 | 1회 비용 | 근거 | 상태 |
|---|---|---|---|
| TMAP 대중교통(1차) | **무료 10건/일 안 0원, 넘으면 0.88원/건** (Premium 후불) — 지금은 결제 미등록이라 10건 뒤 호출 안 함 | 11/20 콘솔 확인(`evidence/usage/API_공식한도_20261120.md`) | 외부 고정 · **부가세 포함으로 보임**(SK 공식 계산기: 30,000건 = 26,400원이 'VAT 포함' 합계, 11/20 한태경) — SK 회신으로 최종 확인 |
| 카카오맵 대중교통·도보(2차) | 1,000건/일 안 0원, **넘으면 10원/건 + 부가세 = 11원/건** — 유료 API를 켜고 비즈월렛을 연결해야 계속 쓸 수 있음(지금은 '사용 안 함') | 같은 파일 5절(11/20 한태경 콘솔 확인) | 외부 고정 |
| 목적지 해석·지도 표시(카카오) | 장소 검색 **2원/건**(100,000건/일 무료 뒤), 지도 SDK **0.1원/건**(300,000건/일 무료 뒤, 부가세 별도) | 같은 파일 5절 | 외부 고정 |
| 캐시로 답함(`route:cache` 60초, TMAP만) · 같은 요청 병합(`singleflight`) | 0원 | 9-1 ④, 7-3 | 설계 고정 |
| 경로 근거용 공공데이터(혼잡·돌발·버스 도착·날씨) | 0원 (하루 호출 한도만 있음 — 9-1 ⑤ 참고 행) | 같은 파일 | 외부 고정 |
| LLM | **0원** — 직접 귀가 조회(A04)는 LLM을 쓰지 않음(규칙·코드 검증). 챗봇으로 물을 때만 아래 ② | 2절·4-5 | 설계 고정 |

→ **귀가 조회 1회 = TMAP을 실제로 부르면 0.88원(부가세 포함), 캐시·병합으로 답하면 0원** (무료 한도 안이면 0원). 카카오 2차로 답하면 무료 한도 뒤 **11원** — TMAP의 **약 12.5배**라, 하루 조회가 많으면 TMAP 유료 전환이 훨씬 싸요(11/26 결정 자료, 9-1 ⑤ `TMAP_PAID_PLAN` 결정 항목).

**② 챗봇(A06)으로 경로를 물을 때 더해지는 비용**: `LLM 호출 수 × (입력 토큰 × 입력 단가 + 출력 토큰 × 출력 단가)`. 모델·단가는 팀 LLM 결정(11/25, W27) 뒤에 채우고, 호출마다 `agent_runs`에 토큰·비용을 남겨 실측합니다(04 문서 6-2).

**③ 전체 사용자 대상 하루 운영비 (계산식)**

`하루 비용 = 하루 귀가 조회 수 × (1 − 캐시·병합 비율) × TMAP 단가` `+ 하루 챗봇 질문 수 × 질문당 LLM 비용` `+ 서버비(AWS 월 비용 ÷ 30)`. **캐시 비율은 TMAP에만**(카카오는 캐시 금지), **병합 비율은 두 공급원 모두**에 적용. 카카오 장소 검색(2원/건)·지도 SDK(0.1원/건, 부가세 별도)는 무료 한도(장소 검색 100,000건/일) 안이면 0원이라 식에서 뺐고, 넘으면 더함

| 예시 (가정값 — **예상 비용**) | 계산 | 결과 |
|---|---|---|
| 축제 하루 방문자 중 귀가 조회 1만 명 × 1인 1.5회 | 15,000건 | |
| 캐시·병합 비율 50% (가정 — W51에서 실측) | 15,000 × 0.5 = 7,500건 TMAP 호출 | |
| TMAP 단가 0.88원 (부가세 포함) — **TMAP 유료(Premium) 전환을 가정**(지금은 무료 10건/일만, 9-1 ⑤) | 7,500 × 0.88 | **약 6,600원/일** (+ LLM·서버비) |
| 같은 조건을 카카오(2차)로만 답할 때 — TMAP 장애·무료 한도만 쓸 때. **카카오는 캐시하지 않으므로** 캐시 비율을 빼고 병합만 적용 — 병합 비율 실측(W51) 전 최대치 | (15,000 − 무료 1,000) × 11원 | **최대 약 154,000원/일** (카카오 유료 활성화 가정, 2차는 도보 보완 호출이 더해질 수 있음) |

**④ 빈칸과 담당** (값이 오면 이 표를 채우고 `LIMITS_VERSION`처럼 버전을 올림)

| 빈칸 | 담당 | 언제 |
|---|---|---|
| TMAP 0.88원 부가세 포함 최종 확인 (지금은 SK 계산기로 '포함'으로 봄) | 한태경 | SK 회신 때 |
| 질문당 LLM 토큰·단가 | 한다영 | 모델 결정 11/25 뒤 |
| AWS 서버 월 비용 | 신유빈 | W65 · 12/07–10 |
| 사용자 수 가정(축제 하루 방문자·1인당 조회 수) | 팀 결정(기획 정예진 제안) | W112 · 11/27 |
| 캐시·병합 비율 실측 | 신유빈·권오현 (부하 시험) | W51 · 12/15–17 |
| TMAP 유료 전환(새 앱) 여부 — 하루 10건 넘게 쓸지 | 팀 결정 | 11/26 (9-1 ⑤) |

---

## 10. 실제 호출 근거 (현재 확보분)

| API | 호출 일시 | 요청 조건(키 제외) | 결과 | 증빙 |
|---|---|---|---|---|
| 서울시 실시간 인구데이터 `citydata_ppltn` (OA-21778) | 2026-11-16 16:07경 | `sample` 키, JSON, 장소 `광화문·덕수궁` | `RESULT.CODE=INFO-000`, `AREA_CD=POI009`, `AREA_CONGEST_LVL=보통`, `AREA_PPLTN_MIN/MAX=48000/50000`, `PPLTN_TIME=2026-11-16 15:40`, `FCST_YN=Y` + `FCST_PPLTN[]` | 11/16 sample 키 원본은 로컬 보관. 같은 필드를 **정식 키로 다시 부른 11/19 원본** `evidence/responses/2026-11-19_seoul-ppltn_*.json`이 증빙 |
| TourAPI `searchFestival2` | 2026-11-19 (한태경) | 정식 키, 서울·부산 지역 | ✅ 서울 28건·부산 6건. 지역 변수는 **`lDongRegnCd`(서울 11, 부산 26)**, `areacode`는 빈 값. 필드 `title`·`eventstartdate`·`eventenddate`·`mapx`(경도)·`mapy`(위도)·`contentid`. **시작 전 행사도 섞여 옴** → `event_status` 재계산. 틀린 키: `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` | `evidence/responses/2026-11-19_tourapi_*.json` |
| TourAPI `detailIntro2` | 2026-11-19 (한태경) | 서울 3035607·부산 3360113 | ✅ 입장료 `usetimefestival`, 행사 시간 `playtime`(형식 불규칙), 장소 `eventplace`, 주최 `sponsor1`. 2건 모두 무료라 유료 형식 미확인. **소개(overview)는 이 응답에 없음** → `detailCommon2` 확인 필요 | `evidence/responses/2026-11-19_tourapi-상세_*.json`·`…tourapi-소개_*.json` |
| 서울 실시간 인구 (정식 키) | 2026-11-19 (한태경) | 광화문·덕수궁, 서울역 | ✅ 정식 키 확인. **없는 장소도 HTTP 200 + 본문 `ERROR-500`** → `SOURCE_RESULT_ERROR`로 처리(HTTP 코드만 보면 안 됨). 예측 12건 | `evidence/responses/2026-11-19_seoul-ppltn_*.json` |
| 기상청 초단기실황 | 2026-11-19 (한태경) | 격자 서울 60,127 · 부산 98,75 | ✅ 기온 `T1H`, 강수 `RN1`, 강수형태 `PTY`. **좌표 → 격자 변환이 필요**(부산역은 97,74로 재확인) | `evidence/responses/2026-11-19_kma_*.json` |
| TAGO 버스 정류소 | 2026-11-19 (한태경) | 좌표 검색 부산역·광화문 | 부산역 21건(도시코드 21), **광화문 0건** → **서울 버스는 TAGO로 안 됨**, 서울시 버스도착정보(15000314)로 바꿈 | `evidence/responses/2026-11-19_tago-정류소_*.json` |
| TAGO 버스 도착 | 2026-11-19 (한태경) | 부산역 → 서면역 정류소(`BSB164680201`) | 부산역은 종점이라 0건 → **서면역 재호출 2건 정상**(11/20 한태경). 도착 예정 `arrtime`(초)·남은 정류장 `arrprevstationcnt`·노선 `routeno` | `evidence/responses/2026-11-19_tago-도착_서면.json` |
| 서울 지하철 실시간 도착 | 2026-11-19 (한태경) | 서울역 | ✅ 19건. `barvlDt`(0이어도 도착 전일 수 있음 → `arvlMsg2` 함께 사용), `updnLine`, `recptnDt`. 틀린 키 `INFO-100` | `evidence/responses/2026-11-19_seoul-subway_*.json` |
| 서울 시영주차장 실시간 | 2026-11-19 (한태경) | 전체 | ✅ 122건. `TPKCT`·`NOW_PRK_VHCL_CNT`·`NOW_PRK_VHCL_UPDT_TM`. **위경도 없음** → 지도 표시하려면 주차장 위치 데이터와 연결 필요 | `evidence/responses/2026-11-19_seoul-parking.json` |
| 서울 TOPIS 돌발 `AccInfo` | 2026-11-19 (한태경) | 전체 | ✅ 28건. `acc_type`·`acc_dtype`·`link_id`·`occr_date/time`·`exp_clr_date/time`. XML, **좌표 `grs80tm_x/y` → 위경도 변환 필요**, 시각 자릿수 혼재 | `evidence/responses/2026-11-19_seoul-accinfo.json` |
| 서울 문화행사 OA-15486 | 2026-11-19 (한태경) | 5건 | ✅ 19,783건, 대부분 공연류. 축제 포함 여부·TourAPI 중복 미확인, 날짜 이상값 1건 → **보강용 우선순위 낮춤** | `evidence/responses/2026-11-19_seoul-culture.json` |
| TMAP 대중교통(1차) | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | 10-1 좌표 세트(광화문→서울역, 부산역→서면역, 광화문→서울역 `searchDttm` 22:00) | ✅ 서울·부산 정상. 정류장 ID `stationID`(6자리)·좌표가 옴. **정류장 목록 키는 문서 예시 `stationList`가 아니라 `stations`**. `searchDttm`을 바꿔도 경로·시간은 같고 `service`(1 운행 중/0 운행 종료)만 바뀜 → 막차 안내는 `service`로. 1호선 구간이 17시에도 `service`=0인 이유 확인 중 | **`evidence/길찾기_호출기록.md`**(호출 1건당 1줄: 정상 4건·키 오류 1건, 3경로씩) · `evidence/usage/TMAP_*.csv`(콘솔: 요청 7 = 완료 4 + 403 3, 평균 응답 273ms) · `evidence/responses/합성예시_tmap_*.json` — 원본은 24시간 규칙으로 삭제 |
| 카카오맵 대중교통·도보(2차) | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | TMAP과 같은 좌표 | ✅ 서울·부산 정상. **정류장은 이름만**(ID·좌표 없음) → 버스 혼잡을 붙이려면 이름+거리로 정류장 연결 | `evidence/길찾기_호출기록.md`(대중교통 정상 2건 15경로씩·키 오류 1건, 도보 1건 2,737m) · `evidence/responses/합성예시_kakao-transit_*.json`·`합성예시_kakao-walk_서울.json` — 원본은 저장 제한으로 보관 안 함 |
| 서울 버스도착정보(15000314) | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | 광화문 근처 정류소 | ✅ 차내 혼잡 `reride_Num1`(3 여유 / 4 보통) 실제로 옴. **`arsId`(5자리) ≠ TMAP `stationID`(6자리)** → 같은 값 아님, 이름+거리로 연결(D-033). `itemCount`는 0으로 와서 건수로 쓰지 않음 | `evidence/responses/2026-11-19_seoul-bus_*.json` |
| 경찰청 교통 돌발 | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | 전국 | ✅ 118건(서울 33·부산 4), 행사 유형 있음. **XML만** | `evidence/responses/2026-11-19_police-*.json` |
| 3순위 정적 데이터(12~18번) | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | 서울·부산 | ✅ 호출 확인(`festival-standard`·`tourist-rate`·`tour-demand`·`toilet`·`parking-standard`·`emergency`·`kakao_*-음식점`). 응급실(국립중앙의료원)은 **XML만**. 관광 수요 강도는 시군구 코드+지표 코드를 **함께** 넣어야 값이 옴(문서엔 선택값), 2026-10까지 제공. 전국주차장표준데이터 `instt_nm`은 **정확히 일치**해야 해서 부산은 구청별 호출. 택시 승강장·일부 주차장은 **위경도 없음** → 카카오 주소 검색으로 좌표 변환 | `evidence/responses/2026-11-19_*` (`_호출요약.json`에 호출별 시각·HTTP·건수) |
| 택시 승강장·자전거 | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | 전국 | ✅ 택시: **전국택시승강장표준데이터(15139230)**, 서울 268·부산 87 → **전국 공급원 확인**(D-036 조건 충족). 자전거: 행안부 전국 공영자전거 6,314건 → 전국 | `evidence/responses/2026-11-19_*` |
| TAGO (재확인) | 2026-11-19 한태경(서울·부산, 11/19 17:29 공유) | — | 가끔 **동시 접속 한도 오류 `99`**("가용한 세션이 존재하지 않습니다 (30/30)", HTTP 200) → 일시 오류로 재시도(9-1 ②) | `evidence/오류응답_정리.md` |

→ A10(`crowd`)의 응답 필드는 위 원본으로 정했습니다. **A02·A03(축제) 연결표는 11/19 실호출로 아래처럼 정했고**, A04(경로)는 10-2절(11/19 실호출로 일부 확인)입니다.

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
| `image_url` / `thumbnail_url` | `firstimage` / `firstimage2` (목록·상세 둘 다) | `festivals.image_url` / `thumbnail_url`(003) | ✅ 11/20 원본 16건 모두 있음 |
| `image_copyright` | `cpyrhtDivCd` | `festivals.image_copyright_type`(003) | ✅ 16건 모두 `Type3` |
| `overview` | `overview`(`detailCommon2`, 서울 280자·부산 378자) | `festivals.summary` | ✅ (11/20 한태경) |

### 10-1. 최소 실호출 계획 (강사 일일 피드백 2)

실제 공급원의 무료 한도를 아끼기 위해 **정상·오류 형식을 확인하는 최소 호출만** 합니다. 원본 응답은 키를 지우고 GitHub `evidence/`(`Docs/Step 2/evidence/`)에 연결하되, **TMAP·카카오 원본은 보관하지 않고 호출 기록표·합성 예시만** 남기며(04 문서 7-0 ①), 그 구조를 본뜬 모의 응답을 만들어 개발·부하 시험은 모의 응답으로만 합니다.

| 공급원 | 확인할 것 | 정상 호출 | 오류 호출 | 합계 | 담당 |
|---|---|---|---|---|---|
| TMAP 대중교통(1차) | 응답 필드(`legs[].steps`·`totalFare`·`stationID`·`routeId`·`lat`/`lon`), `searchDttm`, 지방 지원, 오류 형식 | 3회 — **같은 좌표 세트**: ① 서울 축제장 → 서울역(지금) ② 지방 축제장(예: 부산) → 부산역(지금) ③ ①을 축제 종료 시각 `searchDttm=22:00`으로 | 1회: 잘못된 좌표 | 4 (무료 10건 안) | 한태경(원본 보관) → 권오현 검토 |
| 카카오맵 대중교통·도보(2차) | 응답 필드(`fare`·`path.points`), 정류장 정보 부족 확인, 도보 API로 첫·끝 도보 보완, 지방 지원 | TMAP ①② 같은 좌표 2회 + 도보 2회 | 1회: 잘못된 좌표 | 5 (무료 1,000건 안) | 권오현 |
| TMAP `stationID` ↔ 서울 버스 `arsId` | 같은 값인지, 변환이 필요한지 | ①의 경로 속 버스 정류장 1개로 서울 버스 도착정보 조회 | — | 1 | 권오현 |
| 카카오 장소 검색 | 목적지 해석 | 2회: "서울역", "잠실" | 1회: 빈 결과 나오는 검색어 | 3 | 권오현 |
| 서울 버스 도착정보(혼잡 필드) | 차내 혼잡·재차 인원 필드가 실제로 있는지 | 1회: 축제장 근처 정류소 | 1회: 없는 정류소 ID | 2 | 권오현 |
| TourAPI 축제 검색·상세 | ✅ **11/19 한태경 완료**(10절), `detailCommon2` 소개 `overview`도 ✅(11/20) | 1회 | — | 1 | 한태경 |

- 남길 것: 요청 조건(키 제외)·호출 시각·HTTP 코드·원본 결과 코드·응답 JSON 위치. 시연 날에는 실제 호출 수를 세어 9절 한도 규칙(80% 경고·우회 원복, 100% 중지)을 따릅니다.
- 같은 요청을 반복하는 개발 호출, 부하 시험, 장애 주입은 **실제 공급원에 하지 않습니다.**

### 10-2. 원본 응답 → 내부 API → DB 연결표 (11/19 실호출 반영)

| 내부 필드 (A04 `route_candidates[]`) | TMAP 원본 필드(1차) | 카카오맵 원본 필드(2차) | DB 컬럼 | 상태 |
|---|---|---|---|---|
| 경로 구간 `legs[]`(도보 포함) | `legs[]`, 도보 `legs[].steps`, 경로선 `passShape.linestring`·`steps[].linestring`(**경도,위도 순서** → 어댑터가 `[위도, 경도]`로 뒤집음) | 구간 `steps[].properties`(type·stops·vehicles), 경로선 `steps[].path.points`(첫·끝 도보 없음 → 도보 API `route.properties.totalDistance`·`totalTime`으로 보완) | `route_results.candidates` (JSONB, **카카오는 저장 안 함**) | ✅ 실호출 확인(11/19). TMAP 구간 종류 `legs[].mode` = `WALK`·`BUS`·`SUBWAY` |
| 소요 시간 `duration_min` · 도보 `walk_m` · 환승 `transfers` | `totalTime`(**초** → 분으로 바꿈) · `totalWalkDistance`(m) · `transferCount` | `totalTime`(초) · 도보 API 거리 · `transfers` | 같음 | ✅ 실호출 확인(11/19) |
| 요금 `fare_krw` | `fare.regular.totalFare` | `fare.value`(이번 응답엔 min/max 없음) | 같음 | ✅ 실호출 확인(11/19) |
| 정류장·노선 `legs[].stops[]`·`route_id` | `passStopList.stations[].stationID`·`routeId`, 좌표 `lat`/`lon`, 목록 키 **`stations`**(문서 예시 `stationList`와 다름) | 정류장 이름만 `stops[].name`(ID·좌표 없음) | 같음 | ✅ 실호출 확인(11/19 한태경) |
| 운행 여부 `service_running` | `service`(1 운행 중 / 0 운행 종료) + 구간 대체 노선 `lane[].service`. `searchDttm`을 바꾸면 이 값만 바뀜 | 없음 | 같음 | ✅ 실호출 확인(11/19), **11/20 재호출로 1호선 0 원인 확인**: 대표 노선만 0, lane `급행`은 1 → 하나라도 1이면 운행(5절). 대표 노선이 0인 이유는 TMAP 문서에 없음(미확인) — `evidence/길찾기_호출기록.md` 마지막 절 |
| 출처 `provider`·`provider_tier` | 어댑터가 붙임 | 어댑터가 붙임 | `route_results.provider`·`provider_tier` | 설계 확정 |
| 조회 시각 `queried_at` | 어댑터가 호출 시각 기록 | 같음 | `route_results.queried_at` | 설계 확정 |

원본 필드 이름은 공식 문서(태경님 11/19 대조) 기준이며, 11/19 실호출로 확인한 칸은 ✅로 바꿨습니다. 11/20 한태경 님 정리표·합성 예시로 소요 시간·요금·구간 필드까지 모두 확인했습니다. TMAP은 요청에 `count=3`을 넣어 경로를 3개만 받습니다(카카오는 15개).

### 10-3. 길찾기 오류 응답 → 내부 처리 (11/20 한태경 `evidence/오류응답_정리.md`)

**HTTP 상태만 보면 안 됩니다.** TMAP은 경로가 없을 때도 **HTTP 200 + `result.status`**로 오고, 카카오는 본문의 `status`로 알려 줍니다. 어댑터는 HTTP 상태 → 본문 결과 코드 순서로 판정합니다.

| 공급원 | 원본 응답 | 근거 | 어댑터 판정 | 2차로 넘어가나 | 내부 결과(모두 실패 시) |
|---|---|---|---|---|---|
| TMAP | 403 `error.code=INVALID_API_KEY`(게이트웨이 `category: gw`) | **확인** | 설정 오류 — 운영 경고 | 예(1회) | `ROUTE_UPSTREAM_ERROR` |
| TMAP | 200 + `result.status` 11 출발·도착이 가까움 | 문서 기준 | 경로 없음(도보 안내 대상) | 아니요 | `route_status=unavailable`, `ROUTE_NO_RESULT`("걸어서 갈 수 있는 거리예요") |
| TMAP | 200 + `result.status` 12·13·14 출발/도착 정류장 없음·기타 | 문서 기준 | 경로 없음 | 예(1회) | `ROUTE_NO_RESULT` |
| TMAP | 400 + `result.status` 21·22·24 형식·필수값·시각 오류 | 문서 기준 | **우리 요청 오류** — 로그, 재시도 없음 | 아니요 | `ROUTE_INVALID` |
| TMAP | 400 + `result.status` 23 서비스 지역 아님 | 문서 기준 | 지역 미지원 | 예(1회) | `REGION_UNSUPPORTED` |
| TMAP | 500 + `result.status` 31·32, 시간 초과·네트워크 | 문서 기준 | 일시 오류(9-1 ② 재시도 대상) | 예(1회) | `ROUTE_UPSTREAM_ERROR`·`ROUTE_TIMEOUT` |
| TMAP | 무료 한도(10건/일) 초과 응답 | **미확인**(공식 문서에 없음) | 우리 `quota:tmap`이 10건에서 먼저 막음 → 호출 안 함 | 예 | `ROUTE_QUOTA_EXCEEDED`(둘 다 소진 시) |
| 카카오 | 401 `errorType=AccessDeniedError`(키 형식 오류·헤더 없음) | **확인** | 설정 오류 — 운영 경고 | (2차라 끝) | `ROUTE_UPSTREAM_ERROR` |
| 카카오 | 400 `code=-10` "API limit has been exceeded." | 문서 기준 | 한도 소진 — 그날 카카오 중지 | — | `ROUTE_QUOTA_EXCEEDED` |
| 카카오 | 200 + `status` `NO_RESULTS`·`STARTNODES_NULL`·`ENDNODES_NULL` | 문서 기준 | 경로 없음 | — | `ROUTE_NO_RESULT` |
| 카카오 | 200 + `status` `EQUAL_POINTS` / `INVALID_REQUEST` | 문서 기준 | 같은 지점 / 우리 요청 오류 | — | `ROUTE_NO_RESULT` / `ROUTE_INVALID` |
| 카카오 도보 | 200 + `status` `TOO_FAR_AWAY`·`ROUTE_RESULT_NOT_FOUND` 등 | 문서 기준 | 도보 보완만 실패 — 대중교통 경로는 그대로, 첫·끝 도보는 `null` | — | 경고 `notices` |

- '문서 기준'은 공식 문서에만 있고 실제로 받아 보지 않은 것입니다. 개발 중 모의 어댑터(`mock_adapter`)로 이 응답들을 재현해 시험합니다(실제 공급원에 일부러 오류를 만들지 않음).
- 설정 오류(키 403·401)는 사용자 탓이 아니므로 '확인 불가 + 공식 안내'로 답하고, 감지 코드가 `failure_domain=route_upstream` 사건 후보로 셉니다.


---

## 11. 미확인 항목·확인 계획

| 항목 | 현재 상태 | 확인 담당 | 확인 시점 |
|---|---|---|---|
| TMAP 실호출(1차, D-038): 필드·`searchDttm`이 막차 판단에 충분한지·지방 지원·**응답 저장 조건(약관)**·VAT 포함 여부·종량제 결제 등록 | ✅ **11/19 실호출 완료 + 11/20 증빙**(`evidence/길찾기_호출기록.md`·콘솔 사용량). 상품 Free TMAP 대중교통·무료 10건/일·**종량제 미등록**·비용 부담 한태경·11/19 사용 4건. 오류 형식 10-3(키 오류 확인, 나머지 문서 기준). **공식 한도 ✅(11/20 콘솔 확인, `evidence/usage/API_공식한도_20261120.md`)**: Free 10건/일·초과 시 자동 차단, 유료 0.88원/건. **Free를 해지해도 그 달이 지나야 같은 앱에서 유료 전환** → 시연 전에 유료가 필요하면 새 앱 신청(팀 결정 11/26, 9-1 ⑤). **`service`=0 재호출 ✅(11/20, lane까지 보고 판단 — 5절)**. **SK 문의 ✅ 11/20 발송**(차감 기준·결과 저장 기간·카카오맵 위 표시·유료 전환). **남은 것**: SK 회신 — 403 3건이 한도에 들어가는지(회신 전까지 **오류 포함 10건**으로 셈), 한도 초과 응답(문서에 없음 — 코드가 10건째에 막음) | 한태경 | 회신 대기 (11/20 발송) |
| 카카오맵 실호출(2차): 정류장 정보 부족·도보 보완·저장 제한 원문 | ✅ **11/19 실호출 완료 + 11/20 증빙**(대중교통 15경로·도보 1건, 키 오류 401 확인). 무료·결제 미설정·11/19 사용 50회(한도: 대중교통 1,000·도보 1,000·장소 검색 100,000건/일, 월 3,000,000 — 11/20 콘솔). **저장 조건 ✅ 카카오 공식 답변(데브톡 6/29): 실시간 호출만, 저장 불가 → 장소 검색 결과도 저장·캐시 안 함**(5절). **남은 것**: 한도 초과 응답(문서 기준만) | 한태경 | 11/20 확인 |
| **TMAP 경로를 카카오맵(다른 회사 지도) 위에 표시해도 되는지** | 카카오 쪽 ✅ 공식 답변 '타사 지도 위 표시 가능'(11/20). TMAP 쪽은 SK 문의 예정 | 한태경 → SK 문의 | **11/20 발송** · 회신 대기 |
| TMAP 무료 체험 사용 조건 | 하루 10건, **같은 서비스로 프로젝트를 여러 개 만들면 중지될 수 있음 → 팀 키 하나만** 사용 | 한태경 | 진행 중 |
| 지방 축제의 실시간 결합 정보 | 버스 도착·지하철·돌발 등 실시간 결합 API가 서울 중심 → 지방은 경로만 + '실시간 정보 미지원' 안내 | 권오현 | 실호출 후 |
| TourAPI 팀 키 실호출 (A02·A03 필드, 지역 코드 대응) | ✅ 11/19 한태경 정식 키로 확인(10절), `detailCommon2` 소개 ✅(11/20). 한도 1,000건/일(기능별) → 축제는 DB 적재, 요청 때 직접 부르지 않음 | 한태경 | 정함 |
| 목적지·출발지 장소 검색(지오코딩) | **카카오 장소 검색으로 정함**(D-035). 응답 필드는 실호출 후 | 권오현 | 길찾기와 함께 |
| **버스 차내 혼잡도** 공급원 | ✅ 서울시 버스 도착정보 `reride_Num1` 실제 확인(서울만, D-033). 남은 것: TMAP 정류장과 이름+거리 연결 규칙 | 권오현 | 개발 착수 전 |
| 지하철 실시간 도착 범위(수도권 노선 포함 여부) | ✅ 11/19 정식 키로 실호출(10절), 1,000회/일(활용사례 등록 시 무제한). 수도권 노선 범위는 개발 때 역 목록으로 확인 | 권오현 | 개발 착수 전 |
| 공영주차장 실시간 빈자리 | ✅ 11/19 실호출 — 서울 시영주차장만(서울만, 0-2) | 권오현 | 정함 |
| 경찰청 교통돌발 실제 지역 범위·행사/공사 구분 | ✅ 11/19 실호출: 전국 118건, 행사 유형 있음, XML만 | 권오현 | 정함 |
| 방문 집중 예측: 축제 장소가 '관광지' 목록과 맞는 비율 | 웹 조사만 | 권오현 | 키 발급 후 |
| 자전거 존·택시 승강장 데이터 공급원 | 자전거: ✅ 행정안전부 전국 공영자전거 실시간 정보 11/19 실호출 확인(6,314건) → 전국. 택시 승강장: ✅ **전국택시승강장표준데이터(15139230) 11/19 실호출 확인 → 전국**(D-036 조건 충족). 위경도가 없어 카카오 주소 검색으로 좌표 변환 필요 | 권오현 | 개발 착수 전 |
| 경로 점수 비율(시간·거리·비용·혼잡) | 미정(D-025) | 권오현·정예진 | 실제 응답 확보 후 |
| 서비스 범위 | ✅ **D-020·D-022로 정함**: 전국에 있는 데이터 = 전국, 지역별로만 있는 데이터 = 서울만 (0-2절) | 팀 | 정함 |
| DB·인증 방식 | ✅ D-037(11/19 사용자): AWS 위 Docker PostgreSQL + FastAPI 자체 JWT. **기획서·WBS(GitHub main, 11/20 대조)도 같은 내용**(Supabase 0건). AWS 서버 사양·배포 방식은 인프라 담당과 확정 | 권오현 → 신유빈 | AWS 준비 후 |
| 숫자 상한(동시 요청, 지속시간, 타임아웃, 요청 수 제한, 폴링 횟수, 캐시 시간) | **9-1절 기준표로 통합**(값·설정 키·확정 시험·담당, `LIMITS_VERSION=lim-0.1`). 대부분 임시 | 9-1 '담당' 칸 | W16 11/20 · W36 11/27 · W96/W48 12/04 |
| 장애 감지·복구 성공 기준 숫자 | 12절 3번에 초안 | 신유빈·한다영 | 기준 시험 후 |
| 과거 구간 혼잡 DB (BFCL NLD-12) | 기능 없음으로 정리(BFCL과 같음) | 정예진 | 기능 추가 결정 시 |

---

### 11-1. 제출 뒤 처리할 교차 검토 지적 (11/20 Claude·Codex·agy, 원문은 권오현 개인 보관, 반영 결과는 이 표)

제출 전에 고칠 것(문서 19건·SQL 7건)은 v0.3.3에 반영했습니다. 아래는 **틀린 내용은 아니지만 구현 전에 정할 것**이라 담당·날짜를 붙여 둡니다.

| # | 내용 | 담당 | 언제 |
|---|---|---|---|
| 1 | `route_requests` 30일 정리 순서(`route_results` → 공유 행 → 원본) 또는 FK `ON DELETE` 규칙 + 시험 | 권오현 | W54 · 12/16 |
| 2 | 시험 보강: T20c(23시간 지난 TMAP 행으로 정리 확인), T38f(방·메시지 따로 셈), T25(`pg_dump` 실패 감지), 동시 승인·선점은 두 연결로(W128) | 권오현·한태경 | W65 · 12/07–10 |
| 3 | 기존 데이터가 있는 DB에서 마이그레이션 시험(003 이미지 행, 004 되돌리기 범위), 파일별 트랜잭션 적용 | 권오현·신유빈 | W65 · 12/07–10 |
| 4 | `route_key`(좌표 포함)도 서버 비밀키 HMAC으로, 사건 연결 행에 남길 칸 정리 | 권오현 | W16 구현 때 · 11/27 |
| 5 | 챗봇 작업: 주체 확인 뒤 멱등 판정, 큐 등록 실패한 `queued`·`retrying` 정리, 비로그인 대화 권한 이어 가기 | 한다영·권오현 | W27 · 11/27 |
| 6 | 귀가 요청 멱등 키에 사용자·임시 세션 포함, 토큰 재발급 전 소유 확인 | 권오현 | W16 구현 때 · 11/27 |
| 7 | 통제 공지 입력(출처·시간·공간)과 승인·재검토·효력 시작/종료 때 캐시 무효화 범위 | 권오현 | W27 · 11/27 |
| 8 | 지표 집계 차원(`direction`)·여러 창 고유 키 수·빈 창 처리, MTTR 시작점을 WBS W48(감지→지속 복귀)로 통일 | 신유빈·권오현 | W48 · 12/04 |
| 9 | 추천: 취향 `pet`만 골랐을 때 `pet_allowed` 없는 축제는 점수 계산 전에 거르기, A39 동률 기준, A40 커서·데이터 버전 | 신유빈 | W124 · 12/02 |
| 10 | 1:1 방 차단 해제 뒤 재개방 규칙, `facilities.extra`·`festival_change_history.reason`·`reports` 처리 메모 칸 | 권오현·정예진 | W112 · 11/27 |
| 11 | ERD 표기: 복합 유일키(`source_id, source_item_id`), `friendships.request_id` 기수 | 권오현 | 다음 개정 |
| 12 | ✅ 한태경 증빙 스크립트: 카카오 장소 검색은 **응답 파일을 만들지 않고 건수·판정만** 남기게 고침(main `3a866cb`·`c9bd362` 반영) | 한태경 | 11/20 완료 |
| 13 | API 목록 번호순 정렬·상세 절 링크, ID 접두사 목록(`crm_`·`cpo_`·`cap_`·`frq_`·`rpt_`·`rrt_`·`rat_`) 0절에 추가 | 권오현 | 다음 개정 |
| 14 | 시나리오 반영 후속: 도구 `request_return_route` JSON Schema에 `origin` 추가, 앱 사용법 RAG 문서(`app_guide`) LLM 초안 작성·승인, 비밀번호 변경 API(마이페이지), 앱 운영 공지·이용약관 화면 | 한다영(도구·RAG)·권오현(API) | W27 · 11/27 |
| 15 | 17:31 변경분 교차 검토 후속: 009 적용·되돌리기를 파일별 트랜잭션으로 + 데이터가 있는 상태에서 시험(down은 둘 다 사용자 장소면 해시 1칸 손실·방 신고 삭제), 기존 닉네임 길이·중복 정리 절차, `route_key`를 출발·도착 두 곳 포함 HMAC으로, 도구 감사 기록에서 출발지도 해시, A76 채팅방 신고는 참여자만, `app_guide` 검색 때 승인·현재 앱 버전 검사, T28b·T42l·T43e 시험 보강 | 권오현·한다영 | W16·W65 · 11/27~12/10 |

## 12. 예진님 '수정 전 결정할 사항 6가지'에 대한 API·DB 쪽 제안

> 정예진 님 11/18 11:13 Discord 표. 아래는 **API·DB 설계 쪽에서 제안하는 답**이고, 팀이 확정하면 기획서·WBS에 반영합니다.

| # | 결정할 사항 | API·DB 제안 | 근거 |
|---|---|---|---|
| 1 | 실제 길찾기 API 선정 | **1차 TMAP · 2차 카카오맵**(11/19 D-038, 한태경 님 공식 문서 대조). ODsay는 한도·요금 미확인으로 뺌. 개발·부하 시험은 모의 어댑터만 | D-029·D-038 |
| 2 | 인증·DB 운영 방식 | **D-037(11/19): DB = AWS 위 Docker PostgreSQL 17 + pgvector, 인증 = FastAPI 자체 JWT**(Supabase 사용 안 함 — 예전 Supabase 제안은 D-037로 폐기). 인증 상세는 1-1절 | D-037, 04 문서 3·4절 |
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
| 버스 도착·차내 혼잡(서울) | 서울시 버스도착정보 15000314 (혼잡 `reride_Num1`·`arsId`, 11/19 확인) | seoul_only | 예 | A26, 교통수단 선택 근거 `mode_evidence` | D-024·D-033 |
| 공영주차장 빈자리 | 서울 시영주차장 실시간 | seoul_only | 예 | A27 | D-010 |
| 주차장 위치 | 전국주차장정보표준데이터 | national | 아니요 | A08 | D-014 |
| 교통 돌발 | 경찰청 교통돌발정보 | national | 예 | A28, 경로 근거 | D-012 |
| 교통 통제(서울) | TOPIS 돌발·통제 | seoul_only | 예 | A07·A28 | D-019 |
| 길찾기 1차 | TMAP 대중교통 `POST /transit/routes` (무료 10건/일, 0.88원/건) | national(서울·부산 11/19 확인) | 호출 시 계산 | A04·A25 | D-038 |
| 길찾기 2차 | 카카오맵 대중교통·도보 `GET /v2/routing/publictraffic` (무료 1,000건/일, 10원/건, 응답 저장 제한) | national(서울·부산 11/19 확인) | 호출 시 계산 | A04·A25 | D-038 |
| 지도·장소 검색 | 카카오 지도·로컬 | national | — | 화면, 목적지 해석 | D-035 |
| 화장실 | 행정안전부 공중화장실정보 | national | 아니요 | A08 | D-014 |
| 병원·응급실 | 국립중앙의료원 | national | 위치만 | A08 | D-014 (약국은 보류, D-021) |
| 맛집·주변 관광지 | 카카오 로컬 | national | 아니요 | A08 | D-014 |
| 자전거 존 | 행정안전부 전국 공영자전거 실시간 정보(11/19 확인, 6,314건) | national | 1차는 위치만(실시간 대수는 나중에 — 6-1) | A08 | D-036 |
| 택시 승강장 | 전국택시승강장표준데이터 15139230(11/19 확인, 위경도 없음 → 카카오 주소 검색으로 변환) | national | 아니요(위치만) | A08 | D-036 |
| 지하철역·버스 정류장 위치 | 도시철도 노선정보·TAGO 정류소 | national | 아니요 | A08 | D-014 |
| 방문 집중 예측·지역 수요 | 한국관광공사 (집중률 예측·관광 수요 강도) | national | 30일 예측 | A29 | D-018 |
| 지도 | 카카오 지도 (프론트) | national | — | 화면 | D-035 |
| 지금 핫한 축제 | 외부 사이트 크롤링(대상 미정 — 약관·`robots.txt` 허용 사이트만) | national | 6시간마다 | A42 | 11/20 팀장 결정 |

---

## 14. 확장 지점 (D-034: 완성본이 아님)

**11/19 기획서 최신본에서 신규 필수 기능 2종(맞춤 추천 A36~A41, 동행·친구·채팅)이 정해졌습니다.** 이 문서는 이 기능들을 **기존 A01~A35 계약을 바꾸지 않고 추가만** 해서 붙입니다(6절 A36~A42, 상세는 6-4·6-2절, 친구 A43~A50).

| 확장 대상 | 붙이는 방법 | 지켜야 할 것 |
|---|---|---|
| 새 서비스 기능(예: 일행 찾기·명당 찾기·취향 맞춤) | `/api/v1/<기능 이름>/…` API 묶음 + 필요한 도구 + 테이블을 새로 추가, 6절 목록에 행 추가 | 기존 API·도구 이름·필드는 바꾸지 않음. 위치 공유처럼 개인정보가 생기면 동의·보존 정책을 04 문서에 먼저 씀 |
| 새 지역 | 표준 입력 형태 + 지역별 전처리 어댑터 추가, `data_sources.enabled_region_codes`에 지역 추가 | 데이터가 없는 지역은 `unsupported` 유지(D-023) |
| 새 공급원 | 같은 내부 형식의 어댑터 추가(0절 '공급원 어댑터') | 실호출로 확인 전에는 `unverified` |
| 새 에이전트 도구 | 4절 표에 추가하고 BFCL 문항 추가 여부 결정 | 평가가 시작된 문항의 정답은 바꾸지 않음 |
| 크롤링 보완(D-027, 멘토 권고) | 11/20 팀 결정으로 **A42 '지금 핫한 축제'에만 크롤링 채택**(6-2, 대상 사이트 확정 11/25 제안). 다른 기능으로 넓히면 같은 규칙(약관·`robots.txt` 허용 사이트만, 원문 저장 안 함) | 축제 정보의 정본은 계속 TourAPI |

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
| 맞춤 추천 | A36~A41 + 분류 규칙 | 6-4절 상세(분류·점수·API), DB 005 | ✅ 11/20 |
| 동행·친구·채팅 | 친구 A43~A50 · 동행 A57~A65 · 채팅 A66~A73+WS · 알림 등 A74~A80, DB 005·007 | 6-4절 | ✅ 11/20 |
| 2차 공급원 비동기 전달 | 카카오 결과는 저장 불가 → 동기 전달만 | 5절 규칙·`ROUTE_SECONDARY_SYNC_ONLY` | ✅ (11/19 추가) |

**WBS(128개, 기획서 최신본 7절)와 대조**

| 항목 | WBS | API v0.3 | 판정 |
|---|---|---|---|
| 담당 | M02: R03 권오현 작성·취합, R06 신유빈 검토, 11/20 제출 | 같음 | ✅ (11/19 신유빈 님 검토 완료) |
| W10 실제 경로 응답 | 경로 원본 확보 → 검토 | TMAP·카카오맵 같은 좌표 비교 호출(10-1), 한태경 님 담당 | ✅ |
| 신규 W112~W128 | 추천·동행·친구·채팅 계약·구현·시험 | 계약 상세·DB 시험 완료(구현·기능 시험은 W115~W128) | ✅ 계약 |
| A31(부하 시험 조회) | — | 추가 | ⚠ W95/W96에 연결 요청 |

---


### 15-1. 기획서 필수(Must) 기능 추적표 (11/20 v0.3.3 — 기획서 FR 전체 대조)

기획서 최신본(GitHub `Docs/Step 1/놀다가_기획서.md`)의 **필수(Must) 기능 전부**를 이 문서·04 문서의 위치와 한 줄씩 연결했습니다. Should·Could(고급 경로 5유형, 후기, 분실물 등)는 범위 밖이고 6-1절·기획서 표를 따릅니다. 상태: ✅ 설계 작성(구현 전) / 후속 = 기획서도 후속(A17 지연 예측).

| FR | 기능 | 기획서 우선순위 | 설계 위치 (API 절 / DB) | 상태 |
|---|---|---|---|---|
| FR-F01 | 전국 축제 검색·상세 | Must | A02·A03 (2-3·2-4) / `festivals` | ✅ |
| FR-F02 | 선택 축제 주변 실시간 혼잡 | Must·서울만 | A10 승인 구역의 관측값 (6-2) | ✅ |
| FR-F03 | 혼잡과 위험·공식 통제 분리 | Must | A10 "지역 혼잡 ≠ 길 혼잡"·A07 공지와 응답 분리 (6-2, 2절 규칙) | ✅ |
| FR-F04 | 지도 주변시설 표시 | Must(확보된 범위) | A08 (6-2) / `facilities` | ✅ |
| FR-F05 | 축제 공식 운영 공지 | Must | A07 (6-2) / `official_notices` | ✅ |
| FR-F09 | 날씨·예보 | Must·전국 원천 | A09 (6-2) — 예보는 `unverified`(11/25) | ✅ |
| FR-F10 | 전국 복수 축제 지도·검색 | Must | A02 `bbox`·지도 범위 (2-3) | ✅ |
| FR-F11 | 병원·응급실 정보 | Must | A08 `hospital`·`emergency` (6-2) / `facilities` | ✅ |
| FR-F13 | 교통 돌발·공식 통제 | Must(검증 가능 범위) | A28 (6-2)·경로 근거 `area_evidence` (2절) | ✅ |
| FR-F14 | 축제-혼잡 관측 지역 매핑 | Must·서울만 | A10 승인된 공식 구역 경계 1km 이내 최대 3곳 (6-2) | ✅ |
| FR-F15 | 축제 상태·기간 필터 | Must | A02 `status`·`date_from`·`date_to` (2-3) | ✅ |
| FR-F16 | 교통수단 실시간 도착 | Must(최종·검증된 지원 범위) | A26 (6-2) — 지하철 서울만, 버스 서울/TAGO | ✅ |
| FR-F17 | 관광지 방문 집중 예측 | Must(최종·검증된 지원 범위) | A29 (6-2) / `realtime_snapshots`(`visit_forecast`) | ✅ |
| FR-F18 | 데이터 제공 지역 표시 | Must(표현 원칙) | `coverage`·`status:"unsupported"` (0·0-2·0-3절), A30 | ✅ |
| FR-R06 | 공식 통제 충돌 검증 | Must(확인된 범위) | A54 승인 → `control_version` → 경로 캐시 무효화 (6-6, 04 문서 7절), `verification_status:control_unverified` (2절) | ✅ |
| FR-R08 | 경로 출처·조회시각·상태 | Must | A04 `provider`·`queried_at`·`route_status` (2절) | ✅ |
| FR-R09 | 통제 시 재조회 | Must(검증 가능 범위) | 통제 승인 시 캐시 무효화 후 재조회 (6-6 A54, 04 문서 7절) | ✅ |
| FR-R10 | 접근성 미확인 처리 | Must | A04 `constraint_status: not_verifiable` (2절 규칙) | ✅ |
| FR-R12 | 축제 가는 길 기본 조회 | Must(최종) | A25 (6-2) | ✅ |
| FR-R13 | AI 안심 귀가 기본 조회 | Must·1차 시연 | A04 (2절) — 대표 | ✅ |
| FR-R14 | 비동기 경로 상태 조회 | Must·1차 시연 | A05 (2-2) | ✅ |
| FR-R15 | 경로 요청 이력·개인정보 및 저장 정책 | Must·1차 시연 | 2절 규칙·04 문서 7-0 (라벨 Redis 24시간·해시 HMAC) | ✅ |
| FR-R16 | 경로·조건 유효성 | Must·1차 시연 | 3절 `ReturnRouteRequest`·A04 검증 (2절) | ✅ |
| FR-R17 | 귀가 대기·거절·확인 불가 UX | Must·1차 시연 | `route_status` 6종·화면 문구 (6절 화면 상태 대응), A05 | ✅ |
| FR-R18 | 내부 조회 부하 격리 | Must·1차 시연 | 9절 작업 풀 분리·9-1 ⑤ `ROUTE_WORKER_CONCURRENCY` | ✅ |
| FR-R19 | 경로별 판단 근거(`area_evidence` / `mode_evidence`) | Must(확보된 자료만) | A04 `area_evidence`·`mode_evidence` (2절) | ✅ |
| FR-P01 | 동행 유형별 AI 방문 코스 | Must(최종) | **A51** (6-6) / `assistant_runs.result`(006) | ✅ |
| FR-P03 | 방문 코스 검증 | Must(최종) | **A51 코스 검증 규칙** (6-6) | ✅ |
| FR-C01 | 자연어 축제 안내 | Must | A06 (7-6) | ✅ |
| FR-C02 | 복합 질문 처리 | Must | A06 → Supervisor가 여러 도구 순서대로 (5절 흐름) | ✅ |
| FR-C03 | 동행 유형·조건 이해 | Must | A06 `context`·도구 `user_constraints` (7-6, 4-6) | ✅ |
| FR-C04 | 축제 맥락 유지 | Must | A06 `conversation_id`(대화 상태 7일) (7-6, 04 문서 2-1) | ✅ |
| FR-C05 | 공식 안내 RAG | Must | RAG `rag_documents`·`rag_chunks` (04 문서 2절) — 모델 11/25 결정 | ✅ |
| FR-C06 | 출처·최신성·불확실성 표시 | Must | A06-1 `evidence[]`·`provider`·`queried_at` (7-6) | ✅ |
| FR-C07 | AI 추천 검증 | Must | 도구 결과 코드 검증·A51 코스 검증 (4-5, 6-6) | ✅ |
| FR-C09 | LLM 장애 시 비AI 기본 서비스 유지 | Must | A06 실패해도 A02~A05 독립 (9절 LLM 실패) | ✅ |
| FR-A01 | 자체 회원가입 | Must | A32 (6절) / `users`·`profiles` | ✅ |
| FR-A02 | 로그인·Access/Refresh 발급 | Must | A33 (1절 인증) / Access 30분·Refresh 14일(9-1) | ✅ |
| FR-A03 | 토큰 갱신·재사용 차단 | Must | A34 교체 방식·`refresh:lock` (1절, 04 문서 4절) | ✅ |
| FR-A04 | 로그아웃·토큰 폐기 | Must | A35 `revoked:{jti}` (1절, 04 문서 4절) | ✅ |
| FR-A08 | 관심 축제 저장·해제·모아보기 | Must | A11~A13 (6-2) / `favorites` | ✅ |
| FR-K01 | 공식 문서 수집 | Must | `rag_documents`(출처·발행·대상 축제) (04 문서 2절) | ✅ |
| FR-K02 | 정제·임베딩 | Must | `rag_chunks`·`embedding_model`·중복 방지 UNIQUE (04 문서 2절) | ✅ |
| FR-K03 | 검색 출처 제시 | Must | A06-1 `evidence[]` (7-6) | ✅ |
| FR-K04 | 유효기간·승인 | Must | `approval_status`·`effective_to` 필터 (04 문서 2절) | ✅ |
| FR-K05 | 실시간 API 분리 | Must | "실시간 값을 RAG로 대신하지 않음" (04 문서 2절, 6-2 공통 규칙) | ✅ |
| FR-D01 | 외부 공공 API 수집·상태 기록 | Must | A23·A30 / `ingestion_jobs`·`data_sources.last_success_at` | ✅ |
| FR-D02 | 축제·시설 정적 데이터 제공 | Must | A02·A03·A08 DB에서만 답함 (0절 원칙) | ✅ |
| FR-D03 | 원본 형식·최신성·누락 검사 | Must | 6-2 공통 규칙(본문 결과 코드 확인)·10-3 / `ingestion_jobs.error` | ✅ |
| FR-D05 | 공식 공지 관리자 승인 | Must (D04 적용 시) | **A54** (6-6) / `notice_events`(006) | ✅ |
| FR-D06 | 전국 축제 목록 API 정기 수집 | Must | `INGEST_SCHEDULE`(9-1)·A23 / `ingestion_jobs` | ✅ |
| FR-D07 | 공급원 공통 스키마 정규화 | Must | 10절 원본 → 내부 필드 연결표 / `festival_sources` | ✅ |
| FR-D08 | 중복 축제 식별·통합 | Must | `UNIQUE(source_id, source_item_id)`·A24 `duplicate` (04 문서 7절) | ✅ |
| FR-D09 | 필수값·기간·좌표 검증 | Must | `festivals` 기간·좌표 CHECK·`needs_review` (04 문서 6-3) | ✅ |
| FR-D10 | 축제 DB 저장·증분 갱신 | Must | 업서트·`raw_checksum`·숨김(삭제 안 함) (04 문서 7절) | ✅ |
| FR-D11 | 출처·수집 이력·갱신 시각 | Must | `festival_sources`·`festival_change_history`·`last_synced_at` | ✅ |
| FR-D12 | 관리자 축제 등록·수정·승인 | Must | **A55·A56** (6-6)·A24 | ✅ |
| FR-D13 | 축제 공급원 장애 시 DB 목록 제공 | Must | A02는 DB에서 답함 + `last_synced_at` 표시 (2-3) | ✅ |
| FR-D14 | 수집원 충돌·보류 관리 | Must | A24 `conflict` 대기열 (6-2) / `festival_review_queue` | ✅ |
| FR-H01 | 장애 감지 | Must | 감지 → `incident_logs` (7절, 12절 3번) | ✅ |
| FR-H02 | 허용된 재시도·캐시 | Must | 9-1 ② 재시도·④ 캐시, `valid_cache_serve` (7-3) | ✅ |
| FR-H03 | Diagnosis 근거 기반 진단 | Must | `get_incident`·`get_route_metrics` → `incident_diagnostics` (4-6, 7-2) | ✅ |
| FR-H04 | Recovery 대안 비교·선택 | Must | A18·A19 `select`·`reject`·`defer`·`rollback` (7-3·7-4) | ✅ |
| FR-H05 | 코드 기반 실행·정책 검사 | Must | `policy_gate` 코드 검사 (0절, 7-4, 7-9) | ✅ |
| FR-H06 | AI 추천 오류 검증 | Must(최종) | 도구 결과 검증·A51 코스 검증 (4-5, 6-6) | ✅ |
| FR-H08 | 효과 재검증 및 결과 5종 | Must | 7-5 재검증·`final_mode` 5종 | ✅ |
| FR-H09 | 안전한 기능 축소 | Must | `safe_degrade` (7-3) | ✅ |
| FR-H10 | 장애·감사 로그 | Must | `incident_events`(추가만)·A15 (7-2, 04 문서 7절) | ✅ |
| FR-H11 | 원래 공급원/처리 정책 복귀 | Must(실제 전환 시) | `rollback`·`fallback_provider_switch` 원복 조건 (7-3, 9절 한도 80%) | ✅ |
| FR-H13 | 에이전트 오류 시 비AI 기본 모드 | Must | A06 실패 시 기본 귀가 조회 유지 (9절, 5절) | ✅ |
| FR-H14 | 외부 길찾기 API 장애 | Must(최종) | 1차 TMAP → 2차 카카오 1회·10-3 오류 처리 (5절) | ✅ |
| FR-H15 | 진단/복구 에이전트 자체 오류 | Must | 에이전트 시간 초과·형식 오류 → B1 규칙 정책 (5절 장애 흐름) | ✅ |
| FR-H16 | 축제 목록 수집 장애 | Must(최종·보조) | A23 수집 실패 기록·A02 마지막 목록 (6-2) | ✅ |
| FR-H17 | 축제 수집 품질 검사 | Must(최종) | A24 품질 대기열·`festivals` CHECK (6-2) | ✅ |
| FR-H18 | 영향 범위 분리 | Must | 9절 작업 풀 분리 | ✅ |
| FR-H19 | 장애 사전 예측(대표 전환) | Must(최종 검증, 초도 후속) | A17 (6-2) — 후속, 구현 전 501 | 후속 |
| FR-H20 | 공급원 본문 오류 코드 | Must(보조·계약) | A22 (6-2)·`SOURCE_RESULT_ERROR` | ✅ |
| FR-H21 | 내부 귀가 부하 재현·계측 | Must · 1차 시연 | A20·A31 (7-1, 6-2) / `load_simulations` | ✅ |
| FR-H22 | 실효 복구 조치 후보 검증 | Must · 1차 시연 | 7-3 allowlist·A18 (7-9) | ✅ |
| FR-H23 | 동일 부하 B0/B1/A1 비교 | Must · 1차 시연 | 7-0 B0/B1/A1 (7-1) | ✅ |
| FR-H24 | 요청 완료와 대기 분리 | Must · 1차 시연 | `completed_valid_route`·`valid_route_rate` (2-2, 7-8) | ✅ |
| FR-H25 | Route–Diagnosis–Recovery 협업 근거 | Must · 1차 시연 | `agent_runs`·`incident_diagnostics`·`recovery_plans` 근거 ID (7-2) | ✅ |
| FR-H26 | 요청 패턴 기반 조치 적격성 판단 | Must · 1차 시연 | `duplicate_ratio`·`unique_route_keys`로 `singleflight_enable` 적격 판단 (7-3) | ✅ |
| FR-H27 | 장애 후 자동 전환·효과 없는 조치 중단 | Must · 1차 시연 | 7-5 효과 없음 → 원복 → 다른 조치 → `safe_degrade` | ✅ |
| FR-O01 | 경로/API 상태 모니터링 | Must | A16 (7-8) | ✅ |
| FR-O02 | 사건 타임라인 | Must | A14·A15 (7-7, 7-2) | ✅ |
| FR-O03 | 장애 시뮬레이터 | Must · 1차 시연 | A20·A21·A31 (7-1, 7-10, 6-2) | ✅ |
| FR-O05 | 관리자 인증·권한 | Must | 1절 역할 `operator`·`admin`, `/api/v1/admin/**` 운영자 이상 | ✅ |
| FR-O06 | 공식 공지 수동 등록·수정 | Must(적용 시) | **A52·A53** (6-6) | ✅ |
| FR-O09 | 축제 수집 작업 대시보드 | Must | A23 (6-2) | ✅ |
| FR-O10 | 축제 데이터 수동 보완·승인 | Must | A24·**A56** (6-2, 6-6) | ✅ |
| FR-REC01 | 최초 로그인 취향 온보딩 | Must | A36·A37 `onboarding_status` (6-4) | ✅ |
| FR-REC02 | 취향 카드 5종 | Must | A36 취향 5개 (6-4) | ✅ |
| FR-REC03 | 복수 취향 선택 | Must | A37 `scenarios[]`(반려견은 `pet` 값 하나, 6-4) — 아기 동반 제외(기획서 11/20 15:32) | ✅ |
| FR-REC04 | 취향 저장·건너뛰기 | Must | A37 `skip` (6-4) | ✅ |
| FR-REC05 | 취향 재설정 | Must | A37 변경 시 재계산 (6-4) | ✅ |
| FR-REC06 | 맞춤형 축제 사진 카드 | Must | A38 카드 필드·`thumbnail_url` (6-4) | ✅ |
| FR-REC07 | 전국 추천 전체보기 | Must | A38 `fallback:"all_festivals"`·A02 (6-4) | ✅ |
| FR-REC08 | 검증된 규칙 기반 추천 | Must | 6-4-1 점수 `rec-0.1` (6-4) | ✅ |
| FR-REC09 | 추천 이유·동반 가능성 검증 | Must | 6-4-1 규칙 후보 → LLM 검증 → 원문 일치 확인 (6-4) | ✅ |
| FR-REC10 | 인기 축제 | Must | A39 (6-4) | ✅ |
| FR-REC11 | 전체 축제 일부 둘러보기 | Must | A40 `seed` (6-4) | ✅ |
| FR-REC12 | 지역별 전체 축제 보기 | Must | A02 지역 필터 (6-4) | ✅ |
| FR-REC13 | 최신 등록 축제 | Must | A41 `published_at` (6-4) | ✅ |
| FR-REC14 | 관심과 취향의 관계 분리 | Must | A38 관심 자동 저장 안 함 (6-4) | ✅ |
| FR-REC15 | 빈 상태·오류·부분 장애 | Must | A38 `fallback` (6-4) | ✅ |
| FR-REC16 | 사용자 정보 보호·접근권한 | Must | A36·A37 본인만(RLS T29) (6-4) | ✅ |
| FR-COM01 | 축제별 동행 모집 목록 | Must | A57 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM02 | 모집 글 작성 | Must | A58 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM03 | 모집 일정·조건 검증 | Must | A58 `MEET_AT_INVALID`·정원 1~10 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM04 | 모집 글 생성과 동행방 연결 | Must | A58 동행방 자동 생성 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM05 | 신청·취소 | Must | A60·A62 `cancel`(재신청 규칙) (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM06 | 작성자 승인·거절 | Must | A62 정원 잠금 승인(T36c) (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM07 | 모집 마감 | Must | A62 정원 차면 `full` (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM08 | 동행방 권한 | Must | A64·RLS(T37a·f·h) (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM09 | 동행방 단체 메시지 | Must | A71·WS(T37g) (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM10 | 만남 장소 확정 | Must | A63 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM11 | 만남 장소 변경 | Must | A63 시스템 메시지·알림 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM12 | 친구 검색·신청 | Must | A43·A44 (6-4-3) | ✅ |
| FR-COM13 | 친구 관계의 독립성 | Must | 동행 승인 ≠ 친구 (6-4-3, 04 문서 7-1) | ✅ |
| FR-COM14 | 친구 삭제·차단 | Must | A48·A49·A50 (6-4-3) | ✅ |
| FR-COM15 | 친구 1:1 채팅 | Must | A67 `direct`(친구만) (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM16 | 친구 단체 채팅 | Must | A67 `friend_group`·A69 수락 뒤 입장(T38f) (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM17 | 친구방 운영 | Must | A68·A69·A70 방장 승계 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM18 | 동행 종료/취소 | Must | A65 종료·취소·자동 종료 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM19 | 지난 동행 | Must | A65 읽기 전용·A66 `past` (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM20 | 채팅 탭 목록·빈 상태 | Must | A66 필터·`empty_hint` (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM21 | 신청·친구·방·장소 알림 | Must | A74·A75 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM22 | 마이페이지·프로필 | Must | A78·A79 (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM23 | 신고·차단·운영 | Must | A76·A77·`chat_admin_access` (6-4-4~6-4-6) / 007 | ✅ |
| FR-COM24 | 보안·탈퇴·데이터 처리 | Must | A80 탈퇴·WS 권한 재확인 (6-4-4~6-4-6) / 007 | ✅ |

---

## 16. API 필드 ↔ DB 컬럼 대응 (1차 필수 API)

이름은 가능한 한 같게 썼고, 다른 것은 아래 표가 기준입니다. ID 형식은 0절과 같습니다.

| API 필드 | DB 컬럼 | 비고 |
|---|---|---|
| `request_id` | `route_requests.request_id` (UNIQUE) | 멱등 키 |
| `route_request_id` | `route_requests.route_request_id` (PK) | `rr_…` |
| `festival_id` | `route_requests.festival_id` → `festivals.festival_id` | `fst_…` |
| `origin`·`destination`(사용자가 고른 곳) | `route_requests.origin_type`·`destination_type` + `origin_place_hash`·`destination_place_hash`(HMAC, 009) + Redis `route:label:{id}`(24시간) | **원문 저장 안 함**(DB에 라벨 칸 없음) |
| `travel_mode` · `route_preference` · `user_constraints` | `route_requests.travel_mode` · `route_preference` · `constraints` | |
| `route_status` | `route_requests.status` | |
| `route_candidates[]` (근거 제외) | `route_results.candidates` (JSONB) | 후보·구간·점수 |
| 후보별 `area_evidence` · `mode_evidence` | `route_results.evidence` (JSONB: `{candidate_id: {area_evidence, mode_evidence}}`) | 근거는 이 컬럼 한 곳에만 저장, 응답 때 후보에 붙임 |
| `validity_check` (캐시·대체 경로) | `route_results.validity_check` | 7-5 |
| `stop_reason` · `rollback_reason` | `recovery_attempts.stop_reason` · `rollback_reason` | 7-5 |
| A02·A03 축제 필드(`name`·`venue_name`·`lat`·`lng`·`overview`·`fee_text`·`homepage_url`·`image_url`·`thumbnail_url`·`image_copyright.type`) | `festivals.title`·`venue_name`·`latitude`·`longitude`·`summary`·`admission_fee_text`·`official_url`·`image_url`·`thumbnail_url`·`image_copyright_type`(003) | **이름 다름** — API 이름이 기준, DB는 위 컬럼 |
| A06 `run_id`·`run_status`·`answer` / 사용한 도구 | `assistant_runs`(04 문서 마이그레이션 002, 7-6) / `agent_runs.run_id`·`tool_calls` | |
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

## 17. 실행 확인: 첫 흐름을 모의에서 실제로 (강사 11/20 API 1·2, 2026-11-23)

> 이 절은 **설계가 실제로 동작하는지** 확인한 기록입니다. 실행 환경은 모두 **로컬**(집 PC 또는 학원 노트북 Docker)이며 **AWS가 아닙니다**(AWS는 W65 12/07~10). 근거 코드는 `ohyun` 브랜치 `backend/`.

### 17-1. 첫 흐름 실행 순서와 결과
| 단계 | API | 데이터 | 결과 (11/23) |
|---|---|---|---|
| ① 축제 검색 | A02 `GET /festivals?status=ongoing,upcoming` | **실제**: TourAPI 2026년 축제 870건 수집 → DB(공개 869·검토 대기 1) | 200, `is_mock:false`, 진행·예정 59건 |
| ② 상세 | A03 `GET /festivals/{id}` | **실제**(소개·입장료·장소·원본 번호) | 200, 예: 입장료 "VIP석 70,000원…", `source_ref` = TourAPI contentid |
| ③ 귀가 요청 | A04 `POST /routes/return` | **모의 축제 ID**로 실제 카카오 장소 검색 → TMAP(1차) | 200 `ready`, `provider=tmap`, 0.4~0.5초, 후보 3개 |
| ④ 상태 조회 | A05 `GET /routes/return/{id}` | 시험의 모의 공급원 응답 | `processing`→`ready`(202 뒤 조회) |
| 별도 2차 호출 | A04 (TMAP 건너뜀) | 모의 축제 ID로 **실제** 카카오 대중교통 | 200 `kakao/secondary`, 재조회 시 `ROUTE_SECONDARY_SYNC_ONLY` |
- ①②의 DB 조회는 [수집 구현 계획 3단계](../../backend/Doc/festival-ingestion/IMP-PLAN.md#3단계--a02a03-db-조회-i12i13), ③과 별도 2차 호출은 [경로 공급원 구현 계획의 3단계 실행 결과](../../backend/Doc/route-providers/IMP-PLAN.md), ④는 `test_P11_slow_primary_returns_202_then_finishes_in_background`로 확인했습니다. 같은 실제 축제 ID로 검색→상세→귀가→상태 조회를 화면에서 이어 확인하는 일은 남아 있습니다.
- **모의로 남은 구간:** 공지(A07)·날씨(A09)의 **값**, AI 질문(A06) 답변, 가입·로그인(A32~A35). 화면은 응답의 `is_mock`·`X-Mock`으로 "모의 데이터"를 표시합니다. API별 최신 상태는 `Docs/Step 2/handoff/API_연동_현황표.md`.
- **켜는 방법:** `FESTIVAL_DATA=db`(축제 실제), `ROUTE_PROVIDER=real`(경로 실제). 기본값은 둘 다 모의 — 시험·시연 예비용.

### 17-2. 실제 호출 기록 (원본은 저장하지 않음)
| 일시 | 공급원 | 조건 | 결과 | 호출 수 |
|---|---|---|---|---|
| 11/23 11:36 | TourAPI 목록·상세 | `eventStartDate=20260101` 전체 | 870건, 오류 0, 2분 36초 | 목록 9 · 상세 870+870 |
| 11/23 11:5x | TourAPI 목록(재수집) | 같은 조건 + DB 비교 | 새로 0·수정 0, **상세 재호출 0** | 목록 9 |
| 11/23 13시대 | TMAP 대중교통 | 광화문→서울역, 부산 광복로→부산역 | 200, 후보 3개씩 | **2**(하루 10 중) |
| 11/23 13시대 | 카카오 대중교통 | 광화문→서울역(TMAP 건너뜀) | 200, 후보 3개 | 1 |
| 11/23 13시대 | 카카오 장소 검색 | "서울역"·"부산역" | 공급원 결과 좌표 확인(저장 안 함). 요청 검색어는 메모리에 남음(17-3절) | 4 |
- TMAP 경로는 24시간 이내 삭제, 카카오는 저장 금지라 **응답 원본은 화면에서 요약만 보고 버렸습니다.** 시험은 한태경 님 **합성 예시**(`evidence/responses/합성예시_*`)를 씁니다.

### 17-3. 저장·캐시 규칙 ↔ 실제 코드 (강사 11/20 API 2)

실제 경로 모드에서 `ROUTE_STORE` 기본값은 `memory`입니다. `db` 선택 시 011 적용 DB를 사용합니다. `FESTIVAL_DATA=db`이면 A02·A03과 같은 축제로 A04 접수·처리 상태·결과 저장, A05 재조회까지 이어집니다. 이 연결은 **구현 완료·DB 시험 재실행 대기**입니다.
코드 경로는 `backend/` 기준입니다. 메모리 모드는 `tests/routes/test_p9_real_routes.py`, 한도는 `test_p8_quota.py`, DB 모드 단위·통합 시험은 각각 `test_p16_route_store.py`·`test_p18_route_store_db.py`를 사용합니다.

11/24 전체 오프라인 pytest 377개 중 365개 통과, DB 표시 12개 건너뜀(P18 4개 포함). 11/23 밤의 DB 실행 기록은 DB 설계서 10-A-1절에 남겼습니다.

| 규칙(5절·9절) | 현재 동작(코드 기준, 11/23) | 시험 함수 | 구현 예정(언제·누가) |
|---|---|---|---|
| TMAP 결과 캐시, 만료 뒤 A05는 `ROUTE_RESULT_EXPIRED` | `memory`는 60초 캐시 만료 뒤 **`retryable=true`**. `db`는 후보 요약을 저장하며 24시간 조회 정리 또는 주기 정리 뒤 **`retryable=false`** | `test_P11_expiry_removes_shared_tmap_body_for_all_ids`, P18 DB 시험 재실행 대기 | 주기 정리 실행 주체 확인 필요(신유빈) |
| **카카오 결과는 A04 동기(3초 안) 응답에서만**, 메모리에도 본문 안 남김 | 동기 대기 3초 안에만 전달, 재조회는 `ROUTE_SECONDARY_SYNC_ONLY`. 202 뒤 1차 실패면 카카오를 부르지 않음. DB 결과 행 없음 | `test_P11_secondary_response_is_only_available_on_sync_post`, `test_P11_secondary_in_flight_at_202_is_never_replayed`, `test_P11_slow_primary_returns_202_then_finishes_in_background` | — |
| 같은 조건 요청 병합(singleflight) | 처리 중인 같은 `route_key`를 기다림 | `test_P10_five_concurrent_requests_share_one_tmap_call` | — |
| 전체 처리 10초 제한 | 넘으면 `timed_out`, 병합 대기도 풀림 | `test_P11_overall_deadline_times_out_and_releases_flight` | — |
| 하루 한도(TMAP 10·카카오 1,000), 부르기 **전에** 셈, 다 쓰면 그 공급원 중지 | `api/providers/quota.py`, 환경변수 `ROUTE_TMAP_DAILY_LIMIT`·`ROUTE_KAKAO_DAILY_LIMIT`·`ROUTE_KAKAO_LOCAL_DAILY_LIMIT`(9-1 '현재 코드 기준') | `test_p8_quota.py`(한도·날짜·동시성), `test_P10_quota_skips_route_provider_calls` | 센 횟수를 Redis `quota:*`로 — W36, 권오현 |
| `route_key`에 원문 좌표 없음(HMAC) | `ROUTE_KEY_SECRET` HMAC-SHA256. **입력은 방향·출발/도착 좌표(소수 4자리)·`travel_mode`·`route_preference`·5분 구간뿐.** 비밀키가 없으면 서버가 켜질 때 임의 키 | `test_P10_cache_key_uses_hmac_and_rounded_coordinates` | `user_constraints`·통제 버전·공급원은 아직 키에 없음. 이 값만 다른 요청은 같은 키를 쓸 수 있음. 조건 반영·복구 조치(W48 12/04) 전에 키에 추가 — 권오현 (DB 설계서 4절) |
| 장소 검색어·좌표(18-1) | `memory`는 기존 요청 기록을 프로세스에 보관. `db`는 장소·본문 HMAC만 기록하고 처리 뒤 요청 원문을 보관하지 않음. A05는 정류장 좌표·경로선·사용자 장소 원문이 빠진 요약을 반환 | P16 단위 시험, P18 DB 시험 재실행 대기 | Redis 라벨과 사용자 장소 표시 연동은 후속 |
| A05 조회 토큰 10분 만료(401) | `db`는 서비스 계정으로 요청을 읽고 해시를 비교하며, 토큰은 접수 10분 뒤 만료. `memory`는 기존 토큰 규칙 적용 | P16 단위 시험, P18 DB 시험 재실행 대기 | API 서비스 계정 설정 방식 확인 필요(신유빈) |
| A04 동일 요청 재전송(멱등) | DB 모드에서 조회 토큰 만료 후에도 기존 `route_request_id`를 유지하고 `200 unavailable`·`ROUTE_ACCESS_EXPIRED` 반환 | P17 단위 시험, P18 DB 시험 재실행 대기 | — |
| 막차: 운행 종료 후보 제외, 카카오 `service_running:null` | TMAP은 종료 후보를 제외하고 남은 후보만 `ready`. 모두 종료면 HTTP 200 · `unavailable` · `ROUTE_NO_RESULT` · `retryable=false`. 카카오는 동기 응답에서 `null` + '막차 확인 불가' | `test_P13_tmap_all_candidates_running`, `test_P13_tmap_excludes_ended_candidates`, `test_P14_tmap_service_ended_after_202`, `test_P14_kakao_last_service_unknown_in_sync_response` (합성 고정 파일) | 대체 노선 목록·노선명 원본 필드 확인(P13) |
| 2차로 답해도 '자동 복구'로 세지 않음 | `provider_tier=secondary` 표시만 | — | 복구 판정은 7절(구현 전) |

### 17-4. 합성 예시와 실제 근거 구분
| 구분 | 위치 | 쓰는 곳 | 증거로 쓰는가 |
|---|---|---|---|
| 합성 예시(좌표 이동·이름 바꿈) | `evidence/responses/합성예시_*`, `backend/tests/routes/fixtures/` | 구조 확인·시험 | **구조만** — 실제 경로 증거 아님 |
| 실제 호출 기록 | 10절(11/19), **17-2절(11/23)**, `evidence/길찾기_호출기록.md` | 공급원 동작·한도 확인 | 예 (원본은 약관상 삭제) |
| 실제 수집 결과 | TourAPI 870건(학원 노트북 DB), 고정 파일 `backend/tests/ingestion/fixtures/`(공공데이터, 키 없음) | 축제 API | 예 |
| 복구 성공 증거 | (아직 없음 — 부하·복구 시험은 7절, W96 이후) | — | — |

### 17-5. 첫 흐름 연속 실행 기록(11/23, API 기준)

2026-11-23 15:40 KST에 학원 노트북 API를 SSH 터널로 호출했습니다. A02에서 고른 DDP 건축투어(`fst_01M835C2V19VJPP5F8MSNBMCQ2`)를 A03과 A04에 그대로 사용했습니다. 축제장에서 공공장소인 서울역까지 귀가를 요청했습니다.

| 단계 | API | HTTP | 응답 상태·요약 | 실제/모의 | 근거 파일 |
|---|---|---|---|---|---|
| 검색 | A02 `GET /api/v1/festivals?status=ongoing,upcoming&region=SEOUL` | 200 | 서울 진행·예정 22건, 선택한 축제는 `ongoing` · 75.7ms | 실제 DB | [결과 JSON][first-flow-result]의 `real.steps` |
| 상세 | A03 `GET /api/v1/festivals/{festival_id}` | 200 | 같은 축제 ID, `event_status=ongoing`, `source=tourapi` · 32.4ms | 실제 DB | [결과 JSON][first-flow-result]의 `real.steps` |
| 귀가 요청 | A04 `POST /api/v1/routes/return` | 200 | `ready`, `completed_valid_route=true`, `tmap/primary`, 후보 3개(22·31·28분) · 816.1ms | 실제 경로 | [결과 JSON][first-flow-result]의 `real.steps` |
| 상태 조회 | A05 `GET /api/v1/routes/return/{route_request_id}` | — | A04가 동기로 완료되어 실서버 조회 생략. A05 200 상태 변화는 아래 모의 실행에서 확인 | 모의 증빙 | [결과 JSON][first-flow-result]의 `mock.scenarios` |

**실패 흐름 · 집 PC 모의 API**

| A04 `X-Mock-Scenario` | A04 접수 | A05 1차 | A05 2차 | 최종 `error.code` | `retryable` |
|---|---|---|---|---|---|
| `async_unavailable` | 202 `queued` | 200 `processing` | 200 `unavailable` | `ROUTE_UPSTREAM_ERROR` | `true` |
| `async_timeout` | 202 `queued` | 200 `processing` | 200 `timed_out` | `ROUTE_TIMEOUT` | `true` |
| `async_secondary_sync_only` | 202 `queued` | 200 `processing` | 200 `unavailable` | `ROUTE_SECONDARY_SYNC_ONLY` | `true` |

실행 응답에서 추린 202 접수, 200 처리 중, 200 완료, 200 실패 예시와 요청별 시간은 [결과 JSON][first-flow-result]에 있습니다. A05 실패 응답은 모두 `completed_valid_route=false`입니다. 실서버 A02·A03·A04 응답에는 `X-Request-ID`가 있었고 `X-Mock`은 없었습니다(`is_mock=false`). 모의 A02~A05 응답에는 `X-Request-ID`와 `X-Mock: true`가 있었습니다(`is_mock=true`). 증빙은 경로 후보의 개수와 예상 소요시간만 남기며, 조회 토큰은 `***`로 표시합니다.

**실제·모의 구간**

| 구간 | 사용한 환경·데이터 | 확인 범위 |
|---|---|---|
| A02·A03 | 실제 · 학원 노트북 API의 TourAPI 수집 DB | 서울 축제 검색과 동일 ID 상세 조회 |
| A04 | 실제 · 학원 노트북 API의 `ROUTE_PROVIDER=real` | 출발 축제와 서울역을 입력해 TMAP 1차 경로 결과 확인. 실서버 A04 1회 |
| A04·A05 실패 흐름 | 모의 · 집 PC의 기본 모드, 가상 축제와 모의 공급원 응답 | 접수·처리 중·실패, 시간 초과, 2차 공급원 동기 전용 정책에 따른 실패 상태 |

화면 연결은 12/8 첫 시연에서 확인합니다.

**다시 실행하는 방법**

저장소 루트에서 터미널을 세 개 열어 순서대로 실행합니다. 스크립트에는 두 서버의 기본 주소만 넘깁니다. 실제 A04는 한 번만 호출하며, 202를 받으면 2초 간격으로 A05를 최대 5회 호출합니다.

```bash
# 터미널 1 · 학원 노트북 API 터널
ssh -N -o ExitOnForwardFailure=yes -L 18000:127.0.0.1:8000 laptop

# 터미널 2 · 집 PC 모의 API
cd backend
env -u FESTIVAL_DATA -u ROUTE_PROVIDER PYTHONDONTWRITEBYTECODE=1 uv run --offline \
  --with-requirements api/requirements.txt uvicorn api.main:app \
  --host 127.0.0.1 --port 18001 --no-access-log

# 터미널 3 · JSON 요약을 표준 출력으로 확인
python3 'Docs/Step 2/evidence/first_flow_2026-11-23/run_first_flow.py' \
  http://127.0.0.1:18000 http://127.0.0.1:18001
```

실행을 마치면 터미널 1과 2에서 각각 `Ctrl+C`로 종료합니다. [실행 스크립트](evidence/first_flow_2026-11-23/run_first_flow.py)

[first-flow-result]: evidence/first_flow_2026-11-23/result.json

## 18. 위치·대화 정보 전달 범위 (강사 11/20 API 3)

### 18-1. 어떤 정보를 어느 기능에 넘기나
| 정보 | 쓰는 기능 | 도구·공급원이 받는 것 | 결과를 볼 수 있는 사람 | 로그·DB에 남기는 것 | 하지 않는 것 |
|---|---|---|---|---|---|
| 축제 장소 좌표 | 축제 상세·지도·귀가 출발 | 공개 정보 그대로 | 모두 | 그대로 | — |
| **사용자 출발·도착 장소**(검색어·좌표) | 귀가·가는 길(A04·A25)만 | 카카오 장소 검색(검색어)·TMAP/카카오 경로(좌표) — **그 요청 처리 중에만**(공급원에 보내는 것 기준. 메모리 모드의 요청 기록은 서버 종료까지 보관, DB 모드의 원문은 처리 중 사용, 17-3) | 요청한 본인(A05 조회 토큰, 로그인 여부 공통) | 예정 저장 정책: DB에는 장소 **HMAC 해시**만(009), 라벨은 Redis 24시간. 현재 `route_key`는 HMAC. 서버 로그에는 경로 템플릿·`X-Request-ID`·`route_request_id`·HTTP/처리 상태를 남김. 경로 공급원 호출 로그에는 공급원·HTTP 상태를 기록 | 원문 좌표·검색어를 로그·DB·모델 프롬프트 기록에 남기지 않음, 다른 기능(추천·동행)에 재사용하지 않음 |
| 경로 결과(TMAP) | A04·A05 | — | 본인 | 현재 메모리 60초. 예정: Redis 캐시와 DB 24시간 내 삭제 | 24시간 넘게 보관 |
| 경로 결과(카카오) | A04 동기 응답 | — | 본인 | **아무 데도 안 남김** | 캐시·재전달 |
| 챗봇 질문(A06) | AI 질문 | 에이전트: 질문 문장 + 선택한 `festival_id` | 본인 | 마스킹한 질문(전화·이메일 등, DB 설계서 7-0) | 동행 채팅 원문·다른 사용자 정보를 프롬프트에 넣지 않음 |
| 동행 채팅 원문 | 채팅방 참여자 간 전달 | **에이전트·LLM에 넘기지 않음** | 참여자. 관리자(A77)는 신고된 메시지 1건만, 방 신고는 방 정보·사유만 | DB 보존 규칙(동행 종료 3일, DB 설계서 7-0) | 모델·로그로 전달 |
| 가입 정보(출생연도·성별) | 동행 신청 확인 | `app_applicant_profile`(글 작성자만) | 동행 글 작성자 | DB | 에이전트·추천에 원문 전달 |

### 18-2. 허용·차단 시험
| 시험 | 상태 | 위치 |
|---|---|---|
| `route_key`에 좌표 문자열 없음 | ✅ 11/23 | `backend/tests/routes/test_p9_real_routes.py`의 `test_P10_cache_key_uses_hmac_and_rounded_coordinates` |
| 서버 로그·수집 결과에 API 키 없음 | ✅ 11/23 | `tests/ingestion`(I1·I8), `tests/routes`(P2·P5) + 실제 실행 로그 검사 |
| A04·A05·장소 검색·A10 서버 로그에 출발·도착 좌표(소수 4자리 이상)·장소 검색어·조회 토큰·키 원문 없음. 요청 ID와 HTTP/처리 상태는 기록 | ✅ 모의·실제 모드(가짜 전송) | `backend/tests/api/test_a3_log_redaction.py`. Python 로깅과 Uvicorn HTTP/1.1 접근·ASGI 추적 로그를 오프라인으로 캡처. 500 응답과 원문을 고의로 기록한 대조 시험도 통과 |
| 다른 요청의 토큰으로 경로 조회 → 403 | ✅ | `backend/tests/api/test_step2_routes.py`의 `test_R12_lookup_validates_id_and_token_without_advancing_state` |
| 게시 시각이 있어도 검토 대기 축제는 A02·A03에서 제외 | ✅ 수집 DB 시험 | `backend/tests/ingestion/test_i12_catalog_db.py`. 010 권한 시험 T010a~e는 별도이며 [수집 구현 계획 3단계 첫 문단](../../backend/Doc/festival-ingestion/IMP-PLAN.md#3단계--a02a03-db-조회-i12i13)에 통과 기록만 있음(DB 설계서 10-A-3) |
| 장소 원문이 DB에 남지 않음(해시만) | 🟡 DB 시험(T44~T48 해시 칸) ✅, API→DB 저장 연결은 **구현 완료·DB 시험 재실행 대기** | DB 설계서 10절 |
| 에이전트 도구 입력에 채팅 원문·좌표가 없음 | ⬜ 예정 | 한다영 W24·W25(11/27) 도구 스키마 시험 |
| 요청 만료·삭제 뒤 메모리·DB·Redis에 장소 원문이 없음 | ⬜ 예정 | 17-3, 권오현. T44~T48은 해시 칸 옮김만 확인하고 원문 저장 여부는 확인하지 않음 |
| 관리자 채팅 열람은 신고된 메시지만(서버 검사 + `chat_admin_access` 기록) | ⬜ 예정 | 채팅·신고 구현(A77) 때. DB T40c는 열람 기록 삭제 차단만 확인 |

## 19. 결정 반영 기록 (강사 11/20 API 4)
'작성 / 검토' 칸: 신유빈 님이 11/23 디스코드에서 동의한 4건(D1 DB 접근 방식, 011 메모, 수집 담당, `RESET ALL`)만 검토자 신유빈이고, 나머지는 **검토 대기**입니다.

| 결정 | 상태 | 반영된 곳 (API·도구·시험) | 작성 / 검토 | 날짜 |
|---|---|---|---|---|
| D1 DB 접근: SQLAlchemy 2 + psycopg 3, 계정 2개, 트랜잭션마다 `SET LOCAL`, 로그인 요청은 `user_db_session(user_id)` | 🟡 합의 · `yubeen` 브랜치에 구현, `ohyun` 미병합 | `backend/shared/db/session.py`(신유빈, `yubeen` 브랜치 `83220c9`). 지금 `ohyun`의 수집·축제 조회 코드는 자체 연결을 씀 → 병합 뒤 이 연결로 교체. DB 시험 T21~T23(SQL 시험) | 권오현 / 신유빈 | 11/23 |
| 관심 저장 도구 호출 주체 = Supervisor | ✅ 문서 | 4절 표(변경 없음), 인계 문서 수정 | 권오현 / 검토 대기 | 11/23 |
| 에이전트 실패 → 규칙 정책(B1) → 안 되면 확인 불가 | 🟡 구현 전 | 7절, 상태 전이 설계(W25) | 한다영·권오현 / 검토 대기 | 11/23 |
| 카카오 결과 동기 전용 | ✅ 코드·시험 | 17-3 | 권오현 / 검토 대기 | 11/23 |
| 막차(W36): TMAP 운행 종료 후보 제외, 카카오 막차 확인 불가 | ✅ 코드·합성 응답 시험 | 5절·17-3, STEP3 P13~P15 | 권오현 / 검토 대기 | 11/23 |
| 끝난 축제 숨김 → A02 여러 상태 필터 `status=ongoing,upcoming` | ✅ | A02(2-3 필드 표·3절 모델), 시험 `backend/tests/api/test_i13_multi_status.py` | 권오현 / 검토 대기 | 11/23 |
| 실제 축제 ID로 귀가·현장 정보 동작 | ✅ 시험 · 화면 확인 전 | 시험 `backend/tests/api/test_i14_festival_lookup.py` | 권오현 / 검토 대기 | 11/23 |
| `route_key` HMAC | ✅ 좌표 HMAC · 🟡 추가 입력 예정 | 17-3, DB 설계서 4절 | 권오현 / 검토 대기 | 11/23 |
| 귀가 조회 토큰 확인 칸(011 `access_token_hash TEXT NOT NULL`, 원본 토큰은 DB에 저장하지 않음). 로그인·비로그인 모두 A05 토큰 해시 비교, **`user_id` 칸은 두지 않음** | 🟡 신유빈이 토큰 해시 추가·검증 방식에 동의. `user_id` 없이 구현. **확인 필요(신유빈)** — 서비스 계정 접속 정보, 기존 행 처리, 24시간 정리 실행 주체 | DB 설계서 4·8절. 011과 A04·A05 구현 완료·DB 시험 재실행 대기. 기존 요청은 보존하고 토큰 조회 대상에서 제외. [STEP4 SPEC](../../backend/Doc/route-providers/SPEC.md#7-step4-db-저장-강사-db-피드백-4) | 권오현 / 신유빈(토큰 해시 방식) | 11/23 |
| 축제 실제 수집 코드 = `api/ingestion/festivals/`(권오현), `tourapi_snapshot.py`(신유빈)는 증빙 파일 검증용 | ✅ 합의(11/23 신유빈) | 17-1 | 권오현 / 신유빈 | 11/23 |
| 연결 반납 때 `RESET ALL`(앞 사용자 정보 남지 않게) | 🟡 `yubeen` 브랜치에 구현(`6f767d9`), `ohyun` 미병합 · **독립 재검증 DB-09 통과(11/23 한태경, PG16 일회용 DB, 추가 시험 8개 + `test_session.py` 6개, 수정 전 방식으로 결함 재현 대조군 포함)** · 남은 것: PG17(pgvector:pg17)로 같은 시험 재실행, `ohyun` 연결 | 코드 `backend/shared/db/connection.py`, 시험 `backend/tests/db/test_session.py` 6개(둘 다 `yubeen` 브랜치), DB 설계서 3절 ⑤ | 권오현(기록) / 신유빈·한태경 | 11/23 |
| TMAP 유료 전환(결정 항목 `TMAP_PAID_PLAN` — 환경변수 아님) | ⬜ 미결정 | 9-2절, 바꾸면 환경변수 `ROUTE_TMAP_DAILY_LIMIT`(기본 10) 조정 | 팀 / 검토 대기 | 11/26 예정 |
| TourAPI 지역 코드 `12`(전남광주통합특별시) 나누기 | ⬜ 미결정(임시: 구→광주, 시·군→전남) | 0-1 지역 코드 | 권오현 → 팀 / 검토 대기 | 11/23 |
| RAG 임베딩 모델·차원·검색 방식·재적재·앱 사용법 포함 여부 | ⬜ 미결정 | DB 설계서 2절, WBS W27 | 한다영·권오현 / 검토 대기 | 11/25 예정 |

## 변경 이력

| 버전 | 날짜 | 바뀐 점 |
|---|---|---|
| v0.1 | 2026-11-17 | 첫 초안 (A01~A24, 도구 13개, 부록 A) |
| v0.2 | 2026-11-18 | **11/18 회의 반영**: A25~A30 추가(가는 길·지하철/버스 도착·공영주차장·교통 돌발·방문 집중 예측·데이터 지원 범위), A08 지도 표시 1차 10종(물품보관함·약국 보류, D-021), A03 입장료·소개, 경로 `evidence`(혼잡 구역·교통 돌발·버스 혼잡), 제외 항목 6-1절, 외부 공급원 13절, 지역 코드 0-1절·`coverage`·`REGION_UNSUPPORTED`, ODsay 일일 한도. **BFCL 맞춤**: `failure_domain` 값을 `route_upstream`·`crowd_upstream`으로 통일, 지역 값 `SEOUL`/`ALL`, 평가용 ID 설명, 부록 A 삭제(BFCL 문서가 기준). **기획서 v2.8 맞춤**: Supabase PostgreSQL 확정, Supabase Auth 제안. **강사 2차 의견**: 부하 시험 `cache_state`·`repeat_group`·`run_index`, 시뮬레이션 1회 : 사건 N건, 고유 키에서 병합 기각. 12절 예진님 6가지 결정 사항 제안 추가. **회의록 대조(11/18)**: 물품보관함·약국 보류(D-021), ODsay 결정 확인(사용자), 버스(TAGO)는 1차 서울만. **서비스 범위 D-020(멘토)·D-022(팀)**: 0-2절 — 전국에 있는 데이터는 전국, 지역별로만 있는 데이터는 서울만, 설정으로 지역 확대 |
| v0.3 | 2026-11-19 | **11/19 한태경 님 TMAP↔카카오맵 확인 반영**: 좌표 순서 변환, 정류장 연결 규칙, `service_running`(막차), TMAP 데이터 24시간 사용 제한. **기준**: 강사 일일 피드백(11/19) 5개, 멘토 2차 회의, 결정 D-033~D-039, 수업 가이드 「API 설계 문서 작성법」, 기획서 최신본(11/19). **공통**: 머리말(정본·진행 단계·검토 기록·서버 주소·`/docs`), 경로 `/api/v1`, ID 형식 통일(`trace_id` 미도입), 422(형식)와 400/403/409(서버 판단) 경계. **DB·인증(D-037)**: AWS Docker PostgreSQL, 자체 JWT, 인증 API A32~A35. **길찾기(D-038·D-039)**: 1차 TMAP · 2차 카카오맵(ODsay 제외), 카카오 결과는 저장·캐시 안 함·동기 전달만(`ROUTE_SECONDARY_SYNC_ONLY`), 공급원별 한도·비용 상한, 같은 좌표 비교 호출 계획, TMAP 정류장 ID로 버스 혼잡 연결. **상세 명세**: A04·A05·A19 8칸 + 필드 표, A02·A03·A15·A20 필드 표, A31 추가. **경로**: 근거를 지역 선택·교통수단 선택으로 분리, 추천 기준 5유형(기획서 FR-R01~R05와 같은 이름). **범위**: 버스 차내 혼잡 서울만(D-033), 자전거 존·택시 승강장 전국 공급원 없으면 서울(D-036), '확인 불가' 표시 규칙. **도구**: 공통 출력(`ok`·`retryable`)·실패 뒤 처리·description·JSON Schema 2개, BFCL 대조표. **복구 시험**: 세 구간 × 세 대응 방식, 재검증·종료 기준. **실호출 근거**: 11/19 한태경 님 10종(10절). **신규 기능**: A36~A41 목록(상세 v0.4). **검토**: AI 교차 검토 25건, 신유빈 님 검토(11/19), 정예진 님 피드백 6건 반영 |
| v0.3.1 | 2026-11-19 | **v0.3(팀 문서함 1차 업로드본) 이후 수정분**: 신유빈 님 검토 4건(변경 이력 정리·택시 범위·`trace_id` 미도입·최신 기획서 대조와 신규 기능 표기), 정예진 님 피드백 6건(경로 5유형 = FR-R01~R05, `created` 내부 상태, 카카오 2차 동기 전달만 `ROUTE_SECONDARY_SYNC_ONLY`), 한태경 님 TMAP↔카카오맵 확인(좌표 순서, 정류장 연결 규칙, `service_running`, TMAP 24시간 사용 제한), A36~A41 목록 |
| v0.3.2 | 2026-11-20 | **강사 11/19 피드백 1차 반영**: 정본 파일명 `Docs/Step 2/API_설계문서.md`·짝 문서 `DB_스키마_설계서.md`, 진행 단계(GitHub 업로드 ☑), 옛 'Supabase 확정' 문장 정리(기획서·WBS와 일치 확인). **11/19 한태경 실호출 반영**(10·10-2·11절): TMAP·카카오맵 서울·부산 정상(원본 삭제 → 합성 예시+호출 기록표), TMAP `stations` 키·`service` 막차 판단, 카카오 정류장 이름만, `stationID`≠`arsId` → 이름+거리 연결, 서울 버스 혼잡 `reride_Num1`, 경찰청 전국·XML, 택시(15139230)·자전거 전국, 주소→좌표 변환, `instt_nm` 정확 일치, TAGO 오류 `99` 재시도. `fallback_provider_switch`는 증빙 확보 전 비활성 유지. **피드백 2번 반영**: 필수 도구 6개 JSON Schema와 성공·실패 출력(ID 형식은 BFCL 가상 ID 때문에 스키마 대신 API가 검사), A05 응답 필드 표(`ROUTE_RESULT_EXPIRED`), **A06을 강사 11/19 워커 구조에 맞춰 비동기 작업으로 변경**(202 + `run_id`, A06-1 상태 조회, A06-2 SSE, `run_status` 5종, DB `assistant_runs` — 11/20 마이그레이션 002로 추가), A14·A16·A18·A21 8칸 상세. 오류 코드 `SIMULATION_NOT_FOUND`·`RUN_NOT_FOUND` 추가. **피드백 4번 반영**: 9-1절 제한값 기준표(시간 제한·재시도·폴링·캐시·동시 요청·토큰/키 수명, 설정 키·상태·확정 시험·담당, `LIMITS_VERSION`), 요청 수 제한 'N 미정' → 분당 10회(임시), **중복 방지 키 대조로 `route:inflight` TTL 5초 → 12초(처리 10초보다 먼저 만료되던 문제), `policy:route:active`에 안전 TTL, A06 선점 후 워커가 죽은 작업 정리 규칙** 추가. **DB 보존표(04 문서 7-0)와 맞춤**: 챗봇 답변·대화 상태에 경로 내용을 넣지 않는 규칙을 TMAP까지 넓힘(7-6). **피드백 1·3번 반영(11/20 한태경 증빙)**: 10절 증빙을 GitHub `Docs/Step 2/evidence/` 경로로 연결(호출 기록표·콘솔 사용량·합성 예시·원본 54개·키 없는 스크립트), 10-2 TMAP·카카오 필드 모두 확인(`totalTime` 초·`fare.regular.totalFare`·`passStopList.stations[]` 등), **10-3 길찾기 오류 응답 → 내부 처리표 신설**(TMAP 경로 없음도 HTTP 200 + `result.status`), 오류 코드 `ROUTE_NO_RESULT`, TMAP 종량제 미등록 → 비용 상한 0원, `fallback_provider_switch` 활성 조건 충족, TAGO 서면·`overview` 확인. **피드백 2번 추가**: A07~A13·A17·A22~A31 상세(6-2절, 공통 8칸 + API별 차이·원본 필드), 최종 범위 도구 5개 JSON Schema(4-6 ⑦~⑪) → 13개 도구 전부, 오류 코드 `NOT_IMPLEMENTED`·`QUEUE_ITEM_NOT_FOUND`·`ALREADY_REVIEWED`, `INGEST_SCHEDULE`. **피드백 5번 반영**: 6-3절 추가 기능 범위·작업 순서(계약 상태·미정 기술 결정 시점·핵심 일정 겹침·R03 12/03–08 과부하 제안). **축제 대표 이미지(D-031 확인)**: TourAPI `firstimage`·`firstimage2`·`cpyrhtDivCd` 원본 확인(16건 모두 이미지·`Type3`), A02 `thumbnail_url`·`image_credit`, A03 `image_url`·`thumbnail_url`·`image_copyright`, 이미지 규칙(주소만 저장·출처 표시·변경 금지·기본 이미지). **남은 것**: 추가 기능 상세 계약(W112, 정예진·권오현), 증빙 폴더 GitHub 업로드(신유빈) |
| v0.4 | 2026-11-23 | **강사 11/20 피드백 반영 재제출**: 0-A 반영표, 17절 첫 흐름 실제 실행(TourAPI 870건→DB→A02·A03, TMAP·카카오 실제 경로, 저장·캐시 규칙↔코드·시험), 18절 위치·대화 정보 전달 범위·차단 시험, 19절 결정 반영 기록, A02 `status` 여러 값(11/23), 개인 PC 경로 제거.<br>**교차 검토 반영(11/23, Codex·Gemini)**: 문서와 코드가 다른 곳을 현재 동작/구현 예정으로 나눔(A05 `ROUTE_RESULT_EXPIRED` 60초·`retryable=true`, 조회 토큰 만료 없음, `route_key` 입력 범위, 막차 후보 제외·카카오 `service_running`, 9-1 실제 환경변수·기본값, 장소 원문 메모리 보관), 0-A 1~5 🟡, A77 관리자 열람 = 신고된 메시지만, A02 여러 상태 규격(2-3·3절), 17-3 시험 함수명과 시험 수집 개수(DB 아닌 289 + DB 6), 19절 검토자 정리, 옛 BFCL 파일명·검토 기록 표 빈 줄 정리<br>**첫 흐름 연속 실행(11/23, 17-5절)** — 실제 축제 검색·상세와 TMAP 귀가 완료, 모의 A05 처리 중·실패 3종의 응답 요약 및 재실행 스크립트 추가. 0-A 1번은 화면 연결·후속 기능 합의·11/27 상태 전이 설계 연결이 남아 🟡 유지.<br>**W89 A10(11/23)** — 서울시 공식 구역 경계 1km 이내 최대 3곳, 실제 모드, 대체 평균 표시 및 기존 응답 호환을 반영했습니다. |
| v0.4 | 2026-11-23 | **W36 STEP3 막차 처리**. TMAP 운행 종료 후보 제외·모두 종료 시 `ROUTE_NO_RESULT`, 카카오 `service_running:null`과 '막차 확인 불가'를 실제 모드 코드·합성 응답 시험에 반영(5절·17-3·19절). |
| v0.3.3 | 2026-11-20 | **팀 답변 반영(11/20 오후)**: A42 `GET /api/v1/festivals/trending` 지금 핫한 축제(크롤링·LLM 없음·규칙 연결, 6-2, 6-1 크롤링 제외 범위 수정, 13절 공급원), A36 취향 값 5개, 6-3 결정 반영(추천 신유빈·채팅 WebSocket·동행 3일/친구 30일·채팅 열람 참여자·관리자·권한 기준안), 목적지 라벨을 DB에서 빼 Redis 24시간(`ROUTE_LABEL_TTL_H`)·장소 해시 HMAC, `TREND_CRAWL_SCHEDULE`, 태경님 남은 확인 일정(11/20·11/24·11/25), 증빙 파일명 실제와 맞춤(`합성예시_kakao-transit_*`), GitHub 업로드 상태(v0.3.2 `41c66a5`)  **추천·친구 상세(6-4)**: 축제 → 취향 5개 분류(규칙 후보 → LLM 검증 → 근거 문장이 원문에 그대로 있는지 코드 확인), 점수 `rec-0.1`, A36~A41 상세, **친구 API A43~A50**(친구 코드 검색·신청·수락·차단, 친구 추천은 범위 밖), DB 005 연결, 오류 코드 4개, `TAG_LLM_DAILY_MAX`  **강사 11/20 자료 「설계서 한 줄을 실제 동작으로 연결하기」 반영**: 6-5 기능 연결표(요구사항→화면→API→도구→DB→시험, 실행 범위 A~D 표시, 계약 담당·인계), A06-1 모의 응답 3가지(진행 중·완료·실패)  **기획서 필수 기능 전체 대조(15-1 추적표, Must 131개 모두 위치 연결)**: 빠져 있던 **A51 AI 방문 코스**(FR-P01·P03, 코스 검증 규칙)·**A52~A54 공식 공지 등록·수정·승인**(FR-O06·D05)·**A55~A56 축제 직접 등록·수정**(FR-D12·O10) 추가(6-6), DB 006 연결, 오류 코드 2개  **동행·채팅·알림·신고 상세(6-4-4~6-4-6)**: A57~A65 동행(정원 잠금 승인·재신청 규칙·만남 장소 권한·자동 종료), A66~A73 채팅 + WebSocket 메시지 형식(DB 저장 뒤 ACK, `client_message_id` 중복 방지, 방별 순서, 입장 뒤 메시지만, 초대 수락 전 차단, 방장 승계), A74~A80 알림·신고(관리자 열람 기록)·마이페이지·탈퇴, DB 007 연결, 9-1 채팅 제한값, 오류 코드, 15-1 추적표 FR-COM 전부 ✅ **제출 전 교차 검토 반영(15:00~16:30)**: Claude·Codex·agy 지적 중 문서 19건 — 범위·검토 기록·6절 범위표 옛 문장, 1절 권한표, **인증 A32~A35 상세(1-1)**, 2차 공급원 전환 기준(10-3 표 기준·동기 3초), 운행 종료 후보 제외, A06-1 `route_access_token`·`run_kind`·`result`, 에이전트 입출력 파일 경로 금지, 채팅 Redis 거르기·구독 해제·`notification` 이벤트·경로 등록 순서, A77 글 숨김, A80 탈퇴 목록·덮어쓰기, 12절 Supabase 문장, 14절 크롤링, 10-1·11절 완료 항목. **한태경 11/20 15:03**: 공식 한도(9-1 ⑤), TMAP 유료 전환 제약·오류 포함 셈, 카카오 공식 답변(저장 불가·타사 지도 표시 가능), 서울 정류장 OA-15067, 이미지 CSS 크기 조절, 15:48 최종 정리(`service`·`lane` 판단, SK 문의 11/20 발송, OA-15067 확인 완료, 관광공사 문의 안 함). **추천**: 취향 `pet_or_baby` → `pet`(아기 동반 제외, 반려견은 별도 칸 없이 취향 값 하나 — 기획서 11/20 15:32 main과 같음). **9-2절 추가(16:30)**: 경로 1회 비용·예상 운영비 계산식·빈칸 담당(강사 요청). **16:45**: 한태경 단가 확인(TMAP 0.88원 부가세 포함, 카카오 초과 11원·장소 검색 2원·지도 0.1원), 증빙 스크립트 카카오 저장 제거 ✅. 제출 뒤 처리 11-1절 **기능 상세 시나리오 반영(17:30, 신유빈 초안 + 사용자 결정)**: A04 `origin`(출발 위치 변경)·A25 `destination`(도착 변경), A32 닉네임·출생연도·성별 필수, A43 닉네임 정확히 일치 검색(친구 코드 삭제)·A78 닉네임 변경, A61 신청자 나이·성별(작성자만), A76 `chat_room` 신고, 앱 사용법 RAG — DB 009. 크롤링(A42)은 유지. **17:31 변경분 교차 검토(Claude·Codex·agy) 반영**: 닉네임 검색 차단 관계 제외, 3절 `Endpoint` 입력 모델, 9-2 카카오 최대 154,000원/일·유료 가정 표시, A61 나이(출생연도 대신), A77 `close_room`, `NICKNAME_TAKEN` 공통 오류, 나머지 11-1 #15 |
| v0.4 | 2026-11-23 | **STEP4 귀가 DB 저장(강사 DB 4)**. 011·A04/A05 요청 상태·TMAP 요약 저장, 서비스 계정 토큰 확인·10분 만료, 카카오 동기 전용과 TMAP 정리 구현. 실제 DB 시험 재실행 대기(17-3·19절). |
| v0.4 | 2026-11-23 | **강사 API 3 백엔드 로그 시험**. A04·A05·장소 검색·A10의 원문 차단과 요청 ID·상태 기록을 모의·실제 모드(가짜 전송)에서 검증하고 0-A·18절 갱신. |
