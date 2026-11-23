# SPEC — W89 서울 축제 주변 지역 혼잡 연결

기준은 [API 설계문서 A10](../../../Docs/Step%202/API_설계문서.md)의 A10 절과 `api/schemas/festival_info.py`, `api/services/mock_festival_info.py`의 현재 응답입니다. 2026-11-23 KST 조사 결과입니다.

## 0. 서울시 공급원 조사

| 항목 | 확인 내용 |
|---|---|
| 공급원 | 서울특별시 **서울시 실시간 인구데이터** OA-21778, 서비스 `citydata_ppltn`. 종합 `citydata`(OA-21285)의 인구 부분만 조회할 수 있어 A10에는 OA-21778을 사용합니다. |
| 호출 | `GET http://openapi.seoul.go.kr:8088/***/json/citydata_ppltn/1/1/{area_code}`. 이름 또는 코드 중 하나로 요청합니다. 정식 키의 코드·한글 이름 요청을 확인했습니다. 샘플 키는 광화문·덕수궁에만 쓸 수 있습니다. 서울시는 공식 HTTPS를 제공하지 않는다고 답했습니다. |
| 한 번의 요청 | **장소 1곳**. 공통 오류표의 ‘최대 1,000건’은 요청 행 수 제한입니다. 일부 인자 설명의 116장소 표기는 예전 목록으로, 실제 비교에는 최신 첨부 121곳을 썼습니다. |
| 하루 호출 | 서울시 원천 부서 공식 답변상 **별도 일일 상한 제도 없음**. 과다 호출 시 키 제한이 가능하며, 시간당·과다 판정 임계치 및 한도 전용 본문 코드는 **미확인**입니다. 답변의 하루 2,592회 허용은 문의에 든 9개 장소 사용 사례입니다. 앱 자체 예산은 4절에서 정합니다. |
| 갱신과 시차 | 공식 갱신 주기는 **5분**입니다. `PPLTN_TIME`은 집계 기준 시각이며, 공식 답변에서 제공 시점보다 23~33분 늦는 사례를 안내합니다. 11/23 응답은 약 30~31분 차이였습니다. 보장되는 최대 지연은 **미확인**입니다. |
| 데이터 성격 | 통신사 신호로 추정한 구역 단위 인구입니다. 90일 이하 단기체류 외국인은 실시간 인구 추정에서 제외됩니다. `REPLACE_YN=Y`는 원천·서울시 시스템 오류 등으로 최근 4주 같은 요일·시간대 평균을 제공한다는 뜻입니다. |
| 이용 조건 | 공공누리 1유형입니다. 출처를 밝히면 상업적 이용과 변경이 가능합니다. 화면·문서에 ‘출처 서울특별시 · 2026년 서울시 인구데이터 (OA-21778)’와 데이터셋 링크를 표시합니다. 서울시 답변은 출처 표시를 전제로 자료 보관에 별도 기간 제한을 두지 않는다고 안내합니다. |

