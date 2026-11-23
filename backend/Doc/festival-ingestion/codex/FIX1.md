# Codex 작업 지시서 — FIX1 (실제 축제 ID)

1. `Doc/festival-ingestion/codex/_COMMON.md` 규칙을 지킨다. 이번에는 IMP-PLAN FIX1 목록의 `api/services/` 파일을 고친다.
2. `Doc/festival-ingestion/IMP-PLAN.md`의 **FIX1** 절, `Doc/festival-ingestion/SPEC.md`의 **7절(I14)**만 읽는다.
3. 먼저 `api/services/festival_store.py`(get_festival), `api/routers/festivals/catalog.py`(uses_festival_db), 고칠 서비스 4개를 읽는다. **축제를 찾는 줄만** 바꾸고 다른 동작은 그대로 둔다.
4. 전체 시험이 통과하면 FIX1 체크박스(Codex 몫: 첫 두 줄)를 `[x]`로 바꾸고 멈춘다.
