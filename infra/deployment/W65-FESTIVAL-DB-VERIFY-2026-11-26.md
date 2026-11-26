# W65 로컬 축제 DB A02·A03 검증 — 2026-11-26

- 환경: Docker Desktop Linux 엔진, 별도 Compose 프로젝트 `codex-festival-verify`, 일회용 PostgreSQL 17+pgvector와 FastAPI.
- 001~028 마이그레이션과 역할 비밀번호 설정을 마친 뒤 `FESTIVAL_DATA=db`로 API를 기동했다.
- 실제 TourAPI 키·운영 DB·AWS 자원은 사용하지 않았다. 공개 조건을 확인하기 위해 **시험용 축제 행 3건**을 직접 적재했다: 공개 EV01 1건, 공개 대기 EV01 1건, EV03 비축제 1건.

| 확인 | 결과 |
| --- | --- |
| A02 `GET /api/v1/festivals?region=SEOUL` | HTTP 200, `total=1`, `is_mock=false`, `X-Mock` 없음. 공개 EV01 `fst_VERIFYA001`만 목록에 나타남 |
| A03 `GET /api/v1/festivals/fst_VERIFYA001` | HTTP 200, 같은 `festival_id`·이름·위도 37.5759·경도 126.9768, `is_mock=false` |
| 공개 제외 행 A03 조회 | `fst_VERIFYA002`(pending), `fst_VERIFYA003`(EV03) 각각 HTTP 404 `FESTIVAL_NOT_FOUND` |

이는 **데이터가 들어 있는 별도 DB에서 A02 목록 → 같은 ID의 A03 상세**까지 실제 컨테이너 경로로 읽은 증거다. 실제 TourAPI 수집·정기 실행, 실제 축제 전체 데이터, AWS 배포의 검증 결과는 아니다. 시험 뒤 컨테이너·네트워크·DB 볼륨·임시 환경 파일을 정리했다.
