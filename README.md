# 놀다가 (NOLDAGA)

전국 축제 탐색과 AI 안심 귀가 서비스를 위한 팀 프로젝트 저장소입니다.

## 공통 디렉터리

| 경로 | 용도 |
| --- | --- |
| `Docs/Step 1/` | 확정 기획서와 WBS |
| `Docs/Step 2/` | API·DB 및 추가 기능 설계 문서 |
| `Docs/Step 3/` | 단일 에이전트 상태 전이·자기 성찰 산출물 |
| `Docs/Step 4/` | 멀티 에이전트 협업·보안·Auto-Healing 산출물 |
| `Docs/Step 5/` | 통합 테스트·배포 설계 산출물 |
| `frontend/` | Next.js 웹 화면 |
| `backend/` | FastAPI, Function Calling, LangGraph |
| `infra/` | Docker, PostgreSQL/pgvector, Redis, AWS 설정 |

현재는 팀 공통 디렉터리만 준비했습니다. 각 서비스의 실행 설정과 `compose.yaml`은 구현할 때 추가하고 여기에 실행 방법을 기록합니다.
