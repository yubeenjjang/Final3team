# info2 실행 및 확인

## 오프라인

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```

돌발 XML 시험은 11/19 [UTIC·TOPIS 증빙](../../../Docs/Step%202/evidence/README.md)에서 확인한 필드, 공공데이터포털 합성 응답, 시간·좌표를 바꾼 합성 TOPIS를 사용합니다. 동시 요청과 공급원별 60초 TTL, 오류 응답, 키 로그 차단을 확인합니다. 001~021을 적용한 일회용 DB에 `TEST_DB_URL`을 설정하면 두 API의 비공개·EV02 축제 차단과 공개 축제 동시 조회를 시험합니다. 앱 역할 접속을 별도로 쓰면 `TEST_DB_APP_URL`도 주입합니다.

## 허용된 네트워크에서 공급원 확인

1. 공공데이터포털에서 승인된 경찰청 서비스의 정확한 오퍼레이션 URL을 `POLICE_INCIDENT_API_URL`에 설정하고 비밀 환경으로 `DATA_GO_KR_SERVICE_KEY`를 주입합니다. 주소는 `https://apis.data.go.kr` 아래 경로입니다. 로컬 실호출 증빙은 UTIC `imsOpenData.do`입니다. 별도 포털 오퍼레이션의 주소·페이지 조건·응답 외피는 공급원에서 확인합니다.
2. `TRAFFIC_INCIDENT_PROVIDER=real`로 서울 및 서울 밖의 공개 축제를 조회합니다. 서울에 `SEOUL_OPEN_API_KEY`를 주입하면 TOPIS도 검증할 수 있습니다. UTIC는 기본 꺼짐이고, 학원 허용망에서만 `UTIC_ENABLED=true`와 `UTIC_API_KEY`를 주입합니다. 공급원별 보호 한도는 `POLICE_INCIDENT_DAILY_LIMIT`, `SEOUL_TOPIS_DAILY_LIMIT`, `UTIC_DAILY_LIMIT`로 설정할 수 있습니다. 기본값 2,880회는 60초 주기에서 분당 최초 호출 및 1회 재시도를 허용하는 로컬 보호값입니다.
3. 서울빛초롱축제 장소에 대응하는 관광공사 원본 전체 페이지에서 `tAtsNm`과 두 지역 코드를 대조합니다. 축제 장소와 일치하는 행을 확인하면 팀 검토 후 승인 행을 기록합니다. 이후 `VISIT_FORECAST_PROVIDER=real`과 `VISIT_FORECAST_MAPPING_FILE`을 사용해 일별 상대 점수·지역 수요를 확인합니다.
