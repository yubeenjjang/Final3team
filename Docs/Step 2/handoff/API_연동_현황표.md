# API 연동 현황표 — 프론트·에이전트용 (권오현, 2026-11-23)

> 신유빈 님 11/23 요청 ④(요청·응답 예시, 필수 입력값, 상태·오류 코드, 실제·모의 구분, API별 진행 상황과 연동 가능일)와 강사 11/20 API 피드백 1·2(시연에서 모의 구간과 실제 구간 구분, 동기 전용 결과 구분)에 답하는 문서입니다.
> **원칙:** 모의 → 실제로 바뀌어도 주소·요청과 기존 응답 키를 유지합니다. 실제 응답은 `is_mock:false`이며 A10은 실제 구역 목록 등 선택 필드를 추가합니다. 화면은 지금 모의 서버로 붙이고, 실제 전환일에 주소(`NEXT_PUBLIC_API_BASE`)만 바꾸면 됩니다.
> 자세한 요청·응답 예시: [`backend/api/MOCK_API.md`](../../../backend/api/MOCK_API.md)(curl 예시·시나리오) · 화면별 흐름: [프론트_모의API_연결.md](프론트_모의API_연결.md) · 계약 원문: API 설계문서 v0.4

## 1. API별 상태 (12/8 중간 시연 흐름 = ★)
| API | 주소 | 지금 | 실제 연결 예정 | 실제 데이터 | 근거(WBS) | 비회원 |
|---|---|---|---|---|---|---|
| ★ A02 축제 목록·검색 | `GET /festivals` | **실제 ✅ 11/23** (`FESTIVAL_DATA=db`, 기본은 모의) | — | TourAPI 전국 축제 870건(공개 869) | — | ✅ |
| ★ A03 축제 상세 | `GET /festivals/{id}` | **실제 ✅ 11/23** (`FESTIVAL_DATA=db`) | — | TourAPI 상세(소개·입장료는 원본에 있을 때만) | — | ✅ |
| ★ A04·A05 귀가 경로 | `POST /routes/return` → `GET /routes/return/{id}` | 기본 모의 · 실제 모드 막차 및 `ROUTE_STORE=db` 연결 구현, DB 시험 재실행 대기 | **11/27** | TMAP 1차 · 카카오 2차 | W36 · 강사 DB 4 | 접수는 비회원 가능. DB 상태 조회 토큰은 접수 후 10분 유효 |
| A25 가는 길 | `POST /routes/visit` → `GET /routes/visit/{id}` | 기본 모의 · 실제 모드 막차 및 DB 저장 구현, DB 시험 재실행 대기 | 11/27 (A04와 같은 코드) | 같음 | W36 | A04·A05와 같음 |
| A10 주변 지역 혼잡(서울만) | `GET /festivals/{id}/crowd` | 기본 모의 · 승인된 연결만 실제 조회 가능 | 매핑과 HTTP 전송 확인 후 | 서울시 실시간 인구 관측값 · 승인 구역 중 1km 이내 최대 3곳 | W89 | ✅ |
| A09 날씨 | `GET /festivals/{id}/weather` | 모의 | 11/30 | 기상청 단기예보 | W34 | ✅ |
| A07 공지·통제 | `GET /festivals/{id}/notices` | 모의 | 12/10 | 공식 공지 수집 | 유빈 11/23 일정 | ✅ |
| A08 주변 시설 | — | **없음** | 12/09 | — | 유빈 11/23 일정 | — |
| A32~A35 가입·로그인 | `/auth/*` | 모의(메모리) | 11/26 목표, **시연 흐름 뒤로 밀릴 수 있음** | DB `users` | W18 | — |
| A11~A13 관심 축제 | `/me/favorites` | 모의 | 12/02 | DB `favorites` | W41 | ❌ 로그인 |
| A06 AI 질문 | `POST /assistant/query` → `GET /assistant/runs/{id}` | 모의(키워드로 흉내) | 12월(에이전트 연결) | LangGraph | W24·W45 | ✅ |

- 날짜는 **목표일**입니다. 늦어지면 이 표를 먼저 고치고 디스코드에 알립니다(실제 전환 = 이 표의 '지금' 칸이 '실제'로 바뀜).
- 실제 전환 뒤에도 **모의 서버는 남겨** 둡니다(시험·시연 예비용, `APP_ENV≠prod`).

- **11/23 추가:** A02 `status`에 여러 값(`status=ongoing,upcoming`) — 화면에서 끝난 축제를 빼고 부를 때. 기존 한 값 사용법은 그대로.
- **11/23:** DB 모드에서도 귀가·공지·날씨·혼잡·관심·AI 질문이 **실제 축제 ID**를 받습니다.
- **11/24 W89:** A10의 화면 문구는 ‘주변 지역 혼잡’입니다. 실연동 승인 0건이며 대체 평균은 표시에서 제외합니다. [시연 후보와 승인 기준](../../../backend/Doc/seoul-crowd/SPEC.md)

