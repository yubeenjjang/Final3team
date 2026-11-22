# Codex 작업 지시서 — 5단계

1. `Doc/codex/_COMMON.md`의 규칙을 지킨다.
2. `Doc/IMP-PLAN.md`의 **5단계** 절(만들 파일·체크리스트)을 읽는다.
3. `Doc/SPEC.md`에서 R14(주소만), 5절(R18~R22), R17만 읽는다.
4. 먼저 `api/errors.py`, `api/mocks/store.py`, `api/mocks/festivals.py`, `api/services/mock_auth.py`(access 토큰 → 사용자 확인 함수), `api/routers/festivals/catalog.py`를 읽고 그 방식을 따른다. `api/main.py`는 라우터 등록 두 줄만 추가한다.
5. SPEC 확인 방법을 하나도 빠짐없이 시험으로 만들고, 전체 시험이 통과하면 IMP-PLAN 5단계 체크박스를 `[x]`로 바꾸고 멈춘다(commit하지 않음).
