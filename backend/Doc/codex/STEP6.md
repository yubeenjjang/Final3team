# Codex 작업 지시서 — 6단계

1. `Doc/codex/_COMMON.md`의 규칙을 지킨다.
2. `Doc/IMP-PLAN.md`의 **6단계** 절(만들 파일·체크리스트)을 읽는다.
3. `Doc/SPEC.md`에서 R11·R12·R13(기존 시나리오 동작 이해용, 고치지 않음)과 6절(R23~R26)만 읽는다.
4. 먼저 `api/services/mock_routes.py`, `api/schemas/routes.py`, `tests/api/test_step2_routes.py`를 읽고 그 방식(시나리오 표·상태 진행·오류 모양·시험 fixture)을 따른다.
5. 기존 시나리오 5개의 동작·응답과 기존 시험은 바꾸지 않는다. 새 시나리오는 A04(귀가)와 A25(가는 길) 모두에서 동작해야 한다.
6. SPEC 확인 방법을 하나도 빠짐없이 시험으로 만들고, 전체 시험이 통과하면 IMP-PLAN 6단계 체크박스(commit 줄 제외)를 `[x]`로 바꾸고 멈춘다(commit하지 않음).
