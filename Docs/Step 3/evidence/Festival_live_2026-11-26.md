# Festival Agent 실제 API 연속 조회 기록 — 2026-11-26

## 재현 기준

- 브랜치·실행 커밋: `dayoung dc35ad5`. 실조회 직후 같은 임시 체크아웃에서 `git rev-parse --short HEAD`로 확인했다.
- 실행 환경: 실제 축제·혼잡 API에 접속 가능한 macOS 터미널, 저장소 `backend/`.
- 명령: `python -m agents.check_festival_live --base-url '<API v1 루트 주소>' --crowd-festival-id fst_01M835B57450M888RBNEFVRWWA --require-crowd-answered` (실행 때 사용한 Python 경로·API 주소는 생략).
- 점검기 조건: 검색·상세·혼잡 원시 응답 `is_mock:false`, 혼잡 `answered`, 축제 ID 일치, `observed_at`·`source` 존재. 복합 그래프의 호출 순서 `search_festivals → get_festival → get_crowd`와 근거 3건의 ID 일치.

## 사용자 제공 터미널 출력

```text
ongoing: total=1, agent_evidence=1
upcoming: total=15, agent_evidence=10
detail: festival_id=fst_01M835BCHV21MGQF4333AAJZJ4, outcome=answered, source=tourapi
Real DB search/detail check passed.
crowd_festival_detail: festival_id=fst_01M835B57450M888RBNEFVRWWA, outcome=answered
crowd: festival_id=fst_01M835B57450M888RBNEFVRWWA, provider_status=ok, agent_outcome=answered, is_estimate=False, observed_at=2026-11-26T09:00:00+09:00, source=seoul_citydata
composite: festival_id=fst_01M835B57450M888RBNEFVRWWA, outcome=answered, tool_calls=3, evidence=3
```

검색 결과를 임의로 고른 별도 `detail`은 다른 축제 ID이며, 서울빛초롱축제의 상세·혼잡과 섞지 않는다. 동일 ID 연속 흐름의 근거는 `composite` 행과 점검기 내부 검증이다. 혼잡 `observed_at`은 자료 기준 시각으로, 명령 실행 시각이나 행사장 내부 혼잡을 뜻하지 않는다. 이 실행에서 미지원 지역을 새로 실호출한 것은 아니다.

## 같은 커밋의 Festival 단독 시험

- 실행 환경: 위와 같은 macOS 임시 체크아웃의 `backend/`, Python 3.14.7 가상환경.
- 확인 커밋: `git rev-parse --short HEAD` → `dc35ad5`.
- 명령: `"$test_dir/venv/bin/python" -m unittest discover -s tests/agents -p 'test_festival_*.py' -q`.
- 결과: `Ran 35 tests in 0.076s`, `OK`.
- 출력에 404 `FESTIVAL_NOT_FOUND`와 503 `TOOL_HTTP_ERROR`의 `ResourceWarning` 두 줄이 있었으나 시험 실패는 없었다. 경고를 오류 처리 정상 동작의 증거로 확대하지 않는다.

이 35개는 고정 응답·모의 HTTP를 이용한 Festival 단독 시험이다. 위 실조회와 동일 커밋에서 실행했지만, 팀 `main` 병합 후 전체 백엔드 시험 결과는 아니다.

## 추가 실조회: 서로 다른 축제 두 건 (2026-11-26)

- 실행 전 `git pull origin dayoung`은 `3ce98dc..777d743` 빠른 전진으로 끝났다. 별도의 `git rev-parse` 출력은 제공되지 않았으므로 실행 HEAD는 이 pull 결과를 기준으로 기록한다.
- 실행 옵션: 위 실조회 명령에 `--verify-multi-festival` 추가. 점검기는 진행·예정 검색에서 서로 다른 두 ID를 고르고, 각 ID의 실제 DB 상세와 Agent 상세 근거가 요청 ID와 일치하는지 검사한다.
- 터미널 출력: `ongoing: total=1, agent_evidence=1`, `upcoming: total=15, agent_evidence=10`; 첫 상세 `fst_01M835BCHV21MGQF4333AAJZJ4`는 `answered`·`source=tourapi`였다. `multi_festival: first_id=fst_01M835BCHV21MGQF4333AAJZJ4, second_id=fst_01M835BS447VDC8PVAQNM8GKHF, outcome=answered`가 출력됐다.
- 서울빛초롱축제 `fst_01M835B57450M888RBNEFVRWWA`의 상세·혼잡·복합 조회도 `answered`였다. 혼잡 공급원은 `seoul_citydata`, `is_estimate=False`, `observed_at=2026-11-26T10:00:00+09:00`이며 복합 그래프는 도구 호출 3회·근거 3건이었다.

이는 실제 DB의 **서로 다른 두 축제 상세 ID 분리**와 서울빛초롱축제의 별도 연속 조회를 확인한 결과다. 두 번째 축제의 혼잡 조회, 공식 공지·시설 공급원, 팀 `main` 병합 후 전체 시험은 이 실행에 포함되지 않는다.

## 최신 개인 브랜치 단독 시험 (2026-11-26)

- `git pull origin dayoung`의 `777d743..122cb32` 빠른 전진 후 `git rev-parse --short HEAD` → `122cb32`.
- macOS·Python 3.14.7, `backend/`에서 `"$test_dir/venv/bin/python" -m unittest discover -s tests/agents -p 'test_festival_*.py' -q` 실행.
- 결과: `Ran 35 tests in 0.077s`, `OK`. 404·503 응답 시험에서 `ResourceWarning` 두 줄이 출력됐으나 실패는 없었다.
- 이는 새 시간 예산 시험 코드 및 최종 제출 `main` 커밋 이전 결과다. 해당 결과와 팀 전체 시험은 이후 같은 제출 커밋에서 다시 기록한다.

