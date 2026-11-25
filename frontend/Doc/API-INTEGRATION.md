# 놀다가(NOLDAGA) 프론트엔드 API 연동 명세·체크리스트

> **파일:** `API-INTEGRATION.md`  
> **버전:** v1.0 · 2026-11-25 · **개발 연동용 초안 / 실제 계약 검증 필요**  
> **연관:** [`FRONTEND-PLAN.md`](./FRONTEND-PLAN.md), [`FRONTEND-IMP-PLAN.md`](./FRONTEND-IMP-PLAN.md), [`UI-DESIGN-SYSTEM.md`](./UI-DESIGN-SYSTEM.md)

## 0. 먼저 읽기: API 버전과 정보 출처

이 문서는 사용자가 제공한 다음 자료에 근거해 작성했다.

1. **`UI_요청_1124.md` (2026-11-24)** — 백엔드가 UI에 요청한 A1~A12 필수 상태 및 B1~B8 추가 상태. 이 문서는 **API 설계서 v0.5**를 근거로 한다고 명시한다.
2. **`03_API_설계문서 (2).md` v0.3 (2026-11-19)** — 지금 확인 가능한 실제 경로·필드·인증·에러 형식 참고 문서. 문서 자체가 **팀 검토 전 API 설계안**이라고 밝힌다.
3. **최신 사용자 확정 UI** — 찜/하트/알림/소셜 로그인 제거, 축제 포스터 규격, 공통 메뉴, 혼잡/귀가 문구.

> **중요:** v0.5 정본/실제 Swagger 응답은 이 문서 작성 과정에서 검증하지 못했다. 아래 URL은 **v0.3에 기록된 설계 경로**이므로 실제 서버에서 그대로 동작한다고 단정하지 않는다. v0.3과 11/24 UI 요청이 다른 부분(예: 경로 선호값)은 **11/24 요청을 UI 목표로 기록하고 실제 계약 확인을 `TODO`로 둔다.**

## 1. 연결 기본 규칙

| 항목 | 기준 |
|---|---|
| API 서버(개발 예시) | `http://localhost:8000/api/v1` (v0.3 문서의 개발 기준, 환경별 조정) |
| 실제 배포 서버 | 미정; 인프라 담당이 배포 URL 공유 시 반영 |
| 콘텐츠 형식 | `application/json; charset=utf-8` |
| 날짜/시간 | ISO 8601 + KST (`+09:00`); UI는 한국 시간으로 표시 |
| 요청 ID | `X-Request-ID` 사용/응답 반영. 실패 분석·중복 요청 확인에 사용 |
| 목록 페이지 | `page`(1부터), `page_size`(기본 20, 최대 100) — v0.3 설계안 |
| 실패 형식 | `{ error: { code, message, request_id, retryable } }` — v0.3 공통 형식 |
| 인증 | FastAPI 자체 JWT(Access/Refresh) 기준; 최종 저장 방식은 백엔드와 합의 |
| 외부 데이터 | 브라우저→**놀다가 백엔드**만 호출; 외부 TourAPI/TMAP/서울시 키 브라우저에 넣지 않음 |
| 미지원 지역 | `unsupported` 혹은 `coverage.supported=false`; 다른 지역 값을 대체 표시하지 않음 |
| 모의 자료 | `is_mock=true`이면 실제 안전/교통 정보로 오인하지 않게 표시 |

### 1.1 현재 개발 환경(Next.js App Router)

```dotenv
# .env.local : 프론트에서 접근 가능한 주소만 기록
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
```

- `NEXT_PUBLIC_` 접두사 변수는 번들에 들어갈 수 있으므로 **비밀번호, JWT 서명키, 외부 공급원 API Key를 절대 보관하지 않는다.**
- 개발 서버 CORS와 프록시, HTTPS/HTTP 혼합 콘텐츠 정책은 인프라와 협의한다.

## 2. 우선 연동 API 목록(v0.3 설계 기준)

