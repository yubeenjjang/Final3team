# W82 검증 기록 — 세션 종료·본인 정보 보존/삭제

- **WBS**: W82 「보호 기능 세션 종료·본인 정보 보존/삭제 처리 검증」 (R03 권오현 / R04 한태경, 원래 일정 12/04–12/08)
- **검증일**: 2026-11-25 (일정보다 먼저 실행)
- **기준 커밋**: `ohyun` dbb7037 + 이 기록의 시험 파일 추가
- **범위**: 최소 인증(A32~A35)의 세션 만료·로그아웃, 본인 정보 조회(A11~A13·A36·A37·A78·A79), 탈퇴(A80)와 보존 정리 작업. 독립 계정 관리 기능 확대(비밀번호 찾기 등)는 WBS 정의대로 제외.
- **환경**: 로컬 일회용 PostgreSQL 17 + pgvector 컨테이너(`pgvector/pgvector:pg17`), 마이그레이션 001~028 적용, 계정 `noldaga_app`·`noldaga_service` 분리. AWS가 아니다 — AWS 재시험은 W71(12/23–24)에서 같은 명령으로 다시 실행한다.

## 1. 확인 항목과 결과

| # | 확인 내용 | 근거(설계) | 시험 | 결과 |
|---|---|---|---|---|
| 1 | Access 30분·Refresh 14일 발급, 서명·발급자·만료 검사 | API 1-1절 A33 | `test_auth_db_mode.py::test_access_jwt_signature_issuer_claims_and_expiry` | ✅ |
| 2 | **만료된 Access로 보호 API 호출 → 401** (실제 DB) | 1-1절 | `test_w82_session_privacy_postgres.py::test_w82_logout_expiry_and_disabled_accounts_end_sessions` | ✅ 신규 |
| 3 | **만료 시각 지난 Refresh 갱신 → 401** (실제 DB) | A34 | 같은 시험 | ✅ 신규 |
| 4 | Refresh 교체, 재사용 감지 시 그 계정 Refresh 전부 폐기 | A34 | `test_auth_postgres.py::test_a32_to_a35_postgres_and_rls` | ✅ |
| 5 | **로그아웃한 기기의 Access로 보호 API → 401, 다른 기기는 계속 사용** | A35 "이 기기만 로그아웃" | `test_w82_...::test_w82_logout_expiry_and_disabled_accounts_end_sessions` | ✅ 신규 |
| 6 | **정지(disabled) 계정: 남은 Access·Refresh 거부(401), 로그인 403 `ACCOUNT_DISABLED`, 개인정보는 유지** | 1-1절 "탈퇴·정지 계정", A33 | 같은 시험 | ✅ 신규 |
| 7 | **열린 WebSocket이 로그아웃 뒤 `unsubscribed(deleted)` 후 4403으로 닫힘** | 6-4-5 WS 재인증 | `test_w82_...::test_w82_websocket_closes_after_logout_and_withdrawal` | ✅ 신규 |
| 8 | **열린 WebSocket이 탈퇴 뒤 닫힘** (A80 "열린 WebSocket 종료는 채팅 연결 구현 시 연동") | A80 | 같은 시험 | ✅ 신규 |
| 9 | 본인 정보는 본인만 조회·수정(RLS): 관심 축제·취향·프로필·동행 내역 | A11~A13·A36·A37·A78·A79, DB 7-1 | `test_my_account_postgres.py::test_account_routes_and_withdrawal_with_postgres_rls` | ✅ |
| 10 | 탈퇴 비밀번호 틀림 → 403, 처리 중 오류 → 전부 되돌림(한 트랜잭션) | A80 | 같은 시험 | ✅ |
| 11 | 탈퇴 처리: 이메일·비밀번호 해시 덮어쓰기, 프로필 개인정보 NULL, 관심·취향·알림·Refresh·친구·차단 삭제, 동행 글·신청 취소(정원 반환), 방 퇴장·방장 승계, 챗봇 질문·답변 삭제, 모든 기기 Access·Refresh 거부 | A80, DB 7-0 ② | 같은 시험 | ✅ |
| 12 | **탈퇴자 메시지 본문은 방 보존 정책대로 남고, 다른 참여자에게 작성자 이름 비공개(화면 '알 수 없음')** | DB 7-1 표 "동행 채팅 메시지" | `test_w82_...::test_w82_websocket_closes_after_logout_and_withdrawal` | ✅ 신규 |
| 13 | **탈퇴 뒤 옛 이메일·비밀번호 로그인 → 401, DB에 옛 이메일 없음** | DB 7-0 계정·프로필 | 같은 시험 | ✅ 신규 |
| 14 | 보존 기간 정리: 경로 요청 30일, 채팅(동행 종료 3일·친구 30일), 알림 90일, 체크포인트 7일, 챗봇 30일 | DB 7-0·API 9-1 | `test_jobs_postgres.py` 5개(`daily_route_retention`, `chat_friend_and_notification_cutoffs_and_rls`, `checkpoints_expire`, `daily_retention_cutoffs`, `competing_runners`) | ✅ |
| 15 | 인증 요청 로그에 비밀번호·토큰 원문 없음 | API 18절 | `test_a3_log_redaction.py::test_a3_db_auth_keeps_ids_and_status_without_raw_credentials` | ✅ |

"신규"는 이번 W82에서 추가한 실제 DB 시험이다(`backend/tests/api/test_w82_session_privacy_postgres.py`, 2개).

## 2. 실행 명령과 결과 (2026-11-25)

```bash
# 저장소 루트. 일회용 컨테이너에 001~028 적용 후 계정 비밀번호를 정하고 아래 URL로 실행
TEST_DB_URL=postgresql+psycopg://noldaga_service:<pw>@127.0.0.1:<port>/noldaga \
TEST_DB_APP_URL=postgresql+psycopg://noldaga_app:<pw>@127.0.0.1:<port>/noldaga \
TEST_DB_MIGRATION_URL=postgresql+psycopg://postgres:<pw>@127.0.0.1:<port>/noldaga \
uv run --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt \
  python -m pytest backend/tests -m db -q

# DB 없이 (오프라인)
uv run --offline --with-requirements backend/api/requirements.txt --with-requirements backend/requirements-dev.txt \
  python -m pytest backend/tests -q
```

| 묶음 | 결과 |
|---|---|
| DB 시험 (`-m db`) | **62 통과** (기존 60 + W82 2) |
| 오프라인 시험 | **634 통과**, 66 건너뜀(DB 시험) |
| SQL 실행기 `Docs/Step 2/db/run_tests.sh` | PASS 표기 265줄, FAIL 0 |

컨테이너는 시험 뒤 삭제했다.

## 3. 남은 것 (이번에 하지 않은 이유)

| 항목 | 이유 | 언제·누가 |
|---|---|---|
| 백업 복원 뒤 "탈퇴 목록으로 다시 지움"(DB 7-0 계정·프로필 칸) | 탈퇴 이전 백업을 복원하면 그 사이 탈퇴한 계정이 되살아난다. 탈퇴 목록을 백업과 따로 어디에 둘지(AWS 저장소 등)는 백업·운영 담당(신유빈 W65)과 정해야 해서 지금 만들면 다시 고칠 수 있다 | 팀 결정 뒤 · W65(12/07–10) |
| Redis에 폐기 목록(`revoked:{jti}`) 저장 | 공통 Redis 연결 전이라 API 프로세스 메모리에 둔다. 서버를 여러 개 띄우면 Redis가 필요 | 신유빈 Redis 연결 뒤 |
| AWS에서 같은 시험 다시 실행 | 배포 환경이 아직 없음 | W71(12/23–24) |