## 시간·호출 예산 재현 시험 (2026-11-26)

- 실행 전 `git pull origin dayoung`은 `122cb32..45be6ed` 빠른 전진이었고, `git rev-parse --short HEAD` 출력은 `45be6ed`였다.
- macOS·Python 3.14.7, `backend/`에서 Festival 단독 명령 결과 `Ran 36 tests in 0.080s`, `OK`. 404·503 사례의 `ResourceWarning` 두 줄은 있었으나 실패는 없었다.
- 같은 체크아웃에서 `"$test_dir/venv/bin/python" -m agents.check_festival_budget` 실행.
- **시간 경계:** 가상 시계 30.1초, 실제 벽시계 4.982ms, 도구 호출 2회(검색·상세), `partial`. 혼잡 도구는 호출하지 않았고 답변에 `시험 광장` 상세와 `조회 제한에 도달해 혼잡 정보를 확인할 수 없습니다` 안내가 함께 있었다.
- **4회 상한:** 실제 벽시계 4.102ms, 도구 호출 4회(검색, 상세 실패, 상세 재시도 성공, 혼잡 실패), `partial`. 추가 호출 없이 같은 상세 근거와 혼잡 미확인 안내로 종료했다.

가상 시계의 30.1초는 **실제 30초를 기다린 측정값이 아니다.** 벽시계 수치는 고정 응답을 쓴 로컬 재현 실행의 경과 시간이다. 이 시험은 30초 호출 전 검사와 4회 상한·부분 답변을 검증하며, 실제 외부 HTTP 호출이 30초에서 강제 중단되는지 검증하지 않는다.

## 최신 코드의 Windows 재시험 (2026-11-26)

- 코드 기준: `dayoung f454e7e`, Windows·Python 3.12.15. `backend/`에서 `uv run --no-project --with-requirements agents/requirements.txt python -B -m unittest discover -s tests/agents -p 'test_festival_*.py' -q` 실행: **37개, OK**.
- 같은 환경에서 `uv run --no-project --with-requirements agents/requirements.txt python -B -m agents.check_festival_budget` 실행: 호출 전 30.1초 가상 경계는 2회 호출·`partial`·벽시계 7.264ms, 4회 상한은 4회 호출·`partial`·벽시계 4.244ms였다.
- 신규 37번째 시험은 검색·상세 성공 후 혼잡 도구가 성공 응답을 **30초가 지난 뒤** 반환한 고정 응답이다. 응답은 답변에 사용되지 않았고, 도구 기록에는 `ok=True`가 남았으며, 최종 결과는 상세 근거와 혼잡 미확인 안내를 포함한 `partial`이었다. 실제 공급원에서 30초 대기를 재현한 시험은 아니다.
- 위 결과는 개인 브랜치 시험이다. 제출 기준 `main`의 Festival·백엔드 전체 시험 결과는 아래 병합 후 시험 절에 별도로 기록했다.

## 팀원 독립 재검토 (2026-11-26)

- 태경님이 `dayoung f249f6e` 기준 macOS·Python 3.14.8에서 Festival 단독 `Ran 37 tests`, `OK`, `check_festival_budget` 2회·4회 호출 모두 `partial`을 확인했다.
- 같은 기준에서 `tests/agents` 전체(RAG 포함)는 `Ran 48 tests`, `OK`였다. 이는 태경님이 공유한 시험 출력 요약이며, 팀 `main` 병합 후 전체 백엔드 시험 기록은 아니다.

## 병합 전 백엔드 시험 사전 점검 (2026-11-26)

- 코드 기준: `dayoung 0b2369a`, Windows·Python 3.12.15. 저장소 루트에서 `PYTHONPATH=backend`를 지정하고 LangGraph·pytest를 제공한 환경으로 `python -B -m pytest backend/tests -q` 실행: **51 passed, 2 subtests passed in 0.73s**.
- `dayoung` 단독 체크아웃에서 루트 명령을 경로 지정 없이 실행하면 `agents` 모듈을 찾지 못해 시험 수집 단계에서 실패한다. 위 결과는 실행 환경의 모듈 경로를 보완한 **병합 전 사전 점검**이며, 팀 `main`의 최종 시험으로 기록하지 않는다.

## 제출 기준 `main` 병합 후 시험 확인 (2026-11-26)

- 다영님이 팀에 전달한 시험 확인의 **코드 기준 커밋은 `main 0fda8fd`**다. 이 커밋은 `dayoung 699c214`를 병합한 커밋이다.
- Festival 단독 시험: **37개 통과**.
- 백엔드 전체 시험: **51개 통과, 하위 시험 2개 통과**.
- 시간 제한과 4회 도구 호출 상한의 재현 사례: **두 사례 모두 `partial`로 종료**. 가상 시계·고정 응답으로 확인한 예산 처리이며 실제 외부 HTTP 호출을 30초에 강제 중단한 증거는 아니다.
- 태경님 최종 설계 검토 완료. 앞 절의 개인 브랜치 시험·실조회와 이 병합 후 시험 결과는 기준 커밋이 다르다.

이 절은 다영님이 전달한 결과 요약을 제출 기준으로 기록한다. 병합 후 실행의 원시 터미널 출력, 정확한 실행 명령·Python 버전·경과 시간은 이 메시지에 포함되지 않아 임의로 채우지 않았다. 이 문서 갱신 커밋에서 시험을 재실행한 결과로 표시하지 않는다.
