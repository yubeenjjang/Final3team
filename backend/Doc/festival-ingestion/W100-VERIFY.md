# W100 로컬 검증 — 2026-11-25

## 범위와 판정

- 기준: `yubeen`, Python 3.14 Linux Docker, 일회용 PostgreSQL 17 + pgvector, 마이그레이션 001~028. AWS 운영 DB에는 적용하지 않았다.
- TourAPI는 원본 ID와 체크섬으로 업서트한다. 같은 입력의 재수집은 새 축제·변경 이력을 만들지 않는다. 바뀐 필드만 이력에 남기고 관리자 수정값은 충돌 검토로 보낸다.
- 서울시 문화행사는 TourAPI 축제와 제목·기간·좌표를 대조해 보강한다. 확정할 수 없는 중복·신규 행은 공개하지 않고 검토 대기열에 넣는다.
- 현재 수집 응답의 정규화 계약에는 명시적인 공식 취소 신호가 없다. 목록 누락은 취소 확정이 아니므로 공개 보류·관리자 검토로 처리한다. 관리자가 `event_status=cancelled`로 결정한 행은 공급원 변경 재수집 후에도 취소 상태를 유지하고 충돌 제안을 남긴다.
- `scheduler`는 Compose의 `scheduled` 프로필로 선택 기동한다. 매시간 실행하여 한국 시각 06:00 이후 일일 공급원 수집 회차를 검사한다. 성공 회차는 DB에 기록해 재실행을 건너뛰며, 실패한 공급원 회차는 다음 실행에서 재시도한다. 서울시 공급원은 `SEOUL_CULTURE_ENABLED=true`일 때만 실행한다.

## 실행 결과

- 일회용 DB에 001~028 적용, 앱·서비스 계정 설정 성공.
- `backend/tests/ingestion`, `backend/tests/api/test_jobs.py`, `backend/tests/api/test_jobs_postgres.py`: **161 passed, 0 skipped, 1 SQLAlchemy 사용 중단 예정 경고**. 관리자 취소 보존과 두 공급원의 실행 순서·실패 재시도·성공 회차 중복 방지 시험을 포함한다.
- `docker compose -f infra/deployment/compose.yaml --profile scheduled config --quiet`: 필수 비밀번호에 임시 시험값을 넣어 구성 검사 통과.
- 시험용 DB 컨테이너와 네트워크는 검증 후 삭제했다.

## AWS 단계에서 할 일

- 실제 공급원 키·운영 시크릿 설정과 외부 호출 결과 확인, 운영 DB 백업·복원 뒤 수집 재기동 검증, 스케줄러 로그·비용·접근권한 확인은 W65에서 수행한다.
- 공식 공급원에 명시적 취소 신호가 추가되면 정규화 계약과 시험을 먼저 정의한 뒤 자동 취소 판정을 구현한다.
