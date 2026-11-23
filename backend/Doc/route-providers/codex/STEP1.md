# Codex 작업 지시서 — 경로 1단계 (어댑터·한도)
1. `Doc/route-providers/codex/_COMMON.md` 규칙을 지킨다.
2. `Doc/route-providers/IMP-PLAN.md` **1단계** 절을 읽는다.
3. `Doc/route-providers/SPEC.md`의 0~4절(P1~P8)만 읽는다.
4. 먼저 `tests/routes/fixtures/` 모양, `api/services/mock_routes.py`의 `_candidate()`, `api/providers/tourapi.py`(클라이언트 주입·키 숨김 방식)를 본다.
5. SPEC '확인'을 빠짐없이 시험으로 만들고, 전부 통과하면 1단계 체크박스(commit 줄 제외)를 `[x]`로 바꾸고 멈춘다.