| 설계 ID | 메서드 / 경로 | 화면 | 응답/주의 사항 | 우선 |
|---|---|---|---|---|
| A02 | `GET /festivals` | 홈·축제·검색 | `items`, `total`, `page`, `page_size`; `thumbnail_url` null 가능 여부 확인 | P0 |
| A03 | `GET /festivals/{festival_id}` | 축제 상세 | 이름·기간·좌표·소개·`image_url` 등 optional 필드 | P0 |
| A04 | `POST /routes/return` | 귀가 조회 | 200(결과)/202(접수), `route_status`·후보·처리 중 토큰 | P0 |
| A05 | `GET /routes/return/{route_request_id}` | 경로 상태 | `queued`/`processing`/`ready`/실패, 202에서 받은 조회 토큰 | P0 |
| A06 | `POST /assistant/query` | AI 질문창 | 챗봇(12/8은 예시 응답 가능, **모의 여부 표시**) | P0 UI |
| A07 | `GET /festivals/{festival_id}/notices` | 공식 공지 | 운영·통제·무정차·우회 안내 등 | P0/P1 |
| A08 | `GET /festivals/{festival_id}/facilities` | 상세·지도 | 지원되는 시설만, `coverage`/`unverified` 확인 | P1 |
| A09 | `GET /festivals/{festival_id}/weather` | 상세 날씨 | 발표 시각·값 없음·실패 처리 | P1 |
| A10 | `GET /festivals/{festival_id}/crowd` | 상세 혼잡 | 서울 데이터 지원 구역 한정, 4단계·근접 최대 3구역 | P0 |
| A32 | `POST /auth/signup` | 회원가입 | v0.3은 이메일·비밀번호·표시 이름; 추가 필드 확인 | P1 |
| A33 | `POST /auth/login` | 로그인 | JWT 발급 | P1 |
| A34 | `POST /auth/refresh` | 세션 유지 | Refresh 교체; 저장/갱신 방식 확인 | P1 |
| A35 | `POST /auth/logout` | 로그아웃 | 토큰 폐기 | P1 |
| A25 | `POST /routes/visit` | 축제 가는 길 | 범위 확정 후 | P2 |

위 표의 URL은 공통 기준 주소 `/api/v1`을 **생략해 표기**했다. 실제 호출 예: `GET http://localhost:8000/api/v1/festivals`.

### 2.1 v0.3에 있지만 최신 UX에서 사용하지 않는 API

v0.3 문서에는 A11~A13인 `/me/favorites` 관심 축제 조회·저장·삭제가 존재한다. 그러나 놀다가는 **찜하기를 최종 제외**했으므로 **프론트에서 이 API를 호출하거나 하트 UI를 구현하지 않는다**. 백엔드 API/DB에 과거 필드가 남아 있더라도 UI에는 노출하지 않는다.

또한 과거 문서에 식당·관광 추천이 있어도 최신 사용자 확정 기획에서 제외되었으므로 별도 추천 카드로 넣지 않는다.

## 3. 축제 목록/상세 데이터 계약

### 3.1 축제 목록 A02 (v0.3)

**예상 Query**

| 이름 | 형식 | 설명 |
|---|---|---|
| `region` | string | `ALL` 또는 시·도 코드 |
| `date_from`, `date_to` | `YYYY-MM-DD` | 조회 기간(최대 366일 조건은 v0.3 초안) |
| `q` | string | 축제/장소 검색어 |
| `status` | string | `upcoming/ongoing/ended/cancelled` |
| `bbox` | string | 지도 범위 `minLng,minLat,maxLng,maxLat` |
| `sort` | string | `start_date`, `-start_date`, `name`, `distance` 등 |
| `page`, `page_size` | number | 페이지네이션 |

**예상 응답 목록 필드**: `festival_id`, `name`, `region_code`, `venue_name`, `lat`, `lng`, `start_date`, `end_date`, `event_status`, `thumbnail_url`, `source`, `last_synced_at`.

- 빈 배열 + `total:0`이면 **정상 빈 결과**로 안내.
- 검색한 `festival_id`가 없어서 404 `FESTIVAL_NOT_FOUND`면 존재하지 않는 축제 안내.
- 목록 카드 기본 정보: 사진(없으면 fallback), 이름 2줄, 날짜, 지역. D-day는 KST 날짜와 실제 이벤트 시작일로 계산.
- 축제 목록 API에서 인기/추천/신규 순위가 직접 제공되는지는 **확인 필요**. 검증된 백엔드 정렬/추천 없이는 임의 순위를 실제 순위로 표시하지 않는다.

### 3.2 축제 상세 A03 (v0.3)