## 2. 귀가 조회 상태값 — 화면이 구분해야 할 것
| `route_status` | 뜻 | 화면 | `completed_valid_route` |
|---|---|---|---|
| `queued` · `processing` | 접수됨·찾는 중 | 로딩, `retry_after_s`(2초)마다 다시 조회 | false |
| `ready` | 경로 있음 | 경로 그리기 + **출처(`provider`)·조회 시각(`queried_at`)** 표시 | **true** (이때만 '성공') |
| `unavailable` | 공급원이 답을 못 줌 | `error.message` + `notices`(공식 안내) | false |
| `timed_out` | 시간 초과 | 같음 + 다시 시도 버튼(`retryable`) | false |
| `rejected` | 요청이 많아 거절(접수 단계 503) | "잠시 뒤 다시" | false |

## 3. 귀가 오류 코드 (`error.code`)
| 코드 | 언제 | `retryable` | 화면 문구 예 | 모의로 만들기(`X-Mock-Scenario`) |
|---|---|---|---|---|
| `ROUTE_UPSTREAM_ERROR` | 공급원 오류 | true | 경로 정보를 가져오지 못했어요 | `async_unavailable` |
| `ROUTE_TIMEOUT` | 처리 제한 시간 초과 | true | 경로를 찾는 시간이 초과됐어요 | `async_timeout` |
| `ROUTE_OVERLOADED` | 과부하(503) | true | 요청이 많아요, 잠시 뒤 다시 | `overloaded` |
| `ROUTE_SECONDARY_SYNC_ONLY` | 2차(카카오) 결과는 저장할 수 없어 **나중 조회로 줄 수 없음** | true | 잠시 뒤 다시 조회해 주세요 | `async_secondary_sync_only` · `sync_secondary` 뒤 재조회 *(6단계 추가)* |
| `ROUTE_NO_RESULT` | 조건에 맞는 경로 없음 또는 TMAP 후보 모두 운행 종료 | **false** | 조건에 맞는 경로가 없어요 / 지금은 대중교통으로 갈 수 없어요 | `async_no_result` *(6단계)* |
| `ROUTE_QUOTA_EXCEEDED` | 공급원 하루 한도 소진 | **false** | 공식 교통 안내를 확인해 주세요 | `async_quota_exceeded` *(6단계)* |
| `ROUTE_ACCESS_EXPIRED` (200 `unavailable`) | DB 접수 10분 후 동일 `request_id`·본문 재전송. 기존 경로 ID 반환 | **false** | 경로 조회 시간이 지났어요. 새 요청 ID로 다시 요청해 주세요 | — |
| `ROUTE_INVALID` (400) | 목적지를 못 찾음 | false | 목적지를 찾을 수 없어요 | 목적지에 `없는곳` |
| `FESTIVAL_LOCATION_UNKNOWN` (400) | 축제 좌표 없음 | false | 축제 위치를 확인할 수 없어요 | `fst_000006` |

## 4. 공급원 구분 — 꼭 지킬 규칙 (강사 피드백 API 2)
| `provider_tier` | 공급원 | 받는 방법 | 다시 보기 |
|---|---|---|---|
| `primary` | TMAP | 200(바로) 또는 202 → 상태 조회 | 결과 보존 시간 안에는 A05로 다시 조회 가능 |
| `secondary` | 카카오맵 | **200(접수 응답) 안에서만** | ❌ 저장 불가 → 다시 보려면 **새로 요청**. A05로 다시 부르면 `ROUTE_SECONDARY_SYNC_ONLY` |
| `mock` | 모의 서버 | 둘 다 | 가능 |
- 실제 모드에서는 TMAP의 운행 종료 후보를 제외하고 남은 후보만 표시합니다. 카카오 후보는 `service_running=null`이며 '막차 확인 불가'는 `notices`에 들어갑니다.
- 화면은 `secondary` 결과를 받으면 **그 화면에서 바로 그리고**, 새로고침·뒤로가기 뒤에는 '다시 조회' 버튼을 보여 주세요(같은 결과를 다시 불러올 수 있다고 안내하지 않기).
- 시연에서는 화면 구석의 **'모의 데이터' 표시(`is_mock`)**로 모의/실제 구간을 구분합니다.

## 5. 변경 기록
| 날짜 | 내용 | 작성 |
|---|---|---|
| 11/23 | 처음 작성. 6단계(2차 공급원·오류 시나리오) 모의 서버 반영 | 권오현 |
| 11/23 | A02·A03 실제 DB 조회(TourAPI 870건), 여러 상태 필터, 실제 축제 ID로 귀가 등 연결 | 권오현 |
| 11/23 | W36 STEP3 막차 처리와 합성 응답 시험 반영(기본 모의 유지) | 권오현 |
| 11/23 | STEP4 011 및 A04/A05 DB 저장 구현. 일회용 DB에서 같은 축제로 연속 검증 대기 | 권오현 |
| 11/24 | A04·A25 토큰 만료 뒤 재전송 응답 명시, P18 축제 시험 데이터·조회 계정 수정 | 권오현 |

11/24 백엔드 전체 오프라인 pytest 377개 중 **365개 통과, DB 표시 12개 건너뜀(P18 4개 포함)**. 11/23 밤 로컬 DB는 SQL·백업 로그 PASS 156건, 백엔드 DB 시험 9개 통과·3개 실패였습니다. 수정 후 **DB 시험 재실행 대기**입니다. [귀가 경로 구현 계획](../../../backend/Doc/route-providers/IMP-PLAN.md#step4-db-저장)
