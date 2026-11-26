# src2 적용 및 검증

1. DB 관리자 연결로 001~026 적용을 확인하고 [027_src2.sql](../../../Docs/Step%202/db/027_src2.sql)을 파일 단위 트랜잭션으로 적용한다.
2. 예약 실행기의 환경에서 `SEOUL_CULTURE_ENABLED=true`와 서울시 키를 설정한다. 기존 `api.jobs.scheduler`가 같은 축제 advisory lock과 작업별 성공 회차를 사용한다. 페이지·저장 실패는 재실행 대상으로 남기고, 목록을 모두 읽고 개별 행을 제외한 회차는 A23에 부분 성공으로 기록한다.
3. A23의 `source_id=seoul_culture`로 수집 집계와 날짜 오류를 확인하고 A24에서 격리·충돌 건을 처리한다. A02·A03에서 TourAPI 출처·원본 번호와 보강 필드를 확인한다.
4. [시험 실행기](../../../Docs/Step%202/db/run_tests.sh)는 027 적용·되돌리기·재적용과 RLS를 확인한다. 027까지 적용한 일회용 DB의 `TEST_DB_URL` 및 공개 조회용 `TEST_DB_APP_URL`을 지정하면 `backend/tests/ingestion/test_seoul_culture_db.py`로 병합·격리·잠금·동시성·멱등 및 응답 계약을 시험한다.
5. 되돌릴 때는 서울시 예약 작업을 비활성화하고 [027_src2_down.sql](../../../Docs/Step%202/db/027_src2_down.sql)을 적용한다. 이미 수집한 원본 연결과 검토·보강 이력은 보존한다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```
