# 공식 공지 구현 및 검증 절차

1. `AUTH_PROVIDER=db`는 검증된 JWT `sub`로 공통 사용자 세션을 열고 본인 프로필 역할을 확인합니다. 공지 쓰기와 감사 기록은 서버 계정의 한 트랜잭션에서 처리하고, 검토 시 공지 행을 잠급니다. 기본 모의 모드는 기존 모의 운영자 인증과 잠금 기반 공지 저장소를 사용합니다.
2. [023_notice.sql](../../../Docs/Step%202/db/023_notice.sql)이 수동 종료와 효력 이력을 추가합니다. DB 통제 버전은 해당 축제와 공통 범위에 대해 현재까지 도달한 변경 건수입니다. 예정 시각의 전이도 미리 기록하기 때문에 스케줄러 없이 효력 경계에서 결과가 바뀝니다. DB 캐시는 다음 전이 시각까지만 유효하며, 메모리 캐시는 버전이 포함된 키로 조회합니다.
3. A07은 앱 역할의 공개 RLS를 통과한 승인 공지에 날짜·종류 필터를 적용합니다. 경로 서비스는 `ControlReader`로 버전과 활성 통제 제목을 읽습니다. DB에 저장하는 TMAP 요약의 근거에는 생성 당시 버전을 기록합니다. 기본 모의 A07은 예시 공지와 메모리 관리자 공지를 함께 제공합니다.
4. 프로젝트 루트에서 전체 오프라인 시험을 실행합니다.

   ```bash
   uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
   ```

5. 001~022를 적용한 일회용 PostgreSQL에서 `TEST_DB_URL`과 필요 시 `TEST_DB_APP_URL`을 지정해 `backend/tests/api/test_notice_db.py`를 실행합니다. DB 표시 시험은 실제 JWT와 RLS, 동시 승인, 효력 전이, 이력을 확인합니다. 동시성 검증으로 커밋한 이력은 일회용 DB의 수명으로 정리합니다. [run_tests.sh](../../../Docs/Step%202/db/run_tests.sh)의 022 구간은 적용·되돌리기·재적용과 SQL 권한 검증을 실행합니다. 종료 데이터가 생긴 DB에서는 이력을 보존하기 위해 022 되돌리기가 중단됩니다.
