# 중간 발표 핵심 동선: 축제 찾기 → 상세 → 귀가 → 결과

기준: `yubeen`, 2026-11-25. W56 시연 범위는 A02·A03·A04·A05다. W90 시설 위치, A26 도착, W49/50 자동 복구는 이 동선의 선행 조건이 아니다.

## API 연결 계약

1. `GET /api/v1/festivals?q=<검색어>`에서 공개 축제 목록을 받는다. 실제 데이터 시연은 `FESTIVAL_DATA=db`와 공개 상태·좌표가 검증된 축제 1건 이상이 필요하다.
2. 사용자가 고른 `items[].festival_id`를 **그대로** `GET /api/v1/festivals/{festival_id}`에 사용한다. 상세의 이름·장소·좌표를 보여 주고, 좌표가 없으면 귀가 요청 버튼 대신 위치 확인 불가를 안내한다.
3. `POST /api/v1/routes/return`에 같은 `festival_id`, 고유 `request_id`, 사용자가 입력한 `destination:{"query":"서울역"}`를 보낸다. 200 동기 완료와 202 접수를 모두 처리한다. 200이면 경로 후보·공급원·조회 시각을 표시한다.
4. 202의 `status_url`을 주기적으로 `GET`하고, 202 본문의 `route_access_token`을 `X-Route-Access-Token` 헤더에 넣는다. `queued`·`processing`은 진행 상태, `ready`는 유효 후보·출처·시각, `unavailable`·`rejected`·`timed_out`은 사유와 재시도 가능 여부를 표시한다. 토큰은 화면·로그에 출력하거나 다른 사용자에게 전달하지 않는다.
5. 시연 중 요청마다 모의/실제 배지를 응답의 `is_mock` 또는 `X-Mock`으로 확인한다. `FESTIVAL_DATA=db`만으로 경로까지 실제가 되지 않는다. 경로의 `ROUTE_PROVIDER=real`은 TMAP/카카오 키·호출 한도와 DB 경로 저장 설정을 확인한 뒤 별도로 켠다. 외부 공급원 부하 시험은 하지 않는다.

## 확인 결과와 남은 인계

- A02/A03 구현 및 W100 축제 로컬 적재 검증 기록이 있다. A04/A05 구현과 실제 TMAP 기본 흐름 보고가 있다.
- `backend/tests/integration/test_screen_flows.py::test_midterm_search_detail_return_and_result`는 일회용 DB의 공개 축제를 검색·상세 조회한 뒤 같은 ID로 **모의 공급원** 귀가 결과까지 잇는다. 실제 외부 공급원 성공을 증명하는 시험은 아니다.
- `backend/tests/api/test_midterm_core_flow.py`의 모의 4단계 연속 시험은 Python 3.14 Docker에서 **1 passed**. 202 대기 응답에는 `festival_id`가 없고, `ready` 결과에서 동일 ID와 출발 좌표를 확인한다.
- 2026-11-25 최신 `yubeen`에서 별도 Docker 네트워크의 일회용 PostgreSQL 17+pgvector에 SQL **001~028**을 적용했다. 앱·서비스 역할 비밀번호를 설정한 뒤 `test_midterm_search_detail_return_and_result` **1 passed**(DB 공개 축제 A02→A03, 모의 경로 A04→A05), `test_P18_db_a02_a03_a04_a05_status_and_expiry` **1 passed**(DB 경로 저장·A05 조회, 토큰 검증·만료)였다. 시험 컨테이너와 네트워크는 종료 후 삭제했다. 두 시험 모두 실제 TMAP 호출 결과를 증명하지 않는다.
- 발표용 화면 W31(검색·상세)과 W38(목적지·상태·결과)은 R05/R01 담당으로 아직 통합 검증 기록이 없다. 그 두 화면에서 위 계약과 오류 표시를 확인해야 발표 동선이 완성된다.
- 중간 시연 W56에는 동일 축제 ID의 검색→상세→귀가→결과 1회, 좌표 없는 축제 또는 조회 불가 1회, 모의/실제 구분과 출처·시각을 기록한다. 실제 화면 리허설은 W58에서 한다.
