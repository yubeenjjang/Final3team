# Codex 공통 규칙 — 축제 수집 트랙

- 작업 폴더는 저장소 `backend/`다. 수집 명령은 `backend/`에서 실행한다.
- **읽을 문서는 `Doc/festival-ingestion/SPEC.md`(해당 절)와 `Doc/festival-ingestion/IMP-PLAN.md`(해당 단계)뿐.** 설계서 전체를 읽지 않는다. SPEC에 없는 것은 만들지 않는다.
- **IMP-PLAN '만들 파일' 밖은 만들거나 고치지 않는다.** 특히 `agents/`, `shared/`, `frontend/`, `infra/`, `Docs/`, `tests/ingestion/fixtures/`, 다른 사람 라우터.
- 외부 네트워크·실제 API 키 사용 금지(시험은 `httpx2.MockTransport` + 고정 파일). 새 패키지 설치 금지(`requirements.txt`는 Claude만 고침).
- 저장소 루트 공통 시험은 `python -m pytest backend/tests -q`로 실행한다. uv 환경에서는 `uv run --offline --with-requirements backend/api/requirements.txt python -m pytest backend/tests -q`를 사용한다. 시험 이름에 요구 번호(`test_I5_…`)를 넣는다.
- **키·비밀번호를 코드·시험·출력·로그에 쓰지 않는다.** 시험용 가짜 키는 `"TEST_KEY_DO_NOT_USE"`.
- 주석·오류 메시지 한국어, 이름 영어, 타입 힌트, 함수는 짧게.
- 끝내는 조건: 체크리스트(commit 줄 제외) 완료 + 시험 전부 통과 → 멈춤. 같은 실패 3번 → 멈추고 보고.
- git: commit하지 않는다. 끝나면 짧게 보고: 만든 파일 / 시험 숫자 / SPEC과 다른 곳·이유 / 메모에 적을 것.
