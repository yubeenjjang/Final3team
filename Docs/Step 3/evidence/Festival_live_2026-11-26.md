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
