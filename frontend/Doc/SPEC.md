# SPEC — 웹 화면 1차

- 기준: `REQUEST.md`, `DESIGN.md`, 모의 API(`backend/api/MOCK_API.md`, `openapi.json`). **API 설계문서 전체를 읽지 않는다.**
- 실행 환경: Node 26, npm. 명령은 `frontend/`에서.
  - 개발 서버: `npm run dev` → `http://localhost:3000` (모의 API는 `cd backend && uv run --with-requirements api/requirements.txt uvicorn api.main:app --port 8000`)
  - 확인: `npm run typecheck` · `npm run lint` · `npm test`(vitest) · `npm run build` · `npm run e2e`(Playwright, 5단계)
- 모든 요구는 **확인 방법**이 있다. 단위 시험 이름에 요구 번호(`F6 …`)를 넣는다.
- 화면 글은 모두 한국어. 시안의 문구를 그대로 쓰되, 시안 속 **예시 데이터(축제 이름·숫자)는 쓰지 않고 API 값**을 쓴다.

## 0. 공통

### F1. 프로젝트
- Next.js App Router(`src/app/`), TypeScript strict, Tailwind CSS, ESLint. 패키지 버전은 **정확히 고정**하고 `package-lock.json`을 함께 올린다.
- 폴더는 `frontend/README.md` 구조를 따른다: 화면 진입점은 `src/app/…/page.tsx`, 화면 기능은 `src/features/<기능>/`, 공통 요소 `src/components/`, 공통 도구 `src/lib/`.
- 스크립트: `dev`(3000), `build`, `start`, `typecheck`(`tsc --noEmit`), `lint`, `test`(vitest run), `e2e`(playwright), `gen:api`.
- **확인:** `npm run typecheck`·`npm run lint`·`npm test`·`npm run build`가 모두 0으로 끝남.

### F2. 디자인 토큰 (`DESIGN.md` 값)
- Tailwind 테마에 색 이름으로 등록: `bg`, `surface`, `ink`(글자), `muted`, `brand`(분홍 `#F0145F`), `accent`(보라 `#7C36FC`), `neon`(`#C8FF2F`), `dark-bg`(`#0D0D0C`), `dark-surface`(`#1E1D1C`) + 혼잡 색 `crowd-green`·`crowd-yellow`·`crowd-orange`·`crowd-red`.
- 글꼴: Pretendard(본문), Outfit(로고·숫자). 모서리 토큰 `card`(18px)·`input`(25px)·`chip`(완전 둥글게).
- 화면 코드에 색 값(`#…`)을 직접 쓰지 않는다(토큰만).
- **확인:** `src/` 아래 `.tsx` 파일에 `#[0-9A-Fa-f]{6}` 문자열이 없음(시험 `F2 no raw colors`).

### F3. 공통 틀
- 본문 최대 폭 480px 가운데 정렬, 아래 탭 고정: **홈 `/`·축제 `/festivals`·동행 `/companions`·귀가 `/routes/return`·지도 `/map`**. 현재 탭 강조(분홍 배경).
- `/companions`, `/map`은 "준비 중이에요" 화면(2차).
- 홈(`/`)만 다크 테마, 나머지 라이트.
- 상단 헤더: 로고(NOLDAGA, 분홍 N) + 로그인 상태면 닉네임 첫 글자, 아니면 로그인 아이콘 → `/auth/login`.
- **확인:** 흐름 시험에서 탭 5개 이동 · 홈 배경이 다크 토큰.

### F4. API 연결 (`src/lib/api/`)
- `client.ts`: 기본 주소 `process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1"`. 요청마다 `X-Request-ID: req_` + 영숫자 26자. JSON 응답을 돌려주고, 오류면 `ApiError{status, code, message, requestId, retryable}`를 던진다(본문 `error` 형식 읽기). 네트워크 실패는 `code:"NETWORK_ERROR"`, 메시지 "서버에 연결할 수 없어요".
- 타입: `npm run gen:api`가 `frontend/Doc/openapi.json`(모의 서버 `/openapi.json` 사본)으로 `src/lib/api/schema.d.ts`를 만든다(openapi-typescript). 화면 코드는 이 타입을 쓴다.
- 로그인 토큰이 있으면 `Authorization: Bearer` 자동 추가.
- **확인(단위):** 성공 200 → 본문 반환 · 422 오류 본문 → `ApiError.code=="VALIDATION_ERROR"`·`message` 그대로 · fetch 실패 → `NETWORK_ERROR` · 헤더 `X-Request-ID`가 `^req_[0-9A-Za-z]{26}$`.

### F5. 모의 데이터 표시
- 응답의 `is_mock === true`를 한 번이라도 받으면 화면 오른쪽 아래에 작은 "모의 데이터" 표시.
- **확인:** 흐름 시험에서 축제 목록 화면에 "모의 데이터" 글자가 보임.

