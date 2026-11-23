# Codex 작업 지시서 — 축제 수집 2단계 (DB 저장)

1. `Doc/festival-ingestion/codex/_COMMON.md` 규칙을 지킨다. 이번 단계는 `api/requirements.txt`에 이미 들어간 `sqlalchemy`·`psycopg`·`python-ulid`를 쓴다(새 패키지 금지).
2. `Doc/festival-ingestion/IMP-PLAN.md`의 **2단계** 절을 읽는다.
3. `Doc/festival-ingestion/SPEC.md`에서 4절(I9~I11)과 2절 I3·I7(출력 모양·공개 판정)만 읽는다.
4. IMP-PLAN에 적힌 DDL 블록만 읽고 **실제 컬럼 이름·제약을 그대로** 쓴다(SPEC과 DDL이 다르면 DDL을 따르고 메모에 적는다).
5. 먼저 `api/ingestion/festivals/normalize.py`·`collect.py`를 읽고 그 방식을 따른다.
6. DB가 없으니 `-m db` 시험은 건너뛴 채로 두고, 나머지 시험이 전부 통과하면 체크리스트의 Codex 몫(I9·I10·I11·일반 시험)을 `[x]`로 바꾸고 멈춘다.
