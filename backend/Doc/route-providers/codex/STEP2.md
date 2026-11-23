# Codex 작업 지시서 — 경로 2단계 (실제 경로 서비스·연결)
1. `Doc/route-providers/codex/_COMMON.md` 규칙을 지킨다.
2. `Doc/route-providers/IMP-PLAN.md` **2단계** 절을 읽는다.
3. `Doc/route-providers/SPEC.md`의 1절(P1)과 5절(P9~P12)만 읽는다. 기존 응답 규칙은 `Doc/SPEC.md`의 R11~R13과 6절(R23~R25)만 읽는다.
4. 먼저 `api/services/mock_routes.py`, `api/routers/routes/routes.py`, `api/main.py`(`_serves_real_data`), `api/services/festival_lookup.py`, 1단계 어댑터·`quota.py`를 읽는다. **`ROUTE_PROVIDER`가 없거나 `mock`이면 지금 동작이 한 글자도 바뀌면 안 된다.**
5. 공급원은 가짜 객체로 주입해 시험한다(실제 호출 금지). 시간은 주입 가능한 시계로.
6. 전부 통과하면 2단계 체크박스(Codex 몫)를 `[x]`로 바꾸고 멈춘다.
