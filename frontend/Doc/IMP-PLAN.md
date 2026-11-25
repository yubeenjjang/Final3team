# IMP-PLAN — 웹 화면 1차

> 2026-11-25 최신 변경: 브랜드색 `#F74F85`, 축제 이미지 `1:1.414`, 390px 카드 3.5개, 축제 찜·좋아요 기능 포함. 상세 작업 기준은 `FRONTEND-IMP-PLAN.md`를 우선한다.

단계마다 **만들 파일 범위 안에서만** 만들고, 확인 → 체크 → (Claude가) commit. 한 단계가 끝나기 전에 다음 단계로 가지 않는다.
구현 도구·모델은 실행 전에 사용자에게 알리고 정한다(아래 '도구' 칸은 제안).

| 단계 | 요구 | 도구(제안) | 시작 조건 |
|---|---|---|---|
| 1 뼈대 | F1·F2·F3·F4·F5·F11·F13 | agy | 없음 |
| 2 축제 | F6·F7 | agy | 1단계 확인 통과 |
| 3 귀가 | F8 | **Codex gpt-6.2-sol high** (11/22 전환) | 2단계 통과 |
| 4 홈·계정 | F9·F10 | Codex | 3단계 통과 |
| 5 흐름 시험·캡처 | F12 | Codex | 4단계 통과 |
| 6 검토 | 전체 | Claude 확인 + Codex 읽기 전용 검토(시안 PNG ↔ 캡처 비교 포함) | 5단계 통과 |

## 공통 확인 명령 (`frontend/`)
`npm run typecheck && npm run lint && npm test && npm run build`

## 1단계 — 뼈대
**만들 파일:** `frontend/` 아래 Next.js 기본 파일(`package.json`·`package-lock.json`·`tsconfig.json`·`next.config.*`·`postcss.config.*`·`tailwind` 설정·`eslint` 설정·`vitest.config.*`), `src/app/layout.tsx`·`page.tsx`(임시)·`globals.css`·`companions/page.tsx`·`map/page.tsx`, `src/components/`(아래 탭·헤더·모의 표시·KakaoMap·준비 중), `src/lib/api/`(client·schema.d.ts·auth 토큰 저장), `src/lib/kakao.ts`, 단위 시험 `src/**/*.test.ts(x)`, `.env.local.example`, `.gitignore`, `README.md`(실행 절 추가만)
- [x] F1 프로젝트·스크립트
- [x] F2 최신 토큰 `#F74F85`(색 직접 쓰기 금지 시험 포함)
- [x] F3 틀·탭
- [x] F4 API 연결·타입 생성
- [x] F5 모의 표시
- [x] F11 카카오 지도 + 대체 화면
- [x] F13 환경·문서
- [x] 공통 확인 명령 통과

## 2단계 — 축제
**만들 파일:** `src/app/festivals/page.tsx`, `src/app/festivals/[festivalId]/page.tsx`, `src/features/festivals/explore/`, `detail/`, `live-info/`, 관련 시험
- 추가 허용: `next.config.ts`에 개발 도구 표시 위치만 바꾸기(`devIndicators: { position: 'top-right' }` 등 — 아래 탭의 홈 버튼을 가림, 1단계 확인 때 발견)
- [x] F6 목록·필터·D-day
- [x] F7 상세·현장 정보·1:1.414 포스터·지도·배너·축제 찜
- [x] 공통 확인 명령 통과

## 3단계 — 귀가
**만들 파일:** `src/app/routes/return/page.tsx`, `src/features/routes/return/`, 관련 시험
- [x] F8 입력·접수·조회 반복·결과/실패·지도 경로선·시나리오 도구
- [x] 공통 확인 명령 통과

## 4단계 — 홈·계정
**만들 파일:** `src/app/page.tsx`(임시를 홈으로), `src/app/auth/login/page.tsx`, `src/app/auth/signup/page.tsx`, `src/features/assistant/chatbot/`, `src/features/accounts/auth/`, `src/features/favorites/`, 관련 시험.
- [x] F9 홈·AI 질문창 → 귀가 연결
- [x] F10 로그인·회원가입·토큰 갱신·로그아웃
- [x] 공통 확인 명령 통과

## 5단계 — 흐름 시험
**만들 파일:** `playwright.config.*`, `e2e/*.spec.ts`
- [x] F12 흐름 시험 전부 통과 + 화면 캡처

## 6단계 — 검토 (Claude)
- [x] 모의 서버 + 개발 서버 띄워 직접 확인
- [x] 시안 PNG와 캡처 비교 검토 + Codex 검토(16개) → FIX6로 수정, e2e 8/8 재통과
- [ ] commit, push(사용자 지시 때), 팀 안내 문구

## 메모
- 5단계: e2e는 Ubuntu 26.04에서 Playwright 브라우저 미지원 → `docker run --rm --network host -u $(id -u):$(id -g) -e HOME=/tmp -v "$PWD":/w -w /w mcr.microsoft.com/playwright:v1.57.0-noble npx playwright test`로 실행(서버 2개는 먼저 띄움). 11/22 8개 통과.
- 3단계 검토 메모(6단계에서 처리): 시간 초과 등 실패 카드에서 제목과 본문이 같은 문구로 두 번 보임 · 결과 지도에 출발/도착 이름표(시안의 '출발'·'도착' 말풍선) 없음 · Codex 샌드박스에서는 Turbopack 포트 제한으로 `npm run build`가 실패하지만 Claude 환경에서는 통과(11/22).
- 시안이 이미지 한 장뿐이라 색은 근사값(`DESIGN.md`). 이수언 님이 값을 주면 토큰만 바꾼다.
- 테마·아래 탭이 화면마다 다른 것은 `DESIGN.md` 2절의 기본안으로 구현.
