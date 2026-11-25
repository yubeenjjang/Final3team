# info2 구현 명세

## A28 주변 교통 돌발

`GET /api/v1/festivals/{festival_id}/traffic-incidents`는 공개 API입니다. `radius_m`은 500~10000m, 기본 2000m입니다. `type`은 `accident`, `construction`, `event`, `control`을 선택할 수 있습니다. 형식 오류는 422, 공개 축제가 없으면 404입니다. 좌표가 없거나 공급원이 실패하면 HTTP 200의 `unavailable`과 오류 객체를 사용합니다. 정상 응답에 반경 내 돌발이 없으면 `items:[]`입니다.

| 공급원 | 호출 설정 | 확인 근거 |
|---|---|---|
| 경찰청 전국 | `POLICE_INCIDENT_API_URL`, `DATA_GO_KR_SERVICE_KEY` | 전국 경찰청 필드는 아래 UTIC 응답으로 대조했습니다. 공공데이터포털의 별도 HTTPS 호출 주소·응답 외피는 서비스 상세에서 확인해야 합니다. 표준 XML·JSON 응답 외피 및 경찰청 `result/record` XML을 처리합니다. |
| 경찰청 UTIC | `UTIC_ENABLED=true`, `UTIC_API_KEY` | 11/19 [경찰청 응답](../../../Docs/Step%202/evidence/responses/2026-11-19_police-incident.json), [호출 스크립트](../../../Docs/Step%202/evidence/scripts/noldaga_api_test.py). 학원 허용망의 별도 키를 사용합니다. |
| 서울 TOPIS | `SEOUL_OPEN_API_KEY` | 11/19 [AccInfo 응답](../../../Docs/Step%202/evidence/responses/2026-11-19_seoul-accinfo.json). 서울 축제에서 호출합니다. 표본에서 확인한 `A01` 사고와 `A04` 공사 및 명시적인 한글 유형을 사용합니다. `A11` 표본에는 우회와 노면 주의가 함께 있으므로 코드를 통제 유형으로 확정할 수 없습니다. |

- WGS84 기준 축제 반경과 유형으로 거른 뒤 출처 간 중복을 비교합니다. 유형이 같고 도로 링크 또는 정규화한 제목이 일치하는 두 기록의 발생 시각 구간이 겹치며 위치 차가 100m 이내이면 합칩니다. 종료 미상은 확인된 발생 시각만 비교합니다. 합친 건의 출처 우선순위는 공공데이터포털, UTIC, TOPIS 순입니다.
- 경찰청 한글 날짜와 TOPIS의 날짜·시각을 KST ISO 8601로 변환합니다. TOPIS 좌표에 GRS80 중부원점 EPSG:5181을 적용했으며, 11/19 봉은교 표본의 위경도를 PROJ 계산값과 대조했습니다. 확인 가능한 시각이 없는 필드는 null입니다.
- 공급원별 전국·서울 응답을 60초 동안 프로세스 메모리에 캐시합니다. 동일한 공급원 조회가 겹치면 진행 중인 작업을 공유합니다. 수신 시각을 `observed_at`으로 사용하며, 성공 출처 가운데 가장 오래된 수신 시각이 120초를 넘으면 `stale`입니다. TOPIS만 성공하면 서울 범위와 안내 문구를 함께 반환합니다.
- `FestivalSource`의 `SourceCache` 인터페이스를 통해 저장소를 주입할 수 있습니다. A28은 축제 공개 DB 조회에 기존 EV01·승인·게시 RLS를 사용합니다. 돌발 응답은 메모리 캐시로 제공합니다. A29 DB 모드는 기존 `realtime_snapshots`에 적재합니다.

## A29 첫 후보

| 축제 | 장소 근거 | 관광공사 대조 결과 | 승인 |
|---|---|---|---|
| 서울빛초롱축제 `fst_01M835B57450M888RBNEFVRWWA` | 수집 축제 장소는 청계천(청계광장 ~ 삼일교), 주소는 서울 중구 태평로1가 1입니다. [기존 축제 자료](../../api/data/seoul_crowd_mapping.json) | [11/19 종로구 집중률 응답](../../../Docs/Step%202/evidence/responses/2026-11-19_tourist-rate_서울.json)의 `areaCd=11`, `signguCd=11110`은 종로구 조회 조건입니다. 전체 3,390행 중 첫 10행은 가회민화박물관이며, 이 범위에서 청계천·청계광장에 해당하는 `tAtsNm`과 행의 지역 코드를 확인할 수 없습니다. 축제 주소의 중구와 행사 구간도 함께 대조해야 합니다. | 후보·승인 대기 |

기본 [매핑 파일](../../api/data/visit_forecast_mapping.json)은 승인된 행만 담습니다. 확인할 행이 없어 현재 값은 `{}`입니다. 운영 파일은 `VISIT_FORECAST_MAPPING_FILE`로 지정할 수 있습니다. 기존 축제 ID별 객체에 `approved`를 추가합니다. 기존 파일의 연결도 `approved: true`를 명시해야 조회됩니다. `attraction`에는 공급원의 정확한 `tAtsNm`, `area_code`·`district_code`에는 같은 행의 `areaCd`·`signguCd`를 문자열로 기록합니다. 실행 시 축제 장소명과 관광지명 및 응답의 두 코드가 일치해야 예측값을 제공합니다.
