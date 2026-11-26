# Festival Agent 실제 API 연속 조회 기록 — 2026-11-26

## 재현 기준

- 브랜치: `dayoung`. 혼잡 관측 시각·출처 필수 검사 코드 `dc35ad5` 이후. 사용자가 실행한 정확한 HEAD SHA는 별도 출력되지 않았다.
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
