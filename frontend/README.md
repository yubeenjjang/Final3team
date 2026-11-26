# Frontend

놀다가의 사용자 화면과 관리자 화면을 만드는 폴더입니다.

| 폴더 | 역할 |
| --- | --- |
| `public/` | 로고, 이미지, 아이콘 등 정적 파일 |
| `src/app/` | 화면 주소와 각 화면의 진입점 |
| `src/features/festivals/` | 축제 지도·검색·상세·현장 정보·추천 |
| `src/features/routes/` | 축제 가는 길, 귀가 경로, 조회 상태 |
| `src/features/accounts/` | 회원가입·로그인, 프로필, 관심 축제 |
| `src/features/community/` | 동행, 친구, 사용자 간 채팅, 앱 내 알림 |
| `src/features/assistant/` | AI 챗봇과 방문 코스 화면 |
| `src/features/admin/` | 축제 데이터 관리와 장애·복구 시연 화면 |
| `src/components/` | 여러 기능에서 함께 쓰는 화면 요소 |
| `src/lib/` | 공통 API 요청과 실시간 연결 등 공통 도구 |

`app/`은 화면의 위치를 정하고, 실제 화면 기능은 `features/`에 작성합니다.
프론트 코드는 Next.js(App Router), TypeScript, Tailwind CSS로 작성합니다.

## 실행 명령

모든 프론트엔드 명령은 `frontend/` 폴더에서 실행합니다(Node 26, npm 기준).

### 1. 환경변수 준비

`.env.local.example`을 참고해 필요 시 `.env.local`을 만듭니다(`.env.local`은 git에 올라가지 않습니다).

- `NEXT_PUBLIC_API_BASE`: 기본값 `http://localhost:8000/api/v1`
- `NEXT_PUBLIC_KAKAO_JS_KEY`: 카카오 지도 JavaScript 키(비워 두면 지도 자리에 안내 문구 표시)
- `NEXT_PUBLIC_SHOW_MOCK_TOOLS`: `1`이면 개발용 모의 시나리오 도구 표시
- `NEXT_PUBLIC_USE_MOCK_FESTIVALS`: `1`이면 개발 서버에서 디자인 확인용 로컬 축제 데이터 사용

### 2. 모의 API 서버와 개발 서버 함께 띄우기

터미널 1 — 모의 API 서버(`backend/` 폴더):

```sh
cd backend
uv run --with-requirements api/requirements.txt uvicorn api.main:app --port 8000
```

터미널 2 — 프론트 개발 서버(`frontend/` 폴더):

```sh
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`으로 접속합니다.

### 시연용 프로덕션 서버

개발 서버의 중복 렌더링과 파일 재컴파일 영향을 피하려면 백엔드가 준비된 뒤 프론트엔드를
프로덕션 모드로 실행합니다. 먼저 `http://localhost:8000/api/v1/health`가 200인지 확인한 후
다음 명령을 실행하세요.

```sh
cd frontend
npm run demo
```

귀가 화면의 모의 시나리오 선택기는 `NEXT_PUBLIC_SHOW_MOCK_TOOLS=1`일 때만 표시됩니다.
일반 시연에서는 `.env.local` 값을 `0`으로 유지하세요.

### 3. API 타입 생성·확인·빌드 명령

```sh
npm run gen:api      # Doc/openapi.json → src/lib/api/schema.d.ts 생성
npm run typecheck    # TypeScript 타입 검사 (tsc --noEmit)
npm run lint         # ESLint 검사
npm test             # 단위 시험 (vitest run)
npm run build        # 프로덕션 빌드
npm run e2e          # 흐름 시험 (Playwright)
```

공통 확인 한 줄 명령:

```sh
npm run typecheck && npm run lint && npm test && npm run build
```
