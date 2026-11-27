# Route Agent 최소 흐름 (11/27)

## 범위

12/8 시연을 위해 A04 귀가 경로 요청과 A05 상태 조회의 결과를 해석한다. 입력은 검증된 축제 ID와 목적지이며, 출발 좌표 확인과 실제 경로 계산은 API가 담당한다. Route Agent는 경로를 새로 만들거나 후보의 점수·구간을 해석하지 않는다.

| API 상태 | 에이전트 결과 | 사용자 안내 |
|---|---|---|
| `queued`·`processing` | `pending` | 처리 중이며 나중에 상태 조회 필요. 성공으로 기록하지 않음 |
| `ready` + `completed_valid_route=true` | `answered` | 경로 조회 완료, 귀가 화면에서 확인. 공급원과 조회 시각 표시 |
| `unavailable`·`timed_out`·`rejected` | `unavailable` | 경로 없음·시간 초과·과부하 등 오류 코드에 맞는 안내 |
| `ready` + 유효 경로 확인 실패 | `unavailable` | 완료 표시를 성공으로 오인하지 않음 |

사용자 응답과 에이전트 근거에는 `route_request_id`, 상태, 공급원, 조회 시각, 오류 코드 같은 메타데이터만 둔다. 경로 후보·구간·조회 토큰은 공통 도구 실행기가 제거하며, 경로 본문은 귀가 화면이 A05에서 직접 받는다. `is_mock=true`이면 모의 데이터라고 표시한다.

호출자는 대화마다 같은 `ToolExecutor`를 유지하고 A04의 `operation_id`를 전달해야 한다. 202가 오면 `retry_after_s` 이후 A05를 호출한다. 이 단독 구현은 자동 대기·반복 조회·Supervisor 연결·경로 점수 판정을 포함하지 않는다. 공급원 대체와 10초 처리 제한은 A04의 책임이다.

## 확인 결과

`backend/`에서 `python -B -m unittest tests.agents.test_route_agent -q`: 6개 통과. 전체 에이전트 시험은 Python 3.12와 `agents/requirements.txt` 환경에서 `python -B -m unittest discover -s tests/agents -q`: 74개 통과. 실제 TMAP 연속 호출과 화면 연결은 아직 확인하지 않았다.
