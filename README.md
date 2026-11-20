# 놀다가 (NOLDAGA)

전국 축제 탐색과 AI 안심 귀가 서비스를 위한 팀 프로젝트 저장소입니다.

## 문서 디렉터리

| 경로 | 용도 |
| --- | --- |
| `Docs/Step 1/` | 확정 기획서와 WBS |
| `Docs/Step 2/` | API·DB 및 추가 기능 설계 문서 |
| `Docs/Step 3/` | 단일 에이전트 상태 전이·자기 성찰 산출물 |
| `Docs/Step 4/` | 멀티 에이전트 협업·보안·Auto-Healing 산출물 |
| `Docs/Step 5/` | 통합 테스트·배포 설계 산출물 |

## 코드 디렉터리

| 경로 | 역할 |
| --- | --- |
| `frontend/` | 사용자 화면과 관리자 화면 |
| `backend/api/` | 사용자 요청을 받는 FastAPI 서버와 서비스 기능 |
| `backend/agents/` | AI Agent, RAG, Celery 백그라운드 작업 |
| `backend/shared/` | API와 Agent가 함께 쓰는 설정·데이터 형식·DB 연결 |
| `backend/tests/` | API, Agent, 실시간 통신, 복구, 통합·부하 시험 |
| `infra/` | DB·Redis·배포 환경 설정 |

현재는 기능별 초기 디렉터리와 Python 파일의 용도 주석을 준비했습니다. 구현 코드와 실행 설정은 각 기능을 개발할 때 추가합니다. 담당 경로와 브랜치 규칙은 [협업 규칙 및 디렉터리](Docs/GitHub_협업_규칙_및_디렉터리.md)를 참고하세요.