공식 출처는 [인구 데이터셋과 첨부 파일](https://data.seoul.go.kr/dataList/OA-21778/A/1/datasetView.do), [OA-21778 API 명세·오류표](https://data.seoul.go.kr/dataList/openApiView.do?infId=OA-21778&srvType=A), [서울시 도시데이터 안내](https://data.seoul.go.kr/dataVisual/seoul/guide.do), [서울 열린데이터광장 운영 답변](https://data.seoul.go.kr/together/notice/inquireView.do?bbsCd=10003&ditcCd=QNA01&seq=1d2186fcde0d53cbbb2814bec743624a), [서울시 저작권 안내](https://data.seoul.go.kr/etc/openInfo.do)입니다.

### 실제 호출 기록과 고정 파일

2026-11-23 15:55~15:56 KST에 정식 키로 5회 조회했습니다.

| 요청 장소 | HTTP · 본문 코드 | 관측 시각(KST) / 품질 | 고정 파일 |
|---|---|---|---|
| `POI009` 광화문·덕수궁 | 200 · `INFO-000` | 15:25 / 대체값 `Y` | `citydata_ppltn_replacement.json` |
| 이름 `여의도한강공원` → `POI105` | 200 · `INFO-000` | 15:25 / 대체값 `Y` | |
| `POI083` DDP | 200 · `INFO-000` | 15:25 / 대체값 `Y` | |
| `POI001` 강남 MICE 관광특구 | 200 · `INFO-000` | 15:25 / 대체값 `Y` | |
| 존재하지 않는 장소 이름 | 200 · `ERROR-500` | | `citydata_ppltn_unknown_area.json` |
| `POI009` 광화문·덕수궁, 11/19 저장소 증빙 | 200 · `INFO-000` | 11/19 16:55 / 관측값 `N` | `citydata_ppltn_observed.json` |

[고정 파일](../../tests/crowd/fixtures/)은 서울특별시의 서울시 실시간 인구데이터를 공공누리 1유형으로 이용했습니다. 해당 응답에서 A10에 쓰는 항목과 결과 코드를 보존했습니다. 성별·연령·상주/비상주 비율 등 미사용 인구 통계 필드는 덜어냈습니다. 11/19 예시는 [기존 실호출 증빙](../../../Docs/Step%202/evidence/responses/2026-11-19_seoul-ppltn_광화문덕수궁.json)에서 가져왔습니다.

## 1. P1 — 공식 구역과 거리

- 11/23 권오현 결정. 강사 11/17의 지원 장소 확인만으로 임의 축제 혼잡과 연결할 수 없다는 피드백을 반영해, 축제 근처 **공식 구역의 집계 혼잡**을 안내합니다.
- `festival_lookup.find_festival`로 공개 축제를 확인합니다. 서울 밖, 좌표 없음, 1,000m 이내 구역 없음은 각각 `outside_seoul`, `missing_coordinates`, `no_nearby_areas` 사유로 `unsupported`를 반환합니다.
- `api/data/seoul_areas.json`의 공식 121개 구역을 순수 파이썬으로 읽습니다. WGS84의 위·경도 좌표를 축제 위치 기준 국소 평면에서 미터로 환산한 뒤 다각형 경계의 선분까지 최단거리를 계산합니다. 구역 안과 경계 위는 0m이며 내부 링의 빈 공간은 경계까지 거리를 계산합니다. JSON의 검증 기록에서 원본 경계와의 오차 상한은 약 3.5m입니다.
- 1,000m를 포함해 필터링하고 거리 오름차순, 동률이면 구역 코드순으로 세 곳까지 선택합니다. 비교는 반올림 전 거리이며 응답의 `distance_m`는 소수점 한 자리까지 제공합니다. 양의 거리는 최소 0.1m로 표시합니다.
- [연결표](mapping_draft.md)와 [JSON 초안](../../api/data/seoul_crowd_mapping.json)은 폐기된 대표 구역 승인 방식의 1단계 참고 자료입니다.

## 2. P2 — 공급원과 유효성

- 선택한 구역별 `AREA_CD`로 `citydata_ppltn`에 요청합니다. 연결·본문 읽기를 포함한 총 제한 시간은 3초입니다. 리다이렉트를 따르지 않으며 프로그램 로그와 응답에서 키를 가립니다.
- 결과 코드는 `RESULT` 객체 또는 최상위 객체에서 `"RESULT.CODE"`를 우선 읽고, 없거나 비어 있으면 `"CODE"`를 읽습니다. 성공 코드 `INFO-000`과 함께 `SeoulRtd.citydata_ppltn`에 요청 구역과 일치하는 결과 1개가 있어야 합니다.
- 필수 문자열·허용 혼잡 등급·0 이상 정수 인구 범위(최소≤최대)·서울 기준 시각 `PPLTN_TIME`·`REPLACE_YN`의 `N`/`Y`를 검증합니다. 미래 기준 시각은 실패입니다.
- HTTP·본문 코드·형식·타임아웃은 해당 구역 `unavailable`과 `SOURCE_RESULT_ERROR`로 처리합니다. 자체 재시도는 없고 키 오류, 키 미설정, 일일 한도 소진은 `retryable:false`입니다.
- `REPLACE_YN=Y`는 최근 4주 같은 요일·시간대 평균입니다. `is_estimate:true`로 반환하고 ‘실시간 자료가 없어 최근 4주 같은 시간대 평균이에요’를 표시합니다.

## 3. P3 — A10 응답

- 기존 `is_mock`, `festival_id`, `status`, `coverage`, `source`, `observed_at`, `notices`, `error`, `areas`를 유지합니다. `coverage.supported`는 지역 지원 여부입니다. `source`는 `seoul_citydata`입니다.
- 실제 모드의 `areas[0]`과 최상위 `observed_at`은 조회에 성공한 가장 가까운 구역으로 채웁니다. 기존 구역 필드를 유지하며 `relation_type`은 0m `contains`, 그 밖은 `adjacent`입니다. 실제 조회의 `forecast`는 빈 배열입니다. `observed_at`은 KST ISO 8601입니다.
- 실제 모드에 `nearby_areas`, `is_estimate`, `unsupported_reason`, `source_url`을 추가합니다. 목록 원소는 `area_code`, `area_name`, `distance_m`, `status`, `data`(기존 구역 모양), `is_estimate`, `error`를 갖습니다. 실패한 구역은 `status:"unavailable"`, `data:null`, `is_estimate:null`과 오류를 갖습니다. 최상위 `is_estimate`는 `areas[0]`에 대응하며 자료가 없으면 `null`입니다.
- `notices`는 ‘축제 근처 지역 혼잡(서울시 실시간 도시데이터)’, 구역명·거리·기준 시각, ‘행사장 안 혼잡과 다를 수 있어요’를 제공합니다. 관측값과 대체값 모두 출처는 ‘출처 서울특별시 · 2026년 서울시 인구데이터 (OA-21778)’이며, 데이터셋 링크는 `source_url`로 제공합니다. 대체 자료의 제목은 ‘축제 근처 지역 혼잡(서울시 4주 평균)’입니다. 오래된 자료에는 경과 안내를 붙입니다.

| 경우 | A10 | Festival Agent 현재 분기 |
|---|---|---|
| 일부 이상 조회에 성공 | 200 `ok` 또는 가장 가까운 성공 자료가 오래됐으면 `stale`. 실패 구역은 목록에 상태 유지 | `answered` |
| 서울 밖, 좌표 없음, 주변에 구역 없음 | 200 `unsupported`, `areas:[]`, `error:null`, `unsupported_reason` | `unsupported` |
| 선택한 모든 구역 조회 실패 | 200 `unavailable`, `areas:[]`, `SOURCE_RESULT_ERROR` | `unavailable` |
| 축제 ID 형식 오류 / 공개 축제 없음 | 422 / 404 `FESTIVAL_NOT_FOUND` | 도구 오류 처리 |

`answered`는 에이전트 결과값이고 `source_error`는 모의 입력 시나리오입니다. 에이전트는 기존 `areas[0]`으로 응답합니다. 거리·여러 구역·대체값 안내를 에이전트 답변에 표시하려면 새 필드나 `notices`를 소비해야 합니다.

## 4. P4 — 캐시와 하루 호출 예산

- 검증한 관측값과 대체값을 구역별 60초 동안 프로세스 메모리에 캐시합니다. 같은 구역의 동시 요청은 합칩니다. 시간 초과와 실패는 캐시하지 않습니다.
- 읽을 때마다 관측 시각을 확인합니다. 공식 갱신은 5분이며 일반적인 자료 시차를 고려해 기준 시각에서 **45분 초과**이면 `stale`입니다. 만료 후 신규 조회가 실패하면 그 구역은 `unavailable`입니다.
- `api/providers/quota.py`의 잠금·원자적 파일 교체·80% 초과 경고를 재사용합니다. `CROWD_SEOUL_DAILY_LIMIT` 기본값은 KST 기준 하루 1,000회입니다. 공급원 호출을 시작할 때 예약하고 실패 호출도 셉니다. 캐시 적중·병합 합류·미지원은 추가 차감 없이 처리합니다. `CROWD_QUOTA_FILE` 기본값은 `./.crowd_quota.json`이며 여러 프로세스는 같은 파일을 공유할 수 있습니다.

## 5. P5 — 모의/실제 전환과 시험

- `CROWD_PROVIDER` 기본값은 `mock`입니다. 기존 응답과 `X-Mock-Scenario`의 `source_error`·`stale`을 유지합니다.
- `real`에서만 서버의 `SEOUL_OPEN_API_KEY`를 읽고 공급원을 호출합니다. 실제 모드 A10은 `is_mock:false`이고 `X-Mock`이 없습니다.
- `tests/crowd/`의 고정 파일·가짜 HTTP·가짜 시각으로 검증하고 `backend/`에서 전체 `python -m pytest`를 실행합니다.
