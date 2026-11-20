# Backend

FastAPI 서버와 AI Agent 작업을 만드는 폴더입니다.

| 폴더 | 역할 |
| --- | --- |
| `api/` | HTTP 요청을 받고 인증·기능 처리·응답을 담당 |
| `api/routers/` | 축제·경로·계정·커뮤니티·AI·관리자 기능의 API 주소 |
| `api/schemas/` | 기능별 요청·응답 데이터 형식 |
| `api/services/` | 기능별 처리 규칙 |
| `api/repositories/` | 기능별 DB 조회·저장 코드 |
| `api/providers/` | TMAP·카카오·TourAPI 등 외부 데이터 연결 |
| `api/ingestion/` | 축제 원본 수집·정규화·적재 |
| `api/realtime/` | 사용자 채팅 WebSocket과 Agent 진행 이벤트 중계 |
| `api/healing/` | 내부 경로 처리 지연 계측·복구 조치 실행·재검증 |
| `agents/` | Agent 5개의 판단 흐름과 Celery 작업 |
| `agents/roles/` | Supervisor·Festival·Route·Diagnosis·Recovery Agent |
| `agents/tools/` | Agent가 사용하는 기능 호출 도구 |
| `agents/rag/` | 공식 안내문 검색과 출처 확인 |
| `agents/healing/` | Agent의 호출 재시도·폴백과 worker 상태 점검 |
| `shared/` | API·Agent가 함께 사용하는 코드 |
| `shared/contracts/` | 작업 ID·상태·복구 조치 등 공통 데이터 형식 |
| `shared/db/` | DB 연결, 작업 상태 저장, 모델과 구조 변경 파일 |
| `tests/` | API·Agent·실시간·복구·통합·부하 시험 |

`api/requirements.txt`와 `agents/requirements.txt`는 각각 필요한 Python 패키지를 기록합니다.
현재 `.py` 파일은 용도 주석만 있는 초기 뼈대이며, 실행 방법은 구현하면서 추가합니다.