### F11. 카카오 지도 (`src/lib/kakao.ts`, `src/components/KakaoMap.tsx`)
- SDK를 한 번만 불러옴(`//dapi.kakao.com/v2/maps/sdk.js?appkey=…&autoload=false`). 키는 `NEXT_PUBLIC_KAKAO_JS_KEY`.
- `KakaoMap` props: `center{lat,lng}`, `markers[]`, `polylines[]`(`[[lat,lng],…]`). 키가 없거나 불러오기 실패면 같은 크기의 회색 상자에 "지도를 불러올 수 없어요(지도 키 확인)".
- **확인(단위):** 키가 빈 값이면 대체 문구가 보임.

## 1. 축제

### F6. 축제 목록 `/festivals` (A02)
- 위: 검색창(`q`), 지역 선택(0-1 지역 코드 → 한국어 이름: 전체·서울·부산·…·제주), 상태 칩(전체·진행 중 `ongoing`·예정 `upcoming`·종료 `ended`).
- 카드: 대표 이미지(`thumbnail_url`, 없으면 기본 그림, **잘리지 않게 `object-contain`**), 이름, 기간, 장소, **D-day 배지**(시작 전 `D-n`, 진행 중 `진행 중`, 종료 `종료`), 이미지 있으면 "출처: 한국관광공사".
- 20개씩, 더 있으면 "더 보기". 결과 0개면 "조건에 맞는 축제가 없어요".
- `dday(start, end, today)` 순수 함수로 분리.
- **확인(단위):** `dday("2026-12-05","2026-12-07","2026-11-22")=="D-13"` · 기간 안이면 "진행 중" · 끝나면 "종료" · 날짜 없으면 빈 값. **(흐름)** 서울 선택 → 카드 2개.

### F7. 축제 상세 `/festivals/[festivalId]` (A03·A07·A09·A10·A12·A13)
- 위: 큰 이미지(`object-contain`) + 하트, 이름, 한 줄 소개(`overview`), AI 질문창(홈과 같은 동작, 3단계 F9 재사용).
- 정보 칩: 기간, 장소(`venue_name`), 입장료(`fee_text`), 지역.
- **현장 정보** 3칸 — 각자 따로 불러오고 하나가 실패해도 나머지는 보임:
  - 혼잡(A10): `ok` → 구역 이름 + 색 칩(`congest_color` 토큰) + 인구 범위 / `unsupported` → "이 지역은 아직 지원하지 않아요" / `unavailable` → 오류 문구 / `stale` → 값 + "정보가 오래됐어요"
  - 날씨(A09): 기온 + 강수 형태 한국어(`none`→맑음/흐림 없이 "강수 없음", `rain`→비, `snow`→눈 …)
  - 공지(A07): 목록(제목·효력 기간), 0개면 "확인할 수 있는 공지 자료가 없어요"
- 작은 지도(F11, 축제 좌표 마커). 좌표 없으면 "위치 정보가 없어요".
- 주변 정보 아이콘 줄(화장실·주차장·맛집·병원·지하철·버스): 눌러도 "준비 중이에요"(A08 없음).
- **AI 안심 귀가 배너** → `/routes/return?festivalId=<id>`.
- 하트: 로그인 안 했으면 `/auth/login?next=…`로, 했으면 A12/A13(201·200·204 모두 성공 처리).
- 없는 축제(404) → "축제를 찾을 수 없어요" + 목록으로.
- **확인(흐름):** `fst_000001` 상세에 혼잡 "보통", 날씨 기온, 공지 2개 · `fst_000003`(부산) 혼잡 "아직 지원하지 않아요" · `fst_999999` → 찾을 수 없음.

## 2. 귀가

### F8. AI 안심 귀가 `/routes/return` (A04·A05)
- 입력: 축제(쿼리 `festivalId`로 미리 채움, 없으면 축제 검색 선택), **출발**(기본 "축제 장소", "직접 입력"으로 바꾸면 장소 입력), **도착**(필수, 장소 입력), 추천 기준 칩(가장 빠른 길 `fastest`·도보 최소 `min_walk`·환승 최소 `fewest_transfers`·혼잡 회피 `less_crowded`).
- "경로 찾기" → `request_id = crypto.randomUUID()`로 A04.
  - 202 → `route_access_token` 보관 → `retry_after_s`(2초)마다 A05 조회, **최대 5번**. 5번 뒤에도 끝나지 않으면 "지금은 확인할 수 없어요" + "다시 시도"
  - 200(`sync_ready`) → 바로 결과
  - 조회 반복은 화면을 떠나면 멈춘다