| 필드 | UI 사용 | null/미확인 처리 |
|---|---|---|
| `festival_id`, `name` | 축제 상세 식별자·제목 | 필수로 문서화됨 |
| `region_code`, `venue_name`, `address` | 지역·장소 | 주소/장소 null 가능; 없으면 빈 라벨 강제 노출하지 않음 |
| `lat`, `lng` | 지도·귀가 출발 좌표 | null이면 지도/귀가 기능 제한 및 안내 |
| `start_date`, `end_date` | 일정·D-day | 미정 일정이면 '일정 확인 필요' 등 |
| `event_status` | 예정·진행·종료 | 과거 일정을 현재 개최처럼 표시하지 않음 |
| `overview` | 축제 소개 | 없으면 상세 소개 섹션 숨김/기본 안내 |
| `fee_text` | 입장료 | 없으면 무료라고 추정하지 않음 |
| `homepage_url` | 공식 정보/예매 링크 | 실제 URL 유효성 및 공식 출처 확인 |
| `image_url` | 상세 상단 포스터 | null이면 로고+'이미지 준비 중' |
| `source`, `source_ref`, `last_synced_at` | 출처·수집 시각 | 확인 가능한 시간만 표시 |

- **포스터 UI 비율은 항상 가로:세로 1:1.414**, 원본 이미지는 `contain` 또는 `cover` 정책을 구분.
- `주요 프로그램`·해시태그는 TourAPI에 없는 경우가 있으므로 **값이 없으면 섹션 자체 숨김** (11/24 UI 요청 C2).
- 확정 디자인에 등장하는 '서울 빛 축제', 시연 날짜, 혼잡 수치는 **예시 UI 데이터**일 수 있으므로 진짜 행사 정보/실시간 값으로 가정하지 않는다.

## 4. 주변 지역 혼잡 A10 — UI 우선 규칙

11/24 요청서에 제시된 응답 요소: `congest_level`, `congest_color`, `nearby_areas`, `observed_at`, `stale`, `unsupported`. **정확한 JSON nesting 및 응답 오류 형식은 v0.5/Swagger 확인 필요.**

### 4.1 표시 규칙

| 응답 상태 | 화면 표시 | 하지 말아야 할 일 |
|---|---|---|
| `여유` | 초록 상태 라벨 | 임의 퍼센트 생성 금지 |
| `보통` | 노랑 상태 라벨 | '안전' 보장 문구 금지 |
| `약간 붐빔` | 주황 상태 라벨 | 공식 '위험' 판정으로 단정 금지 |
| `붐빔` | 빨강 상태 라벨 | '위험'이라고 무조건 변환 금지 |
| `nearby_areas` 존재 | 구역 이름 · 혼잡 단계 · 거리(m) 최대 3개 | 없는 거리값 추정 금지 |
| `observed_at` 존재 | `16:40 기준`처럼 표시 | 현재 시각과 혼동 금지 |
| `stale: true` 또는 45분 초과 | '정보가 오래됐어요' | 실시간 데이터처럼 추천 근거 사용 금지 |
| `unsupported` / 서울 밖 | '이 지역은 혼잡 정보가 없어요' | 서울 값을 다른 지역에 대입 금지 |
| 공급원 오류 | '혼잡 정보를 확인할 수 없어요' | 이전 값을 LIVE로 표시 금지 |

- **디자인 내 기존 '현재 혼잡도 높음 (약 85%)' 삭제**, 대신 '주변 지역 혼잡' 사용.
- 45분 최신성 기준은 11/24 요청값. 서버 `stale`이 있다면 우선 적용하고 클라이언트 시간 검증은 보조적으로 사용한다.
- 해당 지역 공식 위험 정보와 일반 혼잡 4단계는 별도 컴포넌트로 취급한다.

### 4.2 UI 상태 타입 예시(실제 DTO가 아님)

```ts
type CrowdView =
  | { kind: 'available'; level: '여유' | '보통' | '약간 붐빔' | '붐빔';
      observedAt: string | null; stale: boolean;
      areas: Array<{ name: string; level: string; distanceM: number | null }> }
  | { kind: 'unsupported' }
  | { kind: 'unavailable' };
```

실제 API 응답을 **위와 같은 UI 모델로 변환하는 Adapter**를 둔다. DTO 내부 형식을 UI에 직접 결합하지 않는다.

## 5. AI 안심귀가 A04/A05 — 상태 전이

### 5.1 경로 선호값(11/24 요청 A10 우선)

| UI 라벨 | `route_preference` 값 |
|---|---|
| 가장 빠른 | `fastest` |
| 도보 최소 | `min_walk` |
| 환승 최소 | `fewest_transfers` |
| 혼잡 적은 | `less_crowded` |
| 이동 편한 | `accessible` |

