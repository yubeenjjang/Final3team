# Codex 작업 지시서 — 축제 수집 3단계 (A02·A03 DB 조회)

1. `Doc/festival-ingestion/codex/_COMMON.md` 규칙을 지킨다. 단, 이번 단계는 `api/routers/festivals/catalog.py`·`api/schemas/festivals.py`(권오현 담당)도 IMP-PLAN 목록대로 고친다.
2. `Doc/festival-ingestion/IMP-PLAN.md`의 **3단계** 절을 읽는다.
3. `Doc/festival-ingestion/SPEC.md`에서 5절(I12·I13)만 읽는다. 기존 모의 동작 규칙은 `Doc/SPEC.md`의 R6~R8만 읽는다.
4. 먼저 `api/routers/festivals/catalog.py`, `api/schemas/festivals.py`, `api/mocks/store.py`, `api/ingestion/db.py`, `tests/api/test_step1_festivals.py`를 읽고 그 방식을 따른다. **`FESTIVAL_DATA`가 없거나 `mock`이면 지금 동작과 응답이 한 글자도 바뀌면 안 된다**(기존 시험 전부 통과).
5. 지정 DDL 블록만 보고 실제 컬럼 이름을 쓴다.
6. DB 시험은 건너뛴 채로 두고, 나머지가 전부 통과하면 체크리스트의 Codex 몫(I12·I13·일반 시험)을 `[x]`로 바꾸고 멈춘다.
