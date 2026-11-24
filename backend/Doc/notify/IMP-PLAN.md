# notify 구현과 검증

1. PostgreSQL 모드에서는 001~021 뒤에 `022_notify.sql`을 적용합니다. `report_moderation`에 운영 조치와 메모를 보관하고 신고 중복 조회 인덱스를 추가합니다. 022는 기존 행을 보존하며, 조치 이력이 들어간 뒤에는 되돌리기를 차단합니다.
2. A76은 RLS 세션으로 글·메시지·방 대상 권한을 확인합니다. 서비스 트랜잭션에서 현재 참여를 다시 확인하고, 신고자와 대상에 대한 PostgreSQL 트랜잭션 잠금으로 동시에 접수된 요청을 직렬화합니다. Mock은 같은 날짜·대상 기준을 프로세스 메모리에서 잠금으로 적용합니다.
3. A77 mock을 사용할 때는 `MOCK_ADMIN_REPORTS_TOKEN`에 32바이트 이상의 값을 설정하고 Bearer 인증에 사용합니다. Redis 연동 전까지 채팅 WebSocket은 기존 메모리 버스 인터페이스와 주기적 조회를 사용합니다.
4. 90일 알림 삭제는 저장소 루트에서 `PYTHONPATH=backend python -m api.jobs.purge_chat`을 실행합니다. 시간당 실행은 배포 작업에서 연결합니다.
5. 전체 오프라인 회귀 시험은 저장소 루트에서 아래 명령을 실행합니다. PostgreSQL 경로는 마이그레이션을 적용한 일회용 DB의 `TEST_DB_URL`로 `-m db` 시험을 실행합니다. 022 적용·되돌리기·재적용과 감사 권한은 `Docs/Step 2/db/run_tests.sh`에 연결되어 있습니다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
```