- 상태 화면: 처리 중(로딩 + "경로를 찾고 있어요. 아직 확정된 경로가 아니에요") · `ready` → 경로 카드(소요 분, 도보, 환승, 구간 칩, `completed_valid_route`면 "추천") + 지도에 경로선(`legs[].path`, **[위도, 경도]**)·출발/도착 마커 · `unavailable`/`timed_out` → `error.message` + `notices` + "다시 시도"(새 `request_id`) · 503 `ROUTE_OVERLOADED` → "요청이 많아요. 잠시 뒤 다시 시도해 주세요" · 400/404/422 → 해당 메시지, 입력 유지.
- `notices`는 항상 카드 아래 작은 글씨로("공식 교통통제 반영 여부를 확인하지 못했어요").
- 개발용: `NEXT_PUBLIC_SHOW_MOCK_TOOLS=1`일 때만 화면 아래 "시나리오" 선택(`X-Mock-Scenario`: 기본·sync_ready·async_unavailable·async_timeout·overloaded).
- 조회 반복 로직은 `pollRoute()`로 분리.
- 결과 화면 직접 열기: `/routes/return?id=<rr_…>&token=<rrt_…>`(홈 AI 질문 연결용) → 바로 조회부터.
- **확인(단위, 가짜 타이머):** 1번째 `processing`·2번째 `ready`면 2번 부르고 멈춤 · 5번 모두 `processing`이면 "확인 불가" 상태 · 중단 신호(AbortSignal)면 더 부르지 않음. **(흐름)** `fst_000001` + 도착 "서울역" → 결과 카드 38분 · 시나리오 `async_timeout` → 시간 초과 문구.

## 3. 홈·계정

### F9. 홈 `/` (다크, A06·A02)
- 시안 `84-286` 배치: 큰 제목 "오늘, 어디서 놀까?", **AI 질문창**, **AI 안심 귀가 카드**(→ `/routes/return`), "내 취향 축제 추천"(→ "준비 중"), "동행 찾기"(→ `/companions`), **지금 주목할 축제** 가로 카드 3개(A02 `status=ongoing` 앞 3개 — 추천 API 전까지 임시, 코드 주석), "전국 축제 둘러보기"(→ `/festivals`).
- AI 질문창: `POST /assistant/query` → `run_access_token` → `GET /assistant/runs/{run_id}` 1초마다 최대 10번. `running` 동안 "생각 중…", `succeeded` → 답변 말풍선, `route_request_id`·`route_access_token`이 있으면 "귀가 경로 보기" 버튼(→ F8 결과 화면 직접 열기), `failed` → `error.message` + "다시 묻기"(새 `request_id`).
- **확인(흐름):** "서울역으로 귀가하는 길 알려줘" → 답변 → "귀가 경로 보기" → 결과 카드.

### F10. 로그인·회원가입 (A32~A35)
- `/auth/login`(시안 `84-363`): 이메일·비밀번호, "로그인", "회원가입" 버튼. 실패 401 → "이메일 또는 비밀번호가 맞지 않아요". 성공 → `next` 쿼리 주소 또는 홈.
- `/auth/signup`(시안 `84-287`): 이메일, 비밀번호(8~64자 영문+숫자), 닉네임(2~12자), 출생연도(1900~올해 선택), 성별(남/여). 화면에서 먼저 같은 규칙으로 검사. 409 `EMAIL_ALREADY_EXISTS`→"이미 가입한 이메일이에요", `NICKNAME_TAKEN`→"이미 쓰는 닉네임이에요". 성공 → 로그인 화면(이메일 채움).
- 토큰: access는 메모리 + `sessionStorage`(모의 단계), refresh는 `sessionStorage`. 401을 받으면 A34로 1번 갱신 후 다시 시도, 실패하면 로그아웃 처리. 로그아웃 A35.
- 비밀번호·토큰을 `console`에 찍지 않는다.
- 검사 규칙은 `validators.ts`로 분리.
- **확인(단위):** 닉네임 1자·13자 거부, 공백만 거부 · 비밀번호 숫자만 거부 · 출생연도 범위. **(흐름)** 가입 → 로그인 → 축제 하트 → 다시 들어가도 하트 유지.

## 4. 시험·문서

### F12. 흐름 시험 (Playwright, 5단계)
- 모의 서버(8000)와 개발 서버(3000)를 띄우는 설정(`webServer`)을 Playwright 설정에 넣는다. 크롬만, 화면 402×874.
- F6·F7·F8·F9·F10의 **(흐름)** 확인을 시험으로 만든다. 단계마다 화면 캡처를 `frontend/e2e-screenshots/`(저장소 제외)에 남긴다.

### F13. 문서·환경
- `frontend/.env.local.example`(키 칸은 빈 값), `.gitignore`에 `.env.local`·`e2e-screenshots/`·`.next/`·`node_modules/`.
- `frontend/README.md`의 "실행 명령" 절에 실행·시험 명령과 모의 서버 함께 띄우는 법을 추가(기존 표는 유지).
- **확인:** `git status`에 `.env.local`이 나오지 않음.
