# Codex 작업 지시서 — 축제 수집 1단계

1. `Doc/festival-ingestion/codex/_COMMON.md` 규칙을 지킨다.
2. `Doc/festival-ingestion/IMP-PLAN.md`의 **1단계** 절을 읽는다.
3. `Doc/festival-ingestion/SPEC.md`에서 0절, 1~3절(I1~I8), 6절만 읽는다.
4. 먼저 `tests/ingestion/fixtures/` 파일 모양과 `api/errors.py`(오류 스타일 참고만)를 본다. `api/providers/tourapi.py`는 지금 주석 한 줄뿐이니 채운다.
5. SPEC '확인'을 하나도 빠짐없이 시험으로 만들고, 전체 시험이 통과하면 IMP-PLAN 1단계 체크박스(commit 줄 제외)를 `[x]`로 바꾸고 멈춘다.
