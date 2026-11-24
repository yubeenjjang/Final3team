# Codex 공통 규칙 (모든 단계)

- 작업 폴더는 저장소 `backend/`다. 서버는 `backend/`에서 실행한다.
- **읽을 문서는 `Doc/SPEC.md`(해당 절)와 `Doc/IMP-PLAN.md`(해당 단계)뿐이다.** `Docs/Step 2/API_설계문서.md` 전체를 읽지 않는다(토큰 절약). SPEC에 없는 것은 만들지 않는다.
- **IMP-PLAN의 '만들 파일' 목록 밖의 파일은 만들거나 고치지 않는다.** 특히 `agents/`, `shared/`, `frontend/`, `infra/`, `Docs/`, 다른 사람 라우터(`routers/festivals/recommendations.py`·`facilities.py`·`data_sources.py`·`info.py`, `routers/admin/`, `routers/community/`)는 건드리지 않는다.
- 외부 네트워크 호출·API 키 사용 금지. 패키지 설치는 `uv run --with-requirements api/requirements.txt …`로만 한다(전역 설치 금지).
- 코드 주석·오류 메시지는 한국어, 이름은 영어. 함수는 짧게. 타입 힌트를 단다.
- 저장소 루트 공통 시험은 `python -m pytest backend/tests -q`로 실행한다. uv 환경에서는 `uv run --offline --with-requirements backend/api/requirements.txt python -m pytest backend/tests -q`를 사용한다. `requirements.txt`에 새 패키지를 넣지 않는다. 시험 이름에 요구 번호(`test_R7_…`)를 넣는다.
- **끝내는 조건:** 해당 단계 체크리스트가 모두 되고 시험이 전부 통과하면 멈춘다. 같은 실패가 3번 반복되면 멈추고 원인을 보고한다.
- git: **commit하지 않는다**(`.git`이 읽기 전용). Claude가 확인한 뒤 commit한다. 체크박스는 시험이 통과하면 `[x]`로 바꾼다.
- 끝나면 마지막 답변으로 아래를 짧게 보고한다: 만든 파일 목록 / 시험 결과 숫자(통과·실패) / SPEC과 다르게 한 곳과 이유 / IMP-PLAN '메모'에 적을 것.