**주의:** 접근 가능한 **v0.3 문서는 `relaxed`, `shortest` 등과 다른 코드**를 사용했다. 11/24 UI 요청에서는 위 5개로 맞추라고 명시했으나 **백엔드 실제 구현 값은 v0.5 정본으로 반드시 재확인**해야 한다. 불일치 시 임의로 송신하지 않는다.

### 5.2 요청/상태 조회 개념

1. 사용자가 축제·목적지·조건을 입력.
2. `POST /routes/return`에 **중복 방지 `request_id`**를 포함해 전송(정확한 body는 최신 Swagger 확인).
3. **HTTP 200**: `route_status`를 확인하고 `ready`일 때만 검증된 후보 표시.
4. **HTTP 202**: `route_request_id`, `route_access_token`, `retry_after_s`, `status_url` 보관 → '경로를 찾는 중이에요' 상태.
5. `GET /routes/return/{route_request_id}` 상태를 제한된 간격으로 조회. **v0.3 임시 정책: 2초 간격, 최대 5회**. 실제 서버의 `retry_after_s`를 우선 고려.
6. **`ready` + 검증된 후보 존재** → 후보 카드/지도/실제 출처 표시.
7. `unavailable`, `timed_out`, `rejected`, `ROUTE_NO_RESULT` → 각 오류 화면 + 공식 안내/재시도.
8. 새 요청으로 전환·화면 이탈 시 기존 폴링 취소, 이전 응답이 새 화면을 덮어쓰지 않게 한다.

### 5.3 상태 매핑표

| 값 / 상황 | UI 화면 | CTA |
|---|---|---|
| `queued` | 경로 요청 접수, 처리 중 | 중복 요청 제한 |
| `processing` | 경로를 찾는 중 | 취소/대기 안내 |
| `ready` + valid candidates | 후보 카드 1~3개, 실제 출처 | 상세 경로 선택 |
| `ready` + 후보 없음 | 정상 성공처럼 표시 금지; 데이터 확인 필요 | 공식 안내/재검색 |
| `unavailable` | 지금은 경로를 확인할 수 없어요 | 다시 시도 · 공식 안내 |
| `timed_out` | 시간이 초과됐어요 | 다시 시도 · 공식 안내 |
| `rejected`/429/503 | 요청이 많아요 | 잠시 후 재시도 |
| `ROUTE_NO_RESULT` | 운행이 끝난 노선이 있어 안내할 경로가 없어요 | 공식 운행 정보 |
| Kakao `service_running: null` | **막차 확인 불가** 작은 안내 | 공식 운행 정보 |
| 경로 공급원 TMAP | 지도 아래 **'경로 정보: TMAP'** | 출처 확인 |
| `is_mock: true` | 시연/예시 데이터 표시 | 실제 교통 안내로 오인 방지 |

### 5.4 지도 표현

- 11/24 팀 결정: **TMAP 경로를 카카오 지도에 그림**. 공급원과 지도 렌더러를 혼동하지 않는다.
- 경로가 카카오 대체 응답이면 출처도 실제 응답의 `provider`로 표시.
- `provider`, `queried_at`, `verification_status`, `constraint_status`, 공식 공지 검증 여부를 활용한다.
- 통제·무정차가 확인되지 않았거나 `constraint_unverified`이면 경로 카드에 '확인 불가'를 명시하고 안전을 보장하지 않는다.
- 막차 여부를 추정하지 않고, `service_running:null`은 **확인 불가**로 남긴다.

## 6. 인증/회원가입/취향/동행 — 계약 확인 필요

### 6.1 v0.3 문서 기준 인증 API

| 엔드포인트 | 내용 | 주의 |
|---|---|---|
| `POST /auth/signup` | 가입(이메일·비밀번호·표시 이름) | UI는 성별·출생연도도 입력 → 백엔드 필드 추가/프로필 수정 API 확인 |
| `POST /auth/login` | 로그인·Access/Refresh | 저장/갱신 전략 검토 |
| `POST /auth/refresh` | Refresh 교체 | 갱신 실패 시 세션 만료 안내 |
| `POST /auth/logout` | 로그아웃·토큰 폐기 | 실패해도 클라이언트 민감 상태 안전하게 정리 |

