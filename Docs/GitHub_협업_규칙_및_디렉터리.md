# 놀다가 디렉터리 및 GitHub 협업 규칙

프론트엔드는 기획서의 React/Next.js 기준이며 코드 언어와 파일 확장자는 아직 정하지 않았습니다. Docker 파일은 추후 추가합니다. 사람별 실제 코드 작업은 아래 작업 공간을 기준으로 합니다.

## 1. 개인 브랜치에서 작업

1. 팀원마다 개인 브랜치 하나를 사용한다. 예: `yubeen`, `yejin`, `sueon`.
2. 각자 맡은 작업을 자기 브랜치에 commit·push한다. 일반 작업은 `main`에 직접 올리지 않는다.
3. 신유빈이 `main` 병합 완료를 알리면, 팀원은 진행 중인 변경을 먼저 커밋하고 최신 `main`을 자기 브랜치에 반영한다.
4. 커밋 메시지는 `[feat]`, `[fix]`, `[docs]`처럼 간단한 말머리와 작업 내용을 적는다.

## 2. 사람별 주 작업 공간

| 팀원 | 담당 영역 |
|---|---|
| 정예진 | 프론트 계정·추천·커뮤니티·공통 파일 |
| 이수언 | 프론트 축제·경로·AI·운영 화면 |
| 권오현 | 백엔드 주요 API·실시간 연결 |
| 한다영 | Agent·RAG·축제 원본 수집 |
| 신유빈 | 인프라 구축·시설/운영 API·내부 복구 |
| 한태경 | 통합·부하·장애 시험·인프라 기동 검증 |

### 상세 폴더 경로

#### 정예진

- `frontend/src/features/accounts/`
- `frontend/src/features/festivals/recommendations/`
- `frontend/src/features/community/`
- `frontend/src/features/admin/festival-management/`
- 위 기능에 해당하는 `frontend/src/app/` 화면
- `frontend/src/components/`, `frontend/src/lib/` 공통 파일 취합

#### 이수언

- `frontend/src/features/festivals/explore/`, `detail/`, `live-info/`
- `frontend/src/features/routes/`, `assistant/`, `admin/operations/`
- 위 기능에 해당하는 `frontend/src/app/` 화면

#### 권오현

- `backend/api/routers/festivals/catalog.py`, `info.py`
- `backend/api/routers/routes/`, `accounts/`, `community/`, `assistant/`
- `backend/api/routers/admin/festival_review.py`
- `backend/api/providers/tmap.py`, `kakao.py`
- `backend/api/realtime/chat_socket.py`, `job_events.py`

#### 한다영

- `backend/agents/`
- `backend/api/providers/tourapi.py`
- `backend/api/ingestion/` 중 축제 원본 수집 코드

#### 신유빈

- `backend/api/routers/festivals/recommendations.py`, `facilities.py`, `data_sources.py`
- `backend/api/routers/admin/operations.py`, `ingestion.py`
- `backend/api/healing/`, `backend/shared/`
- `infra/` 주 담당

#### 한태경

- `backend/tests/integration/`, `load/`, `realtime/`, `healing/`
- `infra/` 설정·기동·검증 지원

`backend/api/schemas/`, `backend/api/services/`, `backend/api/repositories/`에서는 각자 맡은 router 기능에 해당하는 파일을 함께 담당한다. 프론트도 자신이 맡은 `features/` 기능에 대응하는 `app/` 화면을 담당한다.


## 3. 함께 쓰는 파일

- 프론트 공통 레이아웃·컴포넌트·API 연결 파일은 **정예진**이 취합한다.
- `backend/api/main.py`는 **권오현**, `backend/shared/`의 공통 설정·DB 연결은 **신유빈**, `backend/agents/graph.py`·`state.py`는 **한다영**이 취합한다.
- `backend/api/realtime/chat_socket.py`는 **권오현**이 채팅 WebSocket을 구현한다. `backend/api/realtime/job_events.py`는 **권오현**이 API의 진행 이벤트 중계를 맡고, **한다영**이 `backend/agents/events.py`의 이벤트 발행을 맡는다. Redis 연결·공통 설정 변경은 **신유빈**이 취합한다.
- `infra/`는 **신유빈이 주로 취합하고 한태경이 설정·기동·검증을 지원**한다.
- 다른 사람의 담당 파일을 수정해야 하면 먼저 담당자에게 알린다. 공통 파일의 구조·이름·사용 방법을 바꿀 때도 영향을 받는 팀원에게 미리 알린다.
- API 요청·응답 형식을 바꾸면 API 설계문서도 함께 수정한다.

