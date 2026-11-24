# 5단계 — TourAPI 분류 반영과 재수집

`SPEC.md`의 I18~I20에 따라 TourAPI `lclsSystm2=EV01`인 축제만 공개한다. Claude가 대상 DB의 014를 적용한 뒤, 기존 전국 수집과 동일한 `--since`·`--until` 범위로 실행한다. 아래는 기존의 `--since 2026-01-01`, 종료일 미지정 수집을 기준으로 한 저장소 루트 명령이다.

마이그레이션 실행기가 `009_precheck.sql`도 009로 세므로, 적용 SQL의 임시 목록에서 해당 사전 검사 파일을 제외한다. 이 방식은 기존 실행기로 SQL 해시와 적용 이력을 검사하고 기록한다. `DB_MIGRATION_DSN`은 관리자 실행 환경에 설정한다.

```bash
uv run --offline --with-requirements backend/api/requirements.txt python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.shared.db import migrate

with TemporaryDirectory(prefix="noldaga-migrations-") as directory:
    staged = Path(directory)
    for path in migrate.SQL_DIR.glob("[0-9][0-9][0-9]_*.sql"):
        if path.name != "009_precheck.sql" and not path.name.endswith("_down.sql"):
            (staged / path.name).symlink_to(path)
    migrate.SQL_DIR = staged
    migrate.main()
PY
```

014 적용을 확인한 뒤 저장소 루트에서 재수집한다.

```bash
cd backend
uv run --offline --with-requirements api/requirements.txt python -m api.ingestion.festivals.collect --since 2026-01-01 --no-detail --db --out /tmp/noldaga-tourapi-reclassify
```

- 수집에는 `DATA_GO_KR_SERVICE_KEY`와 `DB_SERVICE_PASSWORD`를 실행할 셸에 `export`한다. 필요하면 `DB_HOST`(기본 `127.0.0.1`), `DB_PORT`(5432), `DB_NAME`(`noldaga`), `DB_SERVICE_USERNAME`(`noldaga_service`)을 설정한다.
- `--no-detail`로 기존 상세를 보존하면서 목록 분류로 재분류한다. 100건마다 목록 1회, 상세 0회이며 11/23의 870건 기준 목록 9회다. 실제 건수 및 일시 오류 재시도에 따라 달라진다. 추후 상세 보강은 `--no-detail`을 빼면 신규·수정 건에 대해 상세 2종을 요청한다.
- DB를 쓰지 않는 미리보기는 수집 명령의 `--db`를 빼고 별도 `--out` 경로를 사용한다. 이 경우에도 TourAPI 목록을 호출한다. `--limit N`은 결과 처리 건수를 제한하며 목록은 전체를 요청한다.
- `report.json`에서 `scanned`, `pending`, `issues.not_festival_class`, `db.updated`, `errors`, `calls`를 확인한다. 기존 공개 축제의 공개 중단은 `festival_change_history`의 `source_classification` 이력에서 작업 ID로 확인한다. 범위 밖 또는 목록에 없는 기존 행은 이 실행에서 새 분류를 확인할 수 없다.

오프라인 전체 백엔드 시험은 414개와 하위 시험 2개를 통과했고 20개를 건너뛰었다. 샌드박스에서만 임시 uv 캐시와 이벤트 루프 폴링을 사용했다. Docker SQL 및 일회용 PostgreSQL 연결 시험은 재실행 대기다.
