# 공통 DB 연결 인계

이 폴더의 연결·세션은 신유빈 담당입니다. 기능별 SQL과 API 응답은 각 기능 담당자가 작성합니다.

- 비회원 조회: FastAPI 라우터에서 `Depends(get_db)`로 `AsyncSession`을 받습니다. DB 역할은 `noldaga_app`이고, `app.user_id`는 설정하지 않습니다.
- 로그인 사용자 조회: JWT를 **검증한 뒤** 얻은 UUID를 `async with user_db_session(user_id)`에 넘깁니다. 사용자 ID는 그 트랜잭션에서만 설정됩니다. 요청값의 사용자 ID를 그대로 넘기지 않습니다.
- 수집·워커: `with service_db_session()`을 사용합니다. DB 역할은 `noldaga_service`입니다. 관리자 API가 이 역할을 쓸 때는 먼저 API에서 권한을 검사합니다.
- 세션 블록이 정상 종료되면 커밋, 예외가 나면 롤백합니다. 세션을 블록 밖으로 전달하지 않습니다.
- 연결 풀에 반납할 때는 롤백 후 `RESET ALL`을 실행하고 확정합니다. DB-09는 일반 세션 설정을 커밋한 뒤 같은 연결을 재사용해 이전 `app.user_id`가 남지 않는지 검증합니다.

2026-11-23 로컬 PostgreSQL 17 일회용 DB의 DB-09 결과: 수정 전 같은 연결에서 이전 ID 잔류, 수정 후 잔류 없음. 실제 DB 세션 테스트 6개 통과. AWS 배포 환경은 아직 검증하지 않았습니다.

`python -m backend.shared.db.migrate`는 `DB_MIGRATION_DSN`의 관리자 계정으로 `Docs/Step 2/db/`의 적용 SQL을 001부터 연속된 번호 순서로 실행합니다. `_down.sql`은 자동 적용하지 않습니다. 이미 적용한 파일은 건너뛰고, 파일명·내용 해시가 적용 이력과 다르거나 번호가 빠지면 중단합니다. 현재 `yubeen`에는 001~011이 있습니다. 011은 병합됐으며, 2026-11-24 유빈님 환경의 일회용 PG17에서 001~011 적용과 재실행 시 11개 건너뛰기를 확인했습니다. `009_precheck.sql`은 009 적용 전 수동 점검 파일이므로 자동 적용에서 제외합니다. 2026-11-24 일회용 PG17에서 001~010 적용·재실행 건너뛰기와 축제 목록·상세 DB 시험 2개를 확인했습니다. 운영 DB 적용 결과는 아닙니다.

백엔드 시험은 저장소 루트에서 `python -m pytest backend/tests -q`로 실행합니다. `backend/`에서 시작하면 `backend` 모듈을 찾지 못하는 DB 시험이 있습니다. 2026-11-24 WSL·일회용 PG17에서 395개 통과, 건너뜀 0개(하위 시험 2개 통과)를 확인했습니다.

현재 모의 서버처럼 `backend/`에서 API를 실행할 때의 비회원 라우터 예시:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db.session import get_db

async def list_festivals(db: AsyncSession = Depends(get_db)):
    # 이 세션에서 필요한 공개 조회 SQL을 실행합니다.
    ...
```

오현님 담당 축제 목록·상세는 `FESTIVAL_DATA=db`일 때 실제 DB를 조회하며, 기본 설정은 모의 응답입니다. 귀갓길 결과 DB 저장과 비회원 경로 조회 토큰 검증은 011과 함께 병합됐습니다. `ROUTE_STORE=db`일 때만 DB를 사용하며 기본값은 memory입니다.

축제 목록·상세의 공개 필드는 `festivals`에서 `noldaga_app`으로 조회할 수 있습니다. 010은 공개 축제의 `festival_sources` 원본 번호 등 필요한 칼럼만 앱 계정에 허용하며, `raw_checksum` 같은 내부 칼럼은 차단합니다. 귀갓길 요청·결과 테이블은 서비스 계정 전용이므로 A05 토큰 확인과 서비스 계정 접근은 011 구현에 포함됐고, 일회용 PG17의 전체 백엔드 시험에서 확인했습니다.

`python -m backend.api.ingestion.tourapi_snapshot`은 2026-11-19 TourAPI 실호출 증빙 **16건(서울 10·부산 6)**을 미리보기만 합니다. 테스트 DB에 기록하려면 `APP_ENV=test`와 DB 서비스 계정 설정 후 `--apply`를 명시합니다. 이 도구는 최신 TourAPI 호출이나 자동 게시를 하지 않으며, 축제는 검토 대기 상태로 저장합니다. 운영 데이터 수집과 게시에는 공급원 키·검증 절차가 별도로 필요합니다.
