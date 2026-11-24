# 귀가 경로의 서울 버스 차내 혼잡

D-024·D-033에 따라 서울 버스 차내 혼잡은 교통수단 선택에 사용합니다. D-025에 따라 화면에서 고른 후보의 버스 승차 구간만 조회합니다.

## API

- A04가 동기 완료되면 `X-Route-Access-Token` 응답 헤더를 사용합니다. 비동기 접수는 202 본문의 `route_access_token`을 사용합니다. 카카오 경로는 동기 응답의 `unsupported`를 표시합니다.
- 선택 뒤 `GET /api/v1/routes/return/{route_request_id}?candidate_id=c1`을 호출합니다. `X-Route-Access-Token` 요청 헤더는 기존 A05 인증 규칙을 적용합니다. 선택 후보가 없는 완료 요청은 404 `ROUTE_CANDIDATE_NOT_FOUND`를 반환합니다.
- 선택 후보의 `mode_evidence.bus_crowding`은 유효한 관측이 있을 때 `available`, 연결 실패·모호함·공급원 오류일 때 `unknown`, 카카오·버스 구간 없음·서울 범위 밖일 때 `unsupported`를 반환합니다. `legs[].leg_index`는 해당 경로의 구간 순서(0부터 시작)입니다. 유효한 도착 정보는 `arrivals[].arrival_order`와 `crowding`으로 표시합니다.

## 매칭과 보관

- 유니코드 정규화와 공백·구두점 제거 후 승차 정류장 이름을 비교합니다. 위경도 간 거리는 30m 이내로 제한합니다. 서울 정류장 조회의 `arsId`로 노선을 확인하고, 같은 노선에서 `staOrd`가 1만큼 증가한 다음 정류장이 TMAP의 다음 정류장과 일치할 때 진행 방향이 확인됩니다. 일치 후보는 한 곳이어야 합니다.
- 서울시 버스도착정보 15000314의 도착 순서별 `rerdie_Div1/2=4`에서 `reride_Num1/2`의 3·4·5만 각각 여유·보통·혼잡으로 표시합니다.
- `BUS_CROWD_PROVIDER` 기본값은 `mock`입니다. `real`은 `DATA_GO_KR_SERVICE_KEY`를 사용하고 버스 구간당 외부 조회의 총 시간을 3초로 제한합니다. 표시용 관측값은 서버 메모리에서 60초 동안 재사용합니다.
- DB 모드에서도 선택 후 조회한 혼잡과 매칭용 좌표는 메모리에서만 사용합니다. 다른 프로세스에서 처리했거나 기존 TMAP 캐시가 만료되어 좌표를 확인할 수 없으면 `unknown`입니다. DB 요청 접근은 011의 조회 토큰이 보호합니다.
