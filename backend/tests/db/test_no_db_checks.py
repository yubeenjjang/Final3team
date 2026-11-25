"""DB 없이 돌리는 연결·비밀값 검사 (R04 한태경).

검증 항목 문서의 DB-08, DB-18, SEC-01, SEC-03을 시험으로 고정한다.
- DB-08·SEC-01: 저장소 파일만 본다. 지금 바로 실행된다.
- DB-18·SEC-03: `backend/shared/config.py`의 `DBSettings`(yubeen 브랜치)가 main에 들어오기 전에는 건너뛴다.

실행 위치(저장소 루트 / backend/)와 관계없이 돌도록 경로를 직접 잡는다.
비밀번호 자리에는 가짜 표시값만 쓴다.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "backend"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FAKE_USER_PW = "fake-user-pw-7f3a9c"
FAKE_SERVICE_PW = "fake-service-pw-2b8d41"


# ---------------------------------------------------------------------------
# DB-08: 사용자 ID는 트랜잭션 안에서만 설정한다 (LOCAL 없는 SET 금지)
# ---------------------------------------------------------------------------

# LOCAL·트랜잭션 한정이 아닌 설정. `SET LOCAL app.user_id`는 허용한다.
_SESSION_SET = re.compile(r"\bSET\s+(?:SESSION\s+)?app\.user_id\b", re.IGNORECASE)
_SET_CONFIG = re.compile(r"set_config\(\s*['\"]app\.user_id['\"]\s*,(?P<rest>[^)]*)\)", re.IGNORECASE)


def find_user_id_leaks(source: str) -> list[str]:
    """사용자 ID를 세션 전체에 남길 수 있는 문장을 찾는다."""
    found = [m.group(0) for m in _SESSION_SET.finditer(source)]
    for m in _SET_CONFIG.finditer(source):
        third = m.group("rest").split(",")[-1].strip().lower()
        if third != "true":  # 세 번째 인자가 true(트랜잭션 한정)가 아니면 위험
            found.append(m.group(0))
    return found


@pytest.mark.parametrize(
    ("source", "leaks"),
    [
        ("SELECT set_config('app.user_id', :user_id, true)", 0),
        ("SET LOCAL app.user_id = 'x'", 0),
        ("SET app.user_id = 'x'", 1),
        ("set session app.user_id = 'x'", 1),
        ("SELECT set_config('app.user_id', :u, false)", 1),
        ("SELECT set_config('app.user_id', :u, :local)", 1),  # 값이 바뀔 수 있는 인자도 막는다
    ],
)
def test_db08_detector_catches_session_wide_user_id(source: str, leaks: int) -> None:
    """검사기 자체가 위험한 문장과 안전한 문장을 구분하는지 먼저 확인한다."""
    assert len(find_user_id_leaks(source)) == leaks


def test_db08_app_code_sets_user_id_only_per_transaction() -> None:
    """앱 코드(시험 폴더 제외) 어디에도 LOCAL 없는 사용자 ID 설정이 없어야 한다."""
    problems = []
    for path in sorted(BACKEND.rglob("*.py")):
        if "tests" in path.relative_to(BACKEND).parts:
            continue
        for leak in find_user_id_leaks(path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(REPO)}: {leak}")
    assert not problems, "트랜잭션 밖까지 남는 사용자 ID 설정:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# SEC-01: 실제 값이 든 .env 파일은 Git에 올라가지 않는다
# ---------------------------------------------------------------------------

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


needs_git = pytest.mark.skipif(
    shutil.which("git") is None or _git("rev-parse", "--git-dir").returncode != 0,
    reason="git 저장소 안에서만 확인할 수 있다",
)


@needs_git
@pytest.mark.parametrize("path", [".env", "backend/.env", ".env.local", "frontend/.env.local", "backend/api/.env.prod"])
def test_sec01_env_files_are_ignored(path: str) -> None:
    assert _git("check-ignore", "-q", "--no-index", path).returncode == 0, f"{path}가 Git 제외 대상이 아님"


@needs_git
def test_sec01_example_files_stay_tracked() -> None:
    """변수 이름만 적는 예시 파일(저장소에 있는 것 전부)은 제외 규칙에 걸리면 안 된다.

    걸리면 내용을 고쳐도 다음 커밋에 빠질 수 있다. 하위 폴더 .gitignore의 예외 규칙까지 반영해 확인한다.
    """
    examples = [p for p in _git("ls-files").stdout.splitlines() if re.search(r"(^|/)\.env[^/]*\.example$", p)]
    assert ".env.example" in examples
    ignored = [p for p in examples if _git("check-ignore", "-q", "--no-index", p).returncode == 0]
    assert not ignored, f"제외 규칙에 걸린 예시 파일: {ignored}"


@needs_git
def test_sec01_no_real_env_file_is_committed() -> None:
    tracked = _git("ls-files").stdout.splitlines()
    env_files = [p for p in tracked if re.search(r"(^|/)\.env(\.|$)", p) and not p.endswith(".example")]
    assert not env_files, f"Git에 올라간 env 파일: {env_files}"


# ---------------------------------------------------------------------------
# DB-18·SEC-03: 설정 객체 (yubeen 브랜치 DBSettings가 main에 들어온 뒤 실행)
# ---------------------------------------------------------------------------

def _config_module():
    try:
        from backend.shared import config
    except ImportError as exc:  # 의존성(python-dotenv 등)이 없는 환경
        pytest.skip(f"DB 설정 모듈을 불러올 수 없음: {exc}")
    if not hasattr(config, "DBSettings") or not hasattr(config, "load_db_settings"):
        pytest.skip("DBSettings가 아직 main에 없음 (yubeen 브랜치 병합 전)")
    return config


def _settings():
    return _config_module().DBSettings(
        host="db.invalid", port=5432, name="noldaga",
        user_username="noldaga_app", user_password=FAKE_USER_PW,
        service_username="noldaga_service", service_password=FAKE_SERVICE_PW,
    )


@pytest.fixture
def fake_db_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    """실제 .env를 읽지 않도록 빈 폴더에서, 가짜 값만 넣는다."""
    monkeypatch.chdir(tmp_path)
    values = {
        "DB_HOST": "db.invalid", "DB_PORT": "5432", "DB_NAME": "noldaga",
        "DB_USER_USERNAME": "noldaga_app", "DB_USER_PASSWORD": FAKE_USER_PW,
        "DB_SERVICE_USERNAME": "noldaga_service", "DB_SERVICE_PASSWORD": FAKE_SERVICE_PW,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_db18_each_role_gets_only_its_own_account() -> None:
    settings = _settings()
    assert settings.credentials("user") == ("noldaga_app", FAKE_USER_PW)
    assert settings.credentials("service") == ("noldaga_service", FAKE_SERVICE_PW)


@pytest.mark.parametrize("role", ["admin", "USER", "", None])
def test_db18_unknown_role_is_rejected(role) -> None:
    with pytest.raises(ValueError):
        _settings().credentials(role)


def test_db18_env_loading_keeps_accounts_apart(fake_db_env) -> None:
    settings = _config_module().load_db_settings()
    assert settings.credentials("user") == ("noldaga_app", FAKE_USER_PW)
    assert settings.credentials("service") == ("noldaga_service", FAKE_SERVICE_PW)


def test_sec03_settings_repr_hides_passwords() -> None:
    settings = _settings()
    for text in (repr(settings), str(settings)):
        assert FAKE_USER_PW not in text and FAKE_SERVICE_PW not in text


def test_sec03_missing_setting_error_shows_names_only(fake_db_env) -> None:
    fake_db_env.delenv("DB_USER_PASSWORD")
    with pytest.raises(ValueError) as caught:
        _config_module().load_db_settings()
    message = str(caught.value)
    assert "DB_USER_PASSWORD" in message
    assert FAKE_SERVICE_PW not in message


def test_sec03_bad_port_error_hides_passwords(fake_db_env) -> None:
    fake_db_env.setenv("DB_PORT", "not-a-port")
    with pytest.raises(ValueError) as caught:
        _config_module().load_db_settings()
    assert FAKE_USER_PW not in str(caught.value) and FAKE_SERVICE_PW not in str(caught.value)


def test_sec03_connection_url_masks_password() -> None:
    """접속 주소를 로그에 찍어도 비밀번호는 가려져야 한다 (SQLAlchemy URL 표시 방식 확인)."""
    pytest.importorskip("sqlalchemy")
    connection = pytest.importorskip("backend.shared.db.connection")
    if not hasattr(connection, "_connection_url"):
        pytest.skip("연결 코드가 아직 main에 없음 (yubeen 브랜치 병합 전)")
    for role in ("user", "service"):
        url = connection._connection_url(_settings(), role)
        for text in (str(url), repr(url)):
            assert FAKE_USER_PW not in text and FAKE_SERVICE_PW not in text