## 4. 병합 요청

1. 개인 브랜치에는 작업 중인 코드도 올릴 수 있다.
2. `main`에 합칠 기능이 완성되면 팀 채널에 **`[병합 요청] 브랜치명 / 작업 내용 / 실행 확인 결과`**를 남긴다.
3. **`main` 병합은 신유빈이 진행한다. 신유빈의 작업도 병합 요청과 실행 확인 내용을 동일하게 기록한다.**
4. 같은 브랜치에 **미완성 작업이 섞여 있으면 반드시 알린다.** 신유빈과 병합 범위를 확인하기 전에는 브랜치 전체를 병합하지 않는다.
5. 병합 중 충돌이 나면 신유빈이 임의로 코드를 지우지 않고 해당 작업 담당자와 함께 해결한다.

## 5. 병합 후 확인

- 신유빈과 작업 담당자가 합쳐진 `main`에서 변경 기능이 실행되는지 확인한다.
- `main`에서 오류가 발견되면 팀 채널에 바로 알린다. 수정에 시간이 오래 걸리면 해당 병합을 되돌리고 개인 브랜치에서 고친 뒤 다시 병합을 요청한다.

## 6. 패키지·설정·DB 변경

- 백엔드 패키지를 추가·변경하면 해당 `requirements.txt`도 함께 올린다.
- 프론트 패키지를 추가·변경하면 `frontend/package.json`과 사용 중인 잠금 파일(예: `package-lock.json`)도 함께 올린다.
- 환경변수가 필요하면 `.env.example`에 **이름만** 추가하고 팀에 알린다. 실제 값은 GitHub나 공개 채팅에 올리지 않는다.
- DB 테이블·컬럼을 바꾸면 `backend/shared/db/migrations/`의 변경 파일을 함께 올리고 적용 방법을 알린다.

## 7. GitHub에 올리지 않을 것

`.env`, API 키, 비밀번호, `node_modules/`, `.venv/`, `__pycache__/`, 임시 로그와 실제 사용자 데이터는 올리지 않는다. 외부 API 증빙에서는 키를 가리고, 저장이 제한된 카카오 경로 본문은 증빙 파일에도 넣지 않는다.

## 전체 디렉터리 구조

