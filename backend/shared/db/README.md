# 공통 DB 연결 인계

이 폴더의 연결·세션은 신유빈 담당입니다. 기능별 SQL과 API 응답은 각 기능 담당자가 작성합니다.

- 비회원 조회: FastAPI 라우터에서 `Depends(get_db)`로 `AsyncSession`을 받습니다. DB 역할은 `noldaga_app`이고, `app.user_id`는 설정하지 않습니다.
- 로그인 사용자 조회: JWT를 **검증한 뒤** 얻은 UUID를 `async with user_db_session(user_id)`에 넘깁니다. 사용자 ID는 그 트랜잭션에서만 설정됩니다. 요청값의 사용자 ID를 그대로 넘기지 않습니다.
- 수집·워커: `with service_db_session()`을 사용합니다. DB 역할은 `noldaga_service`입니다. 관리자 API가 이 역할을 쓸 때는 먼저 API에서 권한을 검사합니다.
- 세션 블록이 정상 종료되면 커밋, 예외가 나면 롤백합니다. 세션을 블록 밖으로 전달하지 않습니다.

현재 모의 서버처럼 `backend/`에서 API를 실행할 때의 비회원 라우터 예시:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db.session import get_db

async def list_festivals(db: AsyncSession = Depends(get_db)):
    # 이 세션에서 필요한 공개 조회 SQL을 실행합니다.
    ...
```

오현님 담당 축제 목록·상세 및 귀갓길 라우터는 아직 모의 데이터를 반환합니다. 실제 DB 전환 시 응답 계약은 `Docs/Step 2/API_설계문서.md`를 기준으로 유지하고, 비회원 경로 조회의 `route_access_token` 검증은 기능 코드에서 수행해야 합니다.

축제 목록·상세의 공개 필드는 `festivals`에서 `noldaga_app`으로 조회할 수 있습니다. 다만 A03의 `source_ref`에 필요한 `festival_sources`는 DB 설계상 `noldaga_service` 전용입니다. **한 요청에서 두 역할을 섞지 않는 규칙**과 응답 계약을 함께 만족시키는 방법은 오현님과 정해야 합니다. 귀갓길 요청·결과 테이블도 서비스 계정 전용이므로, A05의 토큰 확인과 서비스 계정 접근은 기능 담당자가 한 흐름으로 설계해야 합니다. 현재 모의 라우터를 이 문서만 보고 실제 DB 라우터로 바꾸지 않습니다.

`python -m backend.api.ingestion.tourapi_snapshot`은 2026-11-19 TourAPI 실호출 증빙 **16건(서울 10·부산 6)**을 미리보기만 합니다. 테스트 DB에 기록하려면 `APP_ENV=test`와 DB 서비스 계정 설정 후 `--apply`를 명시합니다. 이 도구는 최신 TourAPI 호출이나 자동 게시를 하지 않으며, 축제는 검토 대기 상태로 저장합니다. 운영 데이터 수집과 게시에는 공급원 키·검증 절차가 별도로 필요합니다.