- v0.3의 Access 30분/Refresh 14일은 **임시값**이다. 실제 TTL 확정 필요.
- Refresh를 `HttpOnly; Secure; SameSite` 쿠키로 전송할지 별도 규약을 정한다. 현재 문서만으로 **어떤 저장 방식인지 확정하지 않는다.**
- 로그인 필요 기능만 인증을 요구한다. **축제 찜·관심**은 삭제됐으므로 인증 유도 대상에 넣지 않는다.

### 6.2 화면은 있는데 API가 미확인인 영역

| 기능 | 프론트 화면 요구 | 백엔드 확인할 내용 |
|---|---|---|
| 프로필 조회·수정 | 닉네임·성별·출생연도 | 엔드포인트, 수정 허용 필드, 409 충돌 |
| 취향 저장 | 5개 중 복수 선택, 건너뛰기 | enum 값, 배열 중복, 저장/읽기 URL |
| 맞춤 추천 | 취향 기반 축제 목록 | 추천 API, 결과 순서, 빈 결과 의미 |
| 동행 모집·신청 | 동행 목록/상세, 신청·승인 대기 | 모집·신청·승인 API와 권한 |
| 동행 채팅 | 채팅방 목록/실시간 메시지 | REST/WebSocket, 신고·차단·퇴장 상태 |
| 신고/차단 | 신고 6개 사유 등 | A76 등 실제 API 버전 |
| 외부 예매 링크 | 공식 예매처 열기 | 확인 가능한 `homepage_url`/ticket 필드 여부 |

**이 표에 경로를 임의로 만들어 적지 않는다.** Swagger 또는 백엔드 담당자의 확정 스키마를 받은 뒤 추가한다.

## 7. 공통 오류 처리 표

| 조건 | 화면 UX | 구현 주의 |
|---|---|---|
| HTTP 400/422 | 입력값 확인·수정 | 검증 오류 정보 기반 |
| HTTP 401 | 다시 로그인해 주세요 | 재발급 정책과 무한 반복 방지 |
| HTTP 403 | 이용 권한이 없어요 | 존재하지 않는 권한을 UI에서 부여하지 않음 |
| HTTP 404 `FESTIVAL_NOT_FOUND` | 축제를 찾을 수 없어요 | 목록 0건과 구분 |
| HTTP 409 | 동일 요청/상태 충돌 안내 | 요청 재전송 전 상태 확인 |
| HTTP 429 | 요청이 많아 잠시 후 다시 시도해 주세요 | 지수 백오프/서버 힌트 검토 |
| HTTP 503 `DB_POOL_TIMEOUT` | 같은 토스트 + 다시 시도 | 축제 정보 전체를 예시 데이터로 몰래 대체 금지 |
| 네트워크/타임아웃 | 정보를 불러오지 못했어요 | 안전 관련 기능은 '확인 불가' 명시 |
| null 이미지 | 이미지 준비 중 | 카드+상세 기본 이미지 |
| null 날씨 | 숨김 또는 날씨를 불러오지 못했어요 | 발표 시각도 별도 표시 |
| 구형/stale 데이터 | 정보가 오래됐어요 | 최신 정보처럼 사용하지 않음 |
| 지역 미지원 | 이 지역은 혼잡 정보가 없어요 | 다른 지역 값으로 채우지 않음 |

재시도는 서버 `retryable`과 요청의 멱등성을 고려한다. **경로 POST/가입/신청을 무조건 자동 재요청하지 않는다.**

## 8. 서비스 코드 구성 예시

```text
src/lib/api/
  client.ts                  # baseURL, 에러 표준화, AbortSignal
  auth.ts                    # 인증 세션
  schema.d.ts                # OpenAPI 생성 타입
src/features/festivals/
  explore/api.ts             # A02
  detail/api.ts              # A03/A06
  live-info/api.ts           # A07/A09/A10
src/features/routes/return/
  api.ts                     # A04/A05
  pollRoute.ts               # POST/폴링/취소/상태 머신
src/mocks/
  festival.fixture.ts
  crowd.fixture.ts
  returnRoute.fixture.ts
```

### 8.1 공통 fetch 예시(구현 가이드, 런타임 검증 전)

