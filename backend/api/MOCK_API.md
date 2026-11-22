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

## 가상 축제 6건

| ID | 이름 | 지역 | 장소 | 위도, 경도 | 시작일 ~ 종료일 | 상태 | 이미지 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fst_000001` | 광화문 겨울빛 축제 | SEOUL | 광화문광장 | 37.5759, 126.9768 | 2026-11-20 ~ 2026-12-31 | ongoing | Type3 |
| `fst_000002` | 한강 겨울 야시장 | SEOUL | 여의도 한강공원 | 37.5284, 126.9327 | 2026-12-05 ~ 2026-12-07 | upcoming | Type1 |
| `fst_000003` | 부산 빛 축제 | BUSAN | 광복로 일대 | 35.1003, 129.0337 | 2026-11-15 ~ 2026-11-30 | ongoing | Type3 |
| `fst_000004` | 해운대 모래 축제 | BUSAN | 해운대해수욕장 | 35.1587, 129.1604 | 2026-06-01 ~ 2026-06-03 | ended | Type3 |
| `fst_000005` | 평창 송어 축제 | GANGWON | 오대천 일원 | 37.5640, 128.3846 | 2026-12-26 ~ 2027-01-25 | upcoming | 없음 |
| `fst_000006` | 장소 미정 축제 | GYEONGGI | 미정 | 미정 | 미정 | needs_review | 없음 |
