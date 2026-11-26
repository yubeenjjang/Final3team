# 놀다가 모의 API

모든 값은 가상이며 API의 성공 응답은 `is_mock: true`를 반환합니다. 응답 헤더에는 `X-Mock: true`가 포함됩니다.

## 실행

`backend/`에서 실행합니다.

```sh
uv run --with-requirements api/requirements.txt uvicorn api.main:app --reload --port 8000
```

[API 문서](http://localhost:8000/docs)

## 시험

저장소 루트에서 다음 명령을 실행합니다.

```sh
uv run --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

## A01 서버 상태

`GET /api/v1/health`는 기본 설정에서 서버와 모의 DB·Redis 상태, API 버전을 반환합니다. DB를 사용하는 API 설정에서는 앱 계정으로 1초 안에 `SELECT 1`을 확인하고, 실패하면 503을 반환합니다. 공통 Redis 연결 전까지 이 설정의 `redis` 값은 `not_configured`입니다.

## A02 축제 목록

`GET /api/v1/festivals`에서 `region`, `date_from`, `date_to`, `q`, `status`, `sort`, `page`, `page_size`를 사용할 수 있습니다. 기본값은 전체 지역, 시작일 오름차순, 첫 페이지 20건입니다. 기간을 지정하면 그 기간과 겹치는 축제를 반환합니다.

## A03 축제 상세

`GET /api/v1/festivals/{festival_id}`는 축제 상세와 이미지 저작권 정보를 반환합니다. ID 형식이 잘못되면 422, 해당 축제가 없으면 404를 반환합니다.

## A04 귀갓길 접수

`POST /api/v1/routes/return`은 `request_id`, `festival_id`, `destination`을 받습니다. `origin`을 생략하면 축제 장소에서 출발합니다. 사용자 장소는 `query` 또는 `lat`과 `lng`로 지정합니다. 접수 응답은 202이며 `status_url`과 `route_access_token`을 반환합니다. `sync_ready`는 200으로 경로를 반환하므로 바로 표시합니다. 같은 `request_id`와 본문으로 다시 접수하면 최초 응답을 재사용하며, 본문을 바꾸면 409를 반환합니다.

## A05 귀갓길 조회

`GET /api/v1/routes/return/{route_request_id}`에 접수 응답에서 받은 `X-Route-Access-Token`을 보냅니다. 기본 시나리오에서는 첫 조회가 `processing`, 두 번째부터 `ready`입니다. 처리 실패 상태도 200으로 조회됩니다.

## A25 가는 길 접수·조회

`POST /api/v1/routes/visit`은 `request_id`, `festival_id`, `origin`을 받습니다. `destination`을 생략하면 축제 장소가 도착지입니다. `X-Route-Access-Token`을 보내 `GET /api/v1/routes/visit/{route_request_id}`로 조회합니다. 완료된 경로의 `direction`은 `visit`입니다.

## A06 챗봇 작업 접수

`POST /api/v1/assistant/query`에 `request_id`와 `message`를 보냅니다. 익명 대화를 이어가려면 `conversation_id`와 이전 작업의 `X-Run-Access-Token`을 보냅니다. 선택 항목은 `context.festival_id`, `context.route_request_id`, `reference_date`입니다. 경로 ID를 보내면 `X-Route-Access-Token`도 필요합니다. 접수 응답은 202이며 `run_id`, `conversation_id`, `status_url`, `events_url`, `run_access_token`을 반환합니다. 같은 클라이언트의 세션 쿠키나 작업 토큰으로 다시 제출하면 기존 접수 응답을 반환합니다. 같은 `request_id`로 본문을 바꾸면 409를 반환합니다.

## A06-1 챗봇 작업 조회

`GET /api/v1/assistant/runs/{run_id}`에 `X-Run-Access-Token`을 보냅니다. 첫 조회는 `running`이고, 두 번째부터 `succeeded` 또는 `failed`입니다. 귀가 질문의 결과에 경로 ID와 토큰이 있으면 A05에서 경로를 조회할 수 있습니다.

## A06-2 챗봇 진행 SSE

응답의 `events_url`에 `X-Run-Access-Token`을 보내면 진행 `step`, 답변 `token`, 종료 `done` 또는 `failed`를 받을 수 있습니다.

## A07 공지·통제

`GET /api/v1/festivals/{festival_id}/notices`는 공지와 교통 통제를 최근 효력 시작일 순으로 반환합니다. `type`으로 공지 종류를 고를 수 있습니다. 기본값인 `active_only=true`에서는 모의 기준 시각인 2026년 11월 22일 낮 12시(한국 시간)에 유효한 공지를 반환합니다. 종료된 공지까지 보려면 `active_only=false`를 지정합니다.

## A09 날씨

`GET /api/v1/festivals/{festival_id}/weather`는 현재 기온, 강수량, 강수 형태, 기상청 격자 좌표를 반환합니다. 예보 상태는 `unverified`입니다. 축제 좌표가 없으면 `unavailable`과 `FESTIVAL_LOCATION_UNKNOWN`을 반환합니다.

## A10 혼잡 구역

`GET /api/v1/festivals/{festival_id}/crowd`는 서울의 검증된 혼잡 구역과 예보 3건을 반환합니다. 서울 밖이거나 검증된 구역이 연결되지 않은 축제는 `unsupported`이며, 축제 좌표가 없으면 `unavailable`입니다.

각 구역 객체(`areas[]` 및 실제 모드의 `nearby_areas[]`·`nearby_areas[].data`)에는 서울시 공식 주요 121장소 영역(OA-21778) 기준의 위치 필드가 함께 포함됩니다. 카탈로그에 도형이 없으면 둘 다 `null`입니다.

- `center`: `{"lat": float, "lng": float}` (구역 중심 좌표, WGS84 위도·경도)
- `boundary`: `list[list[{"lat": float, "lng": float}]]` (닫힌 경계 링 배열. `Polygon`은 외곽 링 우선·내부 구멍 링 순, `MultiPolygon`은 포함된 모든 폴리곤의 링을 각 외곽 링 우선으로 평탄화해 포함)

응답 예시(`fst_000001`, 모의 모드, `boundary[0]` 꼭짓점 일부 생략):

```json
{
  "is_mock": true,
  "festival_id": "fst_000001",
  "status": "ok",
  "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": true},
  "source": "seoul_citydata",
  "observed_at": "2026-11-22T11:55:00+09:00",
  "notices": [
    "주변 지역 혼잡(모의 데이터) · 광화문·덕수궁",
    "행사장 안 혼잡과 다를 수 있어요"
  ],
  "error": null,
  "areas": [
    {
      "area_code": "POI009",
      "area_name": "광화문·덕수궁",
      "relation_type": "contains",
      "congest_level": "보통",
      "congest_color": "yellow",
      "congest_message": "사람이 몰려 있을 수 있지만 크게 붐비지는 않아요.(모의)",
      "population_min": 48000,
      "population_max": 50000,
      "observed_at": "2026-11-22T11:55:00+09:00",
      "forecast": [
        {"time": "2026-11-22T13:00:00+09:00", "congest_level": "보통", "population_min": 48000, "population_max": 50000}
      ],
      "center": {"lat": 37.5709305, "lng": 126.9771863},
      "boundary": [
        [
          {"lat": 37.5775077, "lng": 126.9739639},
          {"lat": 37.5775066, "lng": 126.9824442},
          {"lat": 37.5775077, "lng": 126.9739639}
        ]
      ]
    }
  ]
}
```

## A11 관심 축제 목록

`GET /api/v1/me/favorites`는 `Authorization: Bearer <access_token>`에 해당하는 사용자의 관심 축제를 반환합니다. 기본값은 최근에 저장한 순서로 첫 페이지 20건입니다. `sort=start_date`로 축제 시작일 순으로 정렬하고 `page`와 `page_size`로 페이지를 선택할 수 있습니다.

## A12 관심 축제 저장

`PUT /api/v1/me/favorites/{festival_id}`에 액세스 토큰을 보냅니다. 처음 저장하면 201을 반환합니다. 이미 저장된 축제는 기존 `saved_at`을 유지하며 200을 반환합니다.

## A13 관심 축제 삭제

`DELETE /api/v1/me/favorites/{festival_id}`에 액세스 토큰을 보냅니다. 관심 목록에서 삭제하면 204를 반환합니다. 저장한 적이 없는 축제의 삭제도 204를 반환합니다.

## A32 가입

`POST /api/v1/auth/signup`에 `email`, `password`, `display_name`, `birth_year`, `gender`를 보냅니다. 가입하면 201과 사용자 ID, 닉네임을 반환합니다. 등록된 이메일 또는 닉네임이면 409를 반환합니다.

## A33 로그인

`POST /api/v1/auth/login`에 `email`과 `password`를 보냅니다. 로그인하면 액세스 토큰과 갱신 토큰, 사용자 정보를 반환합니다. 이메일 또는 비밀번호가 틀리면 401을 반환합니다.

## A34 토큰 갱신

`POST /api/v1/auth/refresh`에 `refresh_token`을 보냅니다. 성공 응답에는 새 액세스 토큰과 갱신 토큰이 들어 있습니다. 폐기된 갱신 토큰을 다시 보내면 해당 사용자의 갱신 토큰이 모두 폐기됩니다.

## A35 로그아웃

`POST /api/v1/auth/logout`에 `Authorization: Bearer <access_token>` 헤더와 `refresh_token` 본문을 보냅니다. 성공하면 본문 없이 204를 반환합니다.

## X-Mock-Scenario

A04와 A25 접수 요청에 아래 헤더 값을 지정할 수 있습니다.

| 값 | 접수 응답 | 조회 상태 |
| --- | --- | --- |
| `async_ready` (기본) | 202 `queued` | `processing` → `ready` |
| `sync_ready` | 200 `ready` | `ready` |
| `async_unavailable` | 202 `queued` | `processing` → `unavailable` (`ROUTE_UPSTREAM_ERROR`) |
| `async_timeout` | 202 `queued` | `processing` → `timed_out` (`ROUTE_TIMEOUT`) |
| `overloaded` | 503 `ROUTE_OVERLOADED` | 해당 없음 |
| `sync_secondary` | 200 `ready` (`provider: kakao`, `provider_tier: secondary`) | `unavailable` (`ROUTE_SECONDARY_SYNC_ONLY`) |
| `async_secondary_sync_only` | 202 `queued` | `processing` → `unavailable` (`ROUTE_SECONDARY_SYNC_ONLY`) |
| `async_no_result` | 202 `queued` | `processing` → `unavailable` (`ROUTE_NO_RESULT`, 재시도 불가) |
| `async_quota_exceeded` | 202 `queued` | `processing` → `unavailable` (`ROUTE_QUOTA_EXCEEDED`, 재시도 불가) |
| 기타 | 422 `VALIDATION_ERROR` | 해당 없음 |

A07, A09, A10 요청에도 `X-Mock-Scenario`를 보낼 수 있습니다. 축제 조회와 좌표·지원 범위를 먼저 확인합니다. 공지 조회에는 좌표가 필요 없습니다.

| 값 | 응답 |
| --- | --- |
| `ok` (기본) | 200 `ok` |
| `stale` | 200 `stale`, 기존 데이터와 오래된 정보 안내 |
| `source_error` | 200 `unavailable`, 재시도 가능한 `SOURCE_RESULT_ERROR` |
| 기타 | 422 `VALIDATION_ERROR` |

## 가상 축제 6건

| ID | 이름 | 지역 | 장소 | 위도, 경도 | 시작일 ~ 종료일 | 상태 | 이미지 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fst_000001` | 광화문 겨울빛 축제 | SEOUL | 광화문광장 | 37.5759, 126.9768 | 2026-11-20 ~ 2026-12-31 | ongoing | Type3 |
| `fst_000002` | 한강 겨울 별빛 축제 | SEOUL | 여의도 한강공원 | 37.5284, 126.9327 | 2026-12-05 ~ 2026-12-07 | upcoming | Type1 |
| `fst_000003` | 부산 빛 축제 | BUSAN | 광복로 일대 | 35.1003, 129.0337 | 2026-11-15 ~ 2026-11-30 | ongoing | Type3 |
| `fst_000004` | 해운대 모래 축제 | BUSAN | 해운대해수욕장 | 35.1587, 129.1604 | 2026-06-01 ~ 2026-06-03 | ended | Type3 |
| `fst_000005` | 평창 송어 축제 | GANGWON | 오대천 일원 | 37.5640, 128.3846 | 2026-12-26 ~ 2027-01-25 | upcoming | 없음 |
| `fst_000006` | 장소 미정 축제 | GYEONGGI | 미정 | 미정 | 미정 | needs_review | 없음 |

## curl 예시

### 축제 목록

```sh
curl -sS 'http://localhost:8000/api/v1/festivals?region=SEOUL'
```

### 귀갓길 접수 → 조회

접수 응답의 ID와 토큰을 아래 조회 명령에 넣고 두 번 호출합니다.

```sh
curl -sS -X POST 'http://localhost:8000/api/v1/routes/return' \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"return-demo-001","festival_id":"fst_000001","destination":{"query":"서울역"}}'

curl -sS 'http://localhost:8000/api/v1/routes/return/<route_request_id>' \
  -H 'X-Route-Access-Token: <route_access_token>'
```

### 챗봇 접수 → 조회

접수 응답의 ID와 토큰을 아래 조회 명령에 넣고 두 번 호출합니다.

```sh
curl -sS -X POST 'http://localhost:8000/api/v1/assistant/query' \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"assistant-demo-001","message":"귀가 경로 알려 줘","context":{"festival_id":"fst_000001"}}'

curl -sS 'http://localhost:8000/api/v1/assistant/runs/<run_id>' \
  -H 'X-Run-Access-Token: <run_access_token>'
```