```ts
// 실제 인증 헤더, API 경로, 오류 DTO는 최신 OpenAPI 계약에 맞춰 조정한다.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

type ApiErrorBody = {
  error?: { code?: string; message?: string; request_id?: string; retryable?: boolean };
};

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const error = new Error(body.error?.message ?? `HTTP ${response.status}`);
    Object.assign(error, { status: response.status, code: body.error?.code,
      retryable: body.error?.retryable, requestId: body.error?.request_id });
    throw error;
  }
  return (await response.json()) as T;
}
```

**주의:** 인증 Bearer, 202 상태, 204 No Content, 파일 응답, 요청 취소는 상위 어댑터/클라이언트에서 추가로 처리한다. 위 코드를 그대로 프로덕션 완성본으로 간주하지 않는다.

## 9. 화면별 API 연동 체크리스트

| UI 화면 | 필수 데이터 | 예외 데이터 | API 확인 상태 |
|---|---|---|---|
| 홈 축제 카드 | A02 축제 목록 | 이미지 null, 목록 0건 | v0.3 설계만 확인 |
| 축제 홈/검색 | A02, 정렬/추천 별도 계약 | 결과 없음/404 | 추천 계약 미확인 |
| 축제 상세 | A03 | 프로그램/해시태그/소개/주소 null | v0.3 설계만 확인 |
| 상세 혼잡 | A10 | stale/unsupported/근접지역 0건 | 11/24 UI 요구 확인, JSON 검증 대기 |
| 상세 날씨/공지 | A09/A07 | 출처/발표시각/실패/빈 목록 | 설계만 확인 |
| 귀가 | A04→A05 | queued/processing/timeout/no_result/kakao | v0.3 + 11/24 UI 요구, 코드 값 확인 필요 |
| AI 질문 | A06 | 응답 없음/모의/출처 미확인 | 12/8 시연 모의 가능성 명시 |
| 인증 | A32~A35 | 401/403, 가입 필드 추가 | 성별/출생연도 스키마 확인 필요 |
| 취향 추천 | 계약 미확인 | 취향 미선택/추천 0건 | **BLOCKED** |
| 동행/채팅 | 계약 미확인 | 모집 종료/승인/신고/차단 | **BLOCKED** |

## 10. 연동 검증 절차

1. 백엔드 담당자로부터 **API v0.5 정본 또는 배포 Swagger/OpenAPI** 받기.
2. API별 실제 샘플 3종 확보: **정상 / 빈값·미지원 / 실패**.
3. 응답 필드·nullable·시간·enum을 DTO 타입으로 작성.
4. DTO → UI 모델 Adapter 작성, fixture 테스트.
5. 실제 호출 연결. 인증·CORS·202·토큰 조회·timeout 확인.
6. 사용자 문구·출처·관측 시각·로딩·예외 동작을 화면 캡처로 검증.
7. PR에서 **API 버전, 변경 필드, 스크린샷, 미확인 항목** 기록.
8. Mock과 실제 데이터가 혼재하지 않도록 환경 플래그와 화면 표시를 확인.

### 실제 연동 완료 판정

- [ ] 최신 Swagger와 경로·응답 타입 일치
- [ ] 정상·빈값·null·오류 응답 테스트 통과
- [ ] `route_status` 202→상태 조회→완료/실패 전이 검증
- [ ] TMAP/Kakao 및 서울 혼잡 정보의 실제 출처/시각 표시
- [ ] 사용하지 않는 찜 API 호출 없음
- [ ] API Key/JWT/사용자 민감 정보 콘솔/URL/스크린샷 비노출
- [ ] 팀 QA·백엔드 담당 검토 완료

## 11. 백엔드 담당자에게 보낼 확인 메시지 예시

> 프론트 연동 문서 작성 중입니다. `UI_요청_1124.md`가 참조하는 **API v0.5 정본/Swagger 주소**와 A02·A03·A04·A05·A10 실제 성공·빈값·오류 응답 샘플 공유 부탁드립니다. 특히 `route_preference` 5개 코드, A10 혼잡 4단계/45분 stale 구조, 목록·상세 이미지 null 필드를 확인하고 싶습니다. 회원가입 성별·출생연도, 취향 저장, 동행·채팅 API는 확정 여부도 함께 알려 주세요. 축제 찜하기/하트 기능은 프론트 최신 범위에서 제외했습니다.

---

**업데이트 필수:** 이 문서는 2026-11-19 v0.3 API 설계와 11/24 UI 요청을 조합한 **프론트 연동 초안**이다. 새로운 API 정본/실호출 응답을 확인한 뒤 날짜·버전·변경 내역을 기록하고 사용한다.
