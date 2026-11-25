# UTIC 구현 및 검증

1. 앱 lifespan에서 `UTIC_ENABLED`를 확인하고 프로세스별 메모리 저장소와 갱신 작업을 연결합니다. 요청은 lifespan 상태에서 저장소를 받습니다.
2. UTIC는 공급원 XML·쿼터 처리를 재사용하고 개별 HTTP 제한을 적용해 주기마다 한 번 호출합니다. 저장소 인터페이스를 통해 마지막 성공본을 교체합니다.
3. A28에서 시각이 유효한 보관본을 기존 공급원 결과와 합쳐 반경·유형 필터링과 중복 병합을 적용합니다. 축제의 공개 조회는 기존 EV01·승인·게시 조건을 따릅니다.
4. 합성 UTIC 응답으로 초기 수집 중 TOPIS 조회, 만료 경계, 갱신 실패 후 성공본 유지, 경고 마스킹 및 작업 취소를 시험합니다. `TEST_DB_URL`이 제공되면 기존 `db` 표시 시험에서 공개 RLS와 동시 조회도 확인합니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```
