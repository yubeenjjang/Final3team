# W14 Festival Agent 통합 검증 — 2026-11-25

- 기준: `yubeen`에 `dayoung` 5a60245의 Festival Agent 그래프·역할 구현과 관련 시험을 가져왔다. RAG 실험과 별도 `FestivalApiTools` 래퍼는 W14 범위 밖이며, 호출은 `yubeen`의 공통 `ToolExecutor`로 통일했다.
- 복합 흐름: `search_festivals` → 검색 결과의 동일 `festival_id`로 `get_festival` → `get_crowd`. 공통 실행기의 허용 도구 목록과 `X-Request-ID` 전달을 확인했다. 귀가 도구는 Festival Agent 권한에서 거부된다.
- Python 3.14 Linux Docker에서 Agent 시험과 기존 비동기 답변 경계 시험 **51/51 통과**. 현재 FastAPI 라우터를 TestClient로 호출하는 복합 흐름 시험을 포함한다. 이 라우터 시험은 모의 데이터이며 외부 공급원 실호출은 아니다.
- `check_festival_live.py`는 실제 DB·공급원 API를 띄운 환경에서 검색·상세·혼잡을 재검증할 때 사용할 수 있다.
- A06 자연어 질문을 해석해 Festival Agent를 기본 비동기 답변 진입점으로 선택하는 작업은 별도 단계다. 현재 `api.jobs.assistant_runner`의 기본 모의 대체 동작은 바꾸지 않았다.
