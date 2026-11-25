"""DB-20: 워커·내부 작업 코드는 사용자 세션과 앱 계정을 쓰지 않는다 (R04 한태경).

규칙(DB 설계서 3절, D1 문서 4절): Celery 워커·수집·감지·복구처럼 사용자 요청 밖에서 도는 코드는
`noldaga_service`(서비스 세션)만 쓴다. 사용자 세션(`user_db_session`·`get_db`)은 요청한 사용자의
RLS 문맥을 전제로 하므로, 워커가 쓰면 문맥 없이 돌거나 다른 사용자 문맥이 섞일 수 있다.

검사 범위(내부 작업 코드):
- `backend/agents/` 전체 (Celery 앱·작업·에이전트)
- `backend/api/ingestion/`, `backend/api/healing/` (수집·자가 복구)
- 그 밖에 Celery 작업을 정의한 파일(`@shared_task`, `@<앱>.task`, `Celery(`)

DB가 없어도 저장소 코드만 읽어 확인한다. 2026-11-24 기준 Celery 작업 파일은 아직 비어 있어
현재는 수집 코드가 주된 검사 대상이며, 작업이 추가되면 자동으로 범위에 들어온다.
"""

import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
WORKER_DIRS = ("agents", "api/ingestion", "api/healing")
CELERY_TASK = re.compile(r"@(?:shared_task|\w+\.task)\b|\bCelery\(")

# 사용자 요청 전용 세션·엔진과 앱 계정 비밀번호
USER_SESSION = re.compile(r"\b(user_db_session|get_db|create_user_engine|_user_engine)\b")
APP_ACCOUNT = re.compile(r"""["'](DB_USER_PASSWORD|DB_USER_USERNAME)["']""")


def violations(source: str) -> list[str]:
    found = [f"사용자 세션 사용: {m.group(1)}" for m in USER_SESSION.finditer(source)]
    found += [f"앱 계정 환경변수 사용: {m.group(1)}" for m in APP_ACCOUNT.finditer(source)]
    return found


def worker_files() -> list[Path]:
    files = set()
    for d in WORKER_DIRS:
        root = BACKEND / d
        if root.is_dir():
            files.update(p for p in root.rglob("*.py") if "tests" not in p.parts)
    for p in BACKEND.rglob("*.py"):
        if "tests" not in p.relative_to(BACKEND).parts and CELERY_TASK.search(p.read_text(encoding="utf-8", errors="replace")):
            files.add(p)
    return sorted(files)


@pytest.mark.parametrize(("source", "count"), [
    ("from shared.db.session import service_db_session\nwith service_db_session() as s: pass", 0),
    ("from shared.db.session import user_db_session", 1),
    ("async for db in get_db(): ...", 1),
    ("engine = create_user_engine()", 1),
    ("pw = os.environ.get('DB_USER_PASSWORD')", 1),
    ("pw = os.environ.get('DB_SERVICE_PASSWORD')", 0),
    ("def get_db_url(): ...", 0),            # 이름이 비슷한 다른 함수는 잡지 않음
])
def test_db20_detector(source, count):
    assert len(violations(source)) == count


def test_db20_worker_and_job_code_never_use_user_session_or_app_account():
    files = worker_files()
    if not files:
        pytest.skip("내부 작업 코드가 아직 없음")
    problems = [f"{p.relative_to(BACKEND)}: {v}"
                for p in files for v in violations(p.read_text(encoding="utf-8", errors="replace"))]
    assert not problems, "워커·내부 작업이 사용자 세션 또는 앱 계정을 씀:\n" + "\n".join(problems)


def test_db20_jobs_that_touch_db_use_service_account():
    """DB에 접속하는 내부 작업 코드는 서비스 세션 또는 서비스 계정 비밀번호를 쓴다(접속 수단이 확인되는지)."""
    db_touching = []
    for p in worker_files():
        text = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\bcreate_engine\(|\bpsycopg\.connect\(|\bservice_db_session\b|\bSession\(", text):
            db_touching.append((p, text))
    if not db_touching:
        pytest.skip("DB에 접속하는 내부 작업 코드가 아직 없음")
    unclear = [str(p.relative_to(BACKEND)) for p, text in db_touching
               if not re.search(r"\bservice_db_session\b|\bget_service_db\b|DB_SERVICE_PASSWORD|create_service_engine|"
                                r"create_ingestion_engine", text)]
    assert not unclear, f"DB 접속 계정을 확인할 수 없는 내부 작업 파일: {unclear}"
