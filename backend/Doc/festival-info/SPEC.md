# 축제 정보 API 구현 명세

계약은 API 설계문서 6-2, 9-1, 13절 및 DB 스키마 설계서의 006 공지와 외부 캐시 표를 따릅니다.

| API | 실제 모드 | 데이터 및 상태 |
|---|---|---|
| A07 `/{festival_id}/notices` | `NOTICES_PROVIDER=real` | 공개 축제의 `official_notices` 중 `approved`만 응답. `type` 선택, `active_only=true` 기본. 효력 시작·종료가 null이면 해당 방향 제한 없음. 빈 결과는 `ok`와 `items:[]`. |
| A09 `/{festival_id}/weather` | `WEATHER_PROVIDER=real` | 기상청 좌표 격자에서 이전 정시 실황과 최신 공개 단기예보 조회. 실황 `observed_at`은 응답의 `baseDate/baseTime`, 예보 `issued_at`은 발표 시각, `items[].forecast_at`은 대상 시각. 예보 조회만 실패하면 실황과 예보의 오류를 함께 반환. |
| A26 `/{festival_id}/transit` | `TRANSIT_PROVIDER=real` | `facilities`의 역·정류장을 요청 반경으로 걸러 거리순 최대 10곳 선택. 서울 지하철, 서울시 버스, 서울 밖 TAGO. 서울 밖 지하철은 `unsupported`, 적재 위치나 실시간 ID가 없으면 `unverified`. 도착이 0건인 확인된 역·정류장은 `ok`와 빈 도착 배열. |
| A29 `/{festival_id}/visit-forecast` | `VISIT_FORECAST_PROVIDER=real` | 등록된 축제-관광지 연결의 장소명과 시군구를 대조. 연결 또는 일치하는 원본 행이 없으면 `forecast.status:unsupported`. KST 오늘부터 요청한 일수의 상대 점수를 표시. 지역 수요는 직전 달 `2101` 지표, 자료가 없으면 null. |

네 엔드포인트의 기본 모드는 `mock`입니다. 실제 모드는 `is_mock:false`를 반환합니다. 축제 조회는 기존 `FESTIVAL_DATA` 설정을 따릅니다. A07의 공지와 A26의 시설 좌표는 실제 모드에서 공개 DB 계정으로 조회합니다.

- 날씨는 실황·예보별 격자 키로 600초 캐시합니다. 실황 시각에서 2시간, 예보 발표 시각에서 6시간을 넘으면 해당 응답을 `stale`로 표시합니다. 구간으로 발표된 강수량은 단일 값으로 변환할 수 없어 null입니다.
- 도착은 역·정류장·서울 버스 노선별로 30초 캐시합니다. 지하철은 공급원 `recptnDt`, 버스는 수신 시각을 사용합니다. 가장 오래된 제공 값이 60초를 넘으면 상위 상태를 `stale`로 표시합니다.
- 서울 버스는 OA-15067의 시설 `ref_code`에 5자리 `ARS_ID`, `source_item_id`에 9자리 `NODE_ID`를 사용합니다. ID로 확인할 수 없는 후보는 이름·노선·방향이 같고 30m 이내인 후보가 하나일 때 연결합니다. 서울 버스 도착의 식별자나 혼잡 의미 코드가 확인되지 않으면 `crowding:unverified`입니다. 타 지역·지하철의 `crowding`은 null입니다.
- TAGO는 시설 `source_item_id`에 `nodeid`를 사용합니다. `ref_code`가 `citycode:nodeid`로 적재되어 있으면 재사용하며, 기존 시설은 TAGO 근접 목록에서 같은 `nodeid`의 도시 코드를 조회합니다.
- A29는 KST 날짜 및 시군구별 메모리 캐시를 사용합니다. `VISIT_FORECAST_STORE=db`를 설정하면 `realtime_snapshots`에서 같은 날의 적재본을 먼저 읽고 수집 성공 시 유형별 원본 필드를 저장합니다. 일일 수집 시 해당 축제의 경로를 호출하면 캐시와 저장 경로를 같이 사용합니다.
- 공급원 시간 제한은 시도당 3초입니다. 시간 초과·일시 HTTP 오류·TAGO 본문 코드 99는 한 번 재시도하며 기본 간격은 1초입니다. 429의 `Retry-After`가 3초를 넘으면 대기 없이 재시도 가능한 오류를 반환합니다. 상한은 실패·재시도도 포함하고 KST 자정에 갱신됩니다.
- 공급원 실패는 HTTP 200과 `unavailable`, `error{code,message,retryable}`로 표시합니다. 전송·HTTP 오류는 `SOURCE_HTTP_ERROR`, 본문·설정·한도 오류는 `SOURCE_RESULT_ERROR`입니다. 외부 URL 및 공급원 오류 원문은 로그에 기록하지 않습니다.

fixture 출처는 [11/19 응답과 11/20 보충 기록](../../../Docs/Step%202/evidence/README.md)입니다. `*_synthetic.json`은 실제 확인이 남은 단기예보·서울 정류소 기준 응답과 실패 또는 불일치 사례입니다.
