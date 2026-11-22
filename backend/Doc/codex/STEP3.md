# Codex 작업 지시서 — 3단계

1. `Doc/codex/_COMMON.md`의 규칙을 지킨다.
2. `Doc/IMP-PLAN.md`의 **3단계** 절(만들 파일·체크리스트)을 읽는다.
3. `Doc/SPEC.md`에서 3단계 요구만 읽는다: 0절(R1~R5 — 지키기만), 3절(R14~R16), 4절(R17).
4. 1·2단계 코드(`api/errors.py`, `api/mocks/store.py`, `api/services/mock_routes.py`의 `create_ready_route`)를 먼저 읽고 따른다. `api/main.py`·2단계 파일은 고치지 않는다. 3단계 파일을 만들고 SPEC의 **확인 방법을 하나도 빠짐없이** 시험으로 만든다.
5. 시험이 전부 통과하면 IMP-PLAN 3단계 체크박스를 `[x]`로 바꾸고(이 파일 수정은 허용), commit하고 멈춘다.
