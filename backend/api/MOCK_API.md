# 놀다가 모의 API

모든 값은 가상이며 API의 성공 응답은 `is_mock: true`를 반환합니다. 응답 헤더에는 `X-Mock: true`가 포함됩니다.

## 실행

`backend/`에서 실행합니다.

```sh
uv run --with-requirements api/requirements.txt uvicorn api.main:app --reload --port 8000
```

[API 문서](http://localhost:8000/docs)

## 시험

```sh
uv run --with-requirements api/requirements.txt pytest tests/api -q
```

## A01 서버 상태

`GET /api/v1/health`는 서버와 모의 DB·Redis 상태, API 버전을 반환합니다.

## A02 축제 목록

`GET /api/v1/festivals`에서 `region`, `date_from`, `date_to`, `q`, `status`, `sort`, `page`, `page_size`를 사용할 수 있습니다. 기본값은 전체 지역, 시작일 오름차순, 첫 페이지 20건입니다. 기간을 지정하면 그 기간과 겹치는 축제를 반환합니다.

## A03 축제 상세

`GET /api/v1/festivals/{festival_id}`는 축제 상세와 이미지 저작권 정보를 반환합니다. ID 형식이 잘못되면 422, 해당 축제가 없으면 404를 반환합니다.

## A04 귀갓길 접수

`POST /api/v1/routes/return`은 `request_id`, `festival_id`, `destination`을 받습니다. `origin`을 생략하면 축제 장소에서 출발합니다. 사용자 장소는 `query` 또는 `lat`과 `lng`로 지정합니다. 접수 응답은 202이며 `status_url`과 `route_access_token`을 반환합니다. `sync_ready`는 200으로 경로와 조회 토큰을 반환합니다. 같은 `request_id`와 본문으로 다시 접수하면 최초 응답을 재사용하며, 본문을 바꾸면 409를 반환합니다.

```sh
curl -sS -X POST 'http://localhost:8000/api/v1/routes/return' \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"return-demo-001","festival_id":"fst_000001","destination":{"query":"서울역"}}'
```

## A05 귀갓길 조회

`GET /api/v1/routes/return/{route_request_id}`에 접수 응답에서 받은 `X-Route-Access-Token`을 보냅니다. 기본 시나리오에서는 첫 조회가 `processing`, 두 번째부터 `ready`입니다. 처리 실패 상태도 200으로 조회됩니다.

아래 두 자리표시자를 접수 응답의 `route_request_id`와 `route_access_token`으로 바꾸고 두 번 호출합니다.

```sh
curl -sS 'http://localhost:8000/api/v1/routes/return/<route_request_id>' \
  -H 'X-Route-Access-Token: <route_access_token>'
```

## A25 가는 길 접수·조회

`POST /api/v1/routes/visit`은 `request_id`, `festival_id`, `origin`을 받습니다. `destination`을 생략하면 축제 장소가 도착지입니다. `X-Route-Access-Token`을 보내 `GET /api/v1/routes/visit/{route_request_id}`로 조회합니다. 완료된 경로의 `direction`은 `visit`입니다.

## X-Mock-Scenario

A04와 A25 접수 요청에 아래 헤더 값을 지정할 수 있습니다.

| 값 | 접수 응답 | 조회 상태 |
| --- | --- | --- |
| `async_ready` (기본) | 202 `queued` | `processing` → `ready` |
| `sync_ready` | 200 `ready` | `ready` |
| `async_unavailable` | 202 `queued` | `processing` → `unavailable` (`ROUTE_UPSTREAM_ERROR`) |
| `async_timeout` | 202 `queued` | `processing` → `timed_out` (`ROUTE_TIMEOUT`) |
| `overloaded` | 503 `ROUTE_OVERLOADED` | 해당 없음 |
| 기타 | 422 `VALIDATION_ERROR` | 해당 없음 |

## 가상 축제 6건

| ID | 이름 | 지역 | 장소 | 위도, 경도 | 시작일 ~ 종료일 | 상태 | 이미지 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fst_000001` | 광화문 겨울빛 축제 | SEOUL | 광화문광장 | 37.5759, 126.9768 | 2026-11-20 ~ 2026-12-31 | ongoing | Type3 |
| `fst_000002` | 한강 겨울 야시장 | SEOUL | 여의도 한강공원 | 37.5284, 126.9327 | 2026-12-05 ~ 2026-12-07 | upcoming | Type1 |
| `fst_000003` | 부산 빛 축제 | BUSAN | 광복로 일대 | 35.1003, 129.0337 | 2026-11-15 ~ 2026-11-30 | ongoing | Type3 |
| `fst_000004` | 해운대 모래 축제 | BUSAN | 해운대해수욕장 | 35.1587, 129.1604 | 2026-06-01 ~ 2026-06-03 | ended | Type3 |
| `fst_000005` | 평창 송어 축제 | GANGWON | 오대천 일원 | 37.5640, 128.3846 | 2026-12-26 ~ 2027-01-25 | upcoming | 없음 |
| `fst_000006` | 장소 미정 축제 | GYEONGGI | 미정 | 미정 | 미정 | needs_review | 없음 |