```text
Final3team/
├─ .gitignore                         # 로컬 설정·생성 파일 제외
├─ .env.example                       # 환경변수 이름 예시
├─ Docs/                              # 기획·설계 문서
├─ frontend/                          # React/Next.js 웹 화면: 정예진·이수언
│  ├─ public/                         # 로고·이미지·아이콘
│  ├─ src/
│  │  ├─ app/                        # Next.js 화면 경로
│  │  │  ├─ festivals/               # 축제 지도·검색·목록 화면
│  │  │  │  └─ [festivalId]/          # 선택한 축제의 상세·현장 정보 화면
│  │  │  ├─ routes/                  # 길찾기 화면
│  │  │  │  ├─ visit/                 # 축제 가는 길 화면
│  │  │  │  └─ return/                # 축제에서 귀가하는 길 화면
│  │  │  ├─ assistant/                # AI 챗봇·방문 코스 화면
│  │  │  ├─ recommendations/          # 맞춤 추천·인기·둘러보기 화면
│  │  │  ├─ onboarding/               # 첫 로그인 후 축제 취향 선택 화면
│  │  │  ├─ auth/                     # 회원가입·로그인 화면
│  │  │  ├─ favorites/                # 내가 저장한 관심 축제 화면
│  │  │  ├─ companions/               # 축제 동행 모집·신청 화면
│  │  │  ├─ friends/                  # 친구 신청·목록 화면
│  │  │  ├─ chats/                    # 사용자 간 채팅방 목록 화면
│  │  │  │  └─ [roomId]/              # 선택한 채팅방 화면
│  │  │  ├─ notifications/            # 앱 내 알림 화면
│  │  │  ├─ me/                       # 내 프로필·마이페이지 화면
│  │  │  └─ admin/                    # 관리자 화면
│  │  │     ├─ operations/            # 장애·부하·복구 시연 화면
│  │  │     └─ festival-management/   # 축제 수집·중복 검토 화면
│  │  ├─ features/                   # 기능별 화면 구성·상태·API 호출
│  │  │  ├─ festivals/               # 축제 관련 기능
│  │  │  │  ├─ explore/              # 축제 지도·검색·목록
│  │  │  │  ├─ detail/               # 축제 상세
│  │  │  │  ├─ live-info/            # 현장 공지·시설·날씨·교통
│  │  │  │  └─ recommendations/      # 축제 취향·추천·인기·둘러보기
│  │  │  ├─ routes/                  # 길찾기 관련 기능
│  │  │  │  ├─ visit/                # 축제 가는 길
│  │  │  │  └─ return/               # 축제에서 귀가하는 길·조회 상태
│  │  │  ├─ accounts/                # 내 계정 관련 기능
│  │  │  │  ├─ auth/                 # 회원가입·로그인
│  │  │  │  ├─ profile/              # 내 프로필·마이페이지
│  │  │  │  └─ favorites/            # 내가 저장한 관심 축제
│  │  │  ├─ community/               # 사용자 간 관계·대화 기능
│  │  │  │  ├─ companions/           # 동행 모집·신청·만남 장소
│  │  │  │  ├─ friends/              # 친구 신청·목록
│  │  │  │  ├─ chats/                # 사용자 간 채팅
│  │  │  │  └─ notifications/        # 앱 내 알림
│  │  │  ├─ assistant/               # AI 기능
│  │  │  │  ├─ chatbot/              # AI 챗봇
│  │  │  │  └─ visit-course/         # AI 방문 코스
│  │  │  └─ admin/                   # 관리자 기능
│  │  │     ├─ operations/           # 사건·부하·복구 시연
│  │  │     └─ festival-management/  # 축제 수집·중복 검토
│  │  ├─ components/                 # 공통 UI
│  │  └─ lib/                        # 공통 API 요청·Job 이벤트·채팅 소켓·지도 로더
│  ├─ package.json                   # 실행 명령·패키지
│  └─ README.md                      # 프론트 로컬 실행 안내
├─ infra/                             # 신유빈 주 담당, 한태경 부담당
│  ├─ database/                       # PostgreSQL·pgvector 환경
│  ├─ redis/                          # Redis 환경
│  ├─ deployment/                     # 배포 환경·절차
│  └─ README.md                       # 실행·배포 안내
└─ backend/
   ├─ api/                            # FastAPI 서버
   │  ├─ main.py                      # 앱 시작·라우터 등록
   │  ├─ deps.py                      # 사용자·운영자 인증
   │  ├─ celery_client.py             # Agent 작업 요청
   │  ├─ routers/
   │  │  ├─ festivals/
   │  │  │  ├─ catalog.py            # 축제 목록·상세
   │  │  │  ├─ info.py               # 공지·날씨·혼잡·교통 정보
   │  │  │  ├─ facilities.py         # 주변 시설
   │  │  │  ├─ recommendations.py    # 취향·추천·인기·둘러보기·최신
   │  │  │  └─ data_sources.py       # 공급원·지원 지역 조회
   │  │  ├─ routes/
   │  │  │  └─ routes.py             # 귀가·방문 경로
   │  │  ├─ accounts/
   │  │  │  ├─ auth.py               # 가입·로그인·토큰
   │  │  │  ├─ users.py              # 마이페이지·프로필·신고·차단
   │  │  │  └─ favorites.py          # 관심 축제
   │  │  ├─ community/
   │  │  │  ├─ companions.py         # 동행 모집·신청·만남 장소
   │  │  │  ├─ friends.py            # 친구 검색·신청·수락·차단
   │  │  │  ├─ chat.py               # 사용자 간 채팅
   │  │  │  └─ notifications.py      # 앱 내 알림·읽음 처리
   │  │  ├─ assistant/
   │  │  │  ├─ chatbot.py            # AI 챗봇
   │  │  │  └─ agent_jobs.py         # Agent 작업 상태 조회
   │  │  ├─ admin/
   │  │  │  ├─ operations.py         # 사건·지표·복구·부하 시험
   │  │  │  ├─ ingestion.py          # 수집 작업 이력
   │  │  │  └─ festival_review.py    # 축제 중복 검토·승인
   │  │  └─ health.py                 # 서버 상태
   │  ├─ realtime/
   │  │  ├─ chat_socket.py            # 채팅 WebSocket 연결
   │  │  └─ job_events.py             # Agent 작업 진행 SSE 중계
   │  ├─ schemas/                     # routers와 같은 기능군·파일명으로 요청·응답 모델
   │  ├─ services/                    # routers와 같은 기능군·파일명으로 처리 로직
   │  ├─ repositories/                # routers와 같은 기능군·파일명으로 DB 접근
   │  ├─ providers/
   │  │  ├─ route_base.py            # 경로 공급원 공통 입력·출력 형식
   │  │  ├─ mock_route.py            # 내부 부하 시험용 모의 경로 공급원
   │  │  ├─ tourapi.py                # 축제 원본 공급원
   │  │  ├─ tmap.py                   # 1차 경로 공급원
   │  │  ├─ kakao.py                  # 2차 경로·장소 공급원
   │  │  └─ seoul_citydata.py         # 서울 지역 데이터 공급원
   │  ├─ ingestion/                   # 축제 수집·정규화·적재
   │  ├─ healing/
   │  │  ├─ metrics.py                # 내부 경로 처리 지표
   │  │  ├─ policy.py                 # 허용 복구 조치 검사
   │  │  ├─ executor.py               # 복구 조치 실행·원복
   │  │  └─ validation.py             # 조치 후 효과 재검증
   │  └─ requirements.txt             # API용 Python 패키지
   ├─ agents/                         # LangGraph·Celery worker
   │  ├─ roles/
   │  │  ├─ supervisor.py            # Supervisor Agent
   │  │  ├─ festival.py              # Festival Agent
   │  │  ├─ route.py                 # Route Agent
   │  │  ├─ diagnosis.py             # Diagnosis Agent
   │  │  └─ recovery.py              # Recovery Agent
   │  ├─ graph.py                     # Agent 연결 흐름
   │  ├─ state.py                     # Agent 공통 상태
   │  ├─ celery_app.py                # Celery 설정
   │  ├─ tasks.py                     # Agent 작업 함수
   │  ├─ events.py                    # 진행 이벤트 발행
   │  ├─ tools/                       # Agent가 사용하는 도구
   │  ├─ integrations/               # LLM·내부 API 호출
   │  ├─ healing/
   │  │  ├─ retry_policy.py          # Agent의 LLM·도구 호출 재시도/폴백
   │  │  └─ worker_health.py         # Agent worker 상태 점검
   │  ├─ rag/                         # 공식 안내문 색인·검색
   │  ├─ prompts/                     # Agent별 프롬프트
   │  └─ requirements.txt             # Agent용 Python 패키지
   ├─ shared/                         # API·Agent 공통 코드
   │  ├─ config.py                    # 공통 환경변수 설정
   │  ├─ redis.py                     # Redis 연결
   │  ├─ contracts/
   │  │  ├─ agent_jobs.py            # Agent 작업 데이터 형식
   │  │  ├─ identifiers.py           # 공통 식별자 형식
   │  │  ├─ recovery_actions.py      # 허용 복구 조치 형식
   │  │  └─ route_results.py         # 저장 가능한 경로 데이터 형식
   │  └─ db/
   │     ├─ connection.py            # PostgreSQL 연결
   │     ├─ job_store.py             # Agent 작업 상태 저장
   │     ├─ models/                  # 도메인별 DB 모델
   │     │  ├─ auth.py               # 회원·인증
   │     │  ├─ festival.py           # 축제·관심·추천
   │     │  ├─ ingestion.py          # 수집 작업·검토 대기열
   │     │  ├─ route.py              # 경로 요청·허용된 결과
   │     │  ├─ agent_job.py          # Agent 작업 상태
   │     │  ├─ incident.py           # 장애 사건·복구 이력
   │     │  └─ community.py          # 동행·친구·채팅·알림
   │     └─ migrations/              # DB 구조 변경 파일
   ├─ tests/
   │  ├─ api/                        # API 테스트
   │  ├─ agents/                     # Agent·Celery 테스트
   │  ├─ realtime/                   # 채팅·진행 이벤트 테스트
   │  ├─ healing/                    # 복구 테스트
   │  ├─ integration/                # 통합 테스트
   │  └─ load/                       # 내부 부하 시험
   └─ README.md                      # Docker 없는 API·Celery 로컬 실행 안내
```
