# Codex 공통 규칙 — 귀가 경로 실제 조회 트랙

- 작업 폴더는 `backend/`. 공통 시험은 저장소 루트에서 실행한다.
- **읽을 문서는 `Doc/route-providers/SPEC.md`(해당 절)와 `Doc/route-providers/IMP-PLAN.md`(해당 단계)뿐.** SPEC에 없는 것은 만들지 않는다.
- **IMP-PLAN '만들 파일' 밖은 만들거나 고치지 않는다.** 특히 `agents/`, `shared/`, `frontend/`, `infra/`, `Docs/`, `tests/routes/fixtures/`, 다른 사람 파일.
- 외부 네트워크·실제 키 금지(시험은 `httpx2.MockTransport`·가짜 객체·합성 고정 파일). 새 패키지 금지. 시험용 가짜 키 `"TEST_KEY_DO_NOT_USE"`.
- **고정 파일은 합성 데이터다.** 실제 경로처럼 문서·주석에 쓰지 않는다.
- 저장소 루트 공통 시험은 `uv run --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q`로 실행한다. 시험 이름에 요구 번호를 넣는다.
- 키·비밀값을 코드·출력·로그·예외 메시지에 쓰지 않는다. 주석·오류 메시지 한국어, 이름 영어, 타입 힌트, 함수는 짧게.
- 끝내는 조건: 체크리스트(commit·Claude 줄 제외) 완료 + 시험 전부 통과 → 멈춤. 같은 실패 3번 → 멈추고 보고. commit하지 않는다.
- 끝나면 짧게: 만든 파일 / 시험 숫자 / SPEC과 다른 곳·이유 / 메모에 적을 것.
