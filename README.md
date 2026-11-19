# 놀다가 (NOLDAGA)

전국 축제 탐색과 AI 안심 귀가 서비스를 개발하는 저장소입니다. 확정된 기획서와 WBS는 `Docs/Step 1/`에 있습니다.

## 디렉터리

| 경로 | 용도 |
| --- | --- |
| `frontend/app/` | Next.js 페이지와 라우트 |
| `frontend/components/` | 공통 UI 컴포넌트 |
| `frontend/lib/` | API 호출 및 프론트 공통 코드 |
| `frontend/public/` | 공개 정적 파일 |
| `backend/app/api/` | FastAPI `/api/v1` 엔드포인트 |
| `backend/app/core/` | 설정, 인증, 공통 정책 |
| `backend/app/db/` | DB 연결과 모델 |
| `backend/app/services/` | 축제·경로 등 서비스 로직과 외부 API 어댑터 |
| `backend/app/agents/` | LangGraph 에이전트 흐름 |
| `backend/tests/` | 백엔드 테스트 |
| `infra/docker/` | 앱 컨테이너 설정 |
| `infra/db/` | DB 초기화 및 마이그레이션 관련 파일 |
| `scripts/` | 개발·검증 보조 스크립트 |

현재는 팀 공통 디렉터리만 만든 상태입니다. 실행 명령은 프론트엔드, 백엔드, Docker Compose 초기 설정을 추가하면서 이 문서에 기록합니다.
