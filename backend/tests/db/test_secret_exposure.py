"""비밀값이 커밋 기록·접속 오류·DB 로그에 남지 않는지 (R04 한태경, 검증 항목 SEC-02·04·06).

- SEC-02: git 전체 기록(모든 브랜치)에 비밀값이 커밋됐는지. 값은 출력하지 않고 커밋·파일·규칙만 알린다.
  - 형태 검사(항상 실행): 접속 주소 안 비밀번호, 설정 파일의 비밀 변수 값, 공급원 키 형태
  - 실제 값 대조(`SEC_SCAN_REAL_VALUES=1`일 때만): 로컬 환경의 실제 비밀값이 기록에 그대로 있는지
- SEC-04: DB 접속 실패 오류·예외 출력·로그에 비밀번호가 없는지. DB가 없어도 되는 시험과
  `DB_LIVE_TEST=1`이 필요한 시험(틀린 비밀번호로 실제 서버에 거절당하기)이 있다.
- SEC-06: 비밀번호 설정 절차(클라이언트 SCRAM 검증값 전송)가 DDL 기록을 켠 DB 로그에도 평문을 남기지 않는지.
  `DB_LIVE_TEST=1`과 `DB_TEST_CONTAINER`(일회용 Docker 컨테이너)가 필요하다. 시험용 계정을 만들었다 지운다.

모든 비밀번호 자리에는 실행 때 무작위로 만든 표시값만 쓴다.
"""

import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

LIVE = os.environ.get("DB_LIVE_TEST") == "1"
needs_live = pytest.mark.skipif(not LIVE or not os.environ.get("DB_MIGRATION_DSN"),
                                reason="DB_LIVE_TEST=1과 DB 접속 환경변수가 필요함 (일회용 DB 전용)")
needs_container = pytest.mark.skipif(not os.environ.get("DB_TEST_CONTAINER") or not shutil.which("docker"),
                                     reason="DB 로그를 읽을 일회용 Docker 컨테이너(DB_TEST_CONTAINER)가 필요함")


def marker(tag: str) -> str:
    return f"{tag}{secrets.token_hex(8)}"


# ---------------------------------------------------------------- SEC-02 커밋 기록

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, errors="replace")


needs_git = pytest.mark.skipif(shutil.which("git") is None or _git("rev-parse", "--git-dir").returncode != 0,
                               reason="git 저장소 안에서만 확인할 수 있다")

SECRET_NAME = r"[A-Z0-9_]*(?:PASSWORD|SECRET|API_KEY|APP_KEY|APPKEY|ACCESS_KEY|SERVICE_KEY|PRIVATE_KEY)[A-Z0-9_]*"
CONFIG_FILE = re.compile(r"(^|/)(\.env[^/]*|[^/]+\.(env|ya?ml|sh|toml|ini|cfg|conf|properties)|Dockerfile[^/]*|docker-compose[^/]*)$")
RULES = {
    # 접속 주소 안의 비밀번호: postgresql://user:비밀번호@host
    "접속주소_비밀번호": re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^:/\s@'\"]+:([^@\s/'\"]+)@"),
    # 설정 파일의 NAME=값 (예시 파일은 값이 비어 있거나 자리표시여야 함)
    "설정파일_비밀변수": re.compile(rf"^\s*(?:export\s+)?({SECRET_NAME})\s*[=:]\s*['\"]?([^\s'\"#]+)"),
    # 코드의 비밀 이름에 긴 문자열을 직접 넣은 경우
    "코드_비밀상수": re.compile(rf"\b({SECRET_NAME})\s*[:=]\s*['\"]([A-Za-z0-9_\-+/=%]{{16,}})['\"]"),
    # 공급원 키 형태: TMAP appKey, 카카오 KakaoAK, 공공데이터 serviceKey
    "공급원_키형태": re.compile(r"(?i)(?:appkey['\"]?\s*[:=]\s*['\"]?|KakaoAK\s+|serviceKey=)([A-Za-z0-9%+/=_\-]{20,})"),
}
# 값 전체가 자리표시인 경우만 넘긴다. `{이름}`은 f-string·format 자리표시(고정 문자가 섞이면 잡음).
PLACEHOLDER = re.compile(r"(?i)^(<.*>|\$\{?.*|\{\{.*|\{[A-Za-z_][\w.]*(?:\[[^\]]*\])?(?:![rsa])?(?::[^}]*)?\}|"
                         r"x{3,}|\*{3,}|\.\.\.|changeme|none|null|true|false|test|example)$|"
                         r"(test|fake|dummy|example|sample|placeholder|your[_-]|xxxx|<|\$\{)", re.I)


SELF = "backend/tests/db/test_secret_exposure.py"   # 이 파일은 규칙 확인용 가짜 예시를 일부러 담고 있음


def find_committed_secrets(diff_text: str) -> list[str]:
    """`git log -p` 출력에서 추가된 줄만 보고 (커밋, 파일, 규칙) 목록을 돌려준다. 값은 돌려주지 않는다."""
    found, commit, path = [], "?", "?"
    for line in diff_text.splitlines():
        if line.startswith("@@COMMIT "):
            commit = line.split()[1]
        elif line.startswith("+++ "):
            path = line[6:].strip() if line.startswith("+++ b/") else "?"
        elif line.startswith("+") and not line.startswith("+++") and path != SELF:
            text = line[1:]
            for rule, pattern in RULES.items():
                if rule == "설정파일_비밀변수" and not CONFIG_FILE.search(path):
                    continue
                for m in pattern.finditer(text):
                    value = m.group(m.lastindex)
                    if len(value) >= 6 and not PLACEHOLDER.search(value):
                        found.append(f"{commit} {path} [{rule}]")
    return sorted(set(found))


@pytest.mark.parametrize(("line", "path", "hits"), [
    ("+DB_MIGRATION_DSN=postgresql://postgres:Zk3pQ9wLx2@localhost:5432/noldaga", ".env.example", 1),
    ("+DB_MIGRATION_DSN=postgresql://postgres:<관리자비밀번호>@localhost/noldaga", ".env.example", 0),
    ("+DB_USER_PASSWORD=Zk3pQ9wLx2abc", "deploy/app.env", 1),
    ("+DB_USER_PASSWORD=", ".env.example", 0),
    ("+POSTGRES_PASSWORD=test", "Docs/Step 2/db/run_tests.sh", 0),
    ("+TMAP_APP_KEY = 'aB3dE5gH7jK9mN1pQ3rS5tU7'", "backend/api/settings.py", 1),
    ("+TEST_PASSWORD = 'TESTONLYpassword1234'", "backend/tests/x.py", 0),
    ("+_STARTUP_SECRET = secrets.token_bytes(32)", "backend/api/x.py", 0),
    ("+headers = {'Authorization': 'KakaoAK 0123456789abcdef0123456789abcdef'}", "backend/api/kakao.py", 1),
    ("+_TOKEN_HEADER = 'X-Route-Access-Token'", "backend/tests/x.py", 0),
    # 코드에서 실행 때 채우는 자리표시(f-string·format)는 값이 아니다 (11/24 SEC-05 파일 오탐으로 추가)
    ("+dsn = f\"postgresql://postgres:{migration_pw}@127.0.0.1:9/noldaga\"", "backend/tests/x.py", 0),
    ("+dsn = 'postgresql://{user}:{password}@{host}/{db}'.format(**v)", "backend/api/x.py", 0),
    ("+dsn = f\"postgresql://postgres:Zk3pQ9wLx2{suffix}@db/noldaga\"", "backend/api/x.py", 1),  # 고정 값이 섞이면 잡음
])
def test_sec02_detector_rules(line, path, hits):
    """검사 규칙이 실제 비밀값 형태는 잡고, 자리표시·시험값·코드 표현식은 넘기는지."""
    sample = f"@@COMMIT abc1234\n+++ b/{path}\n{line}\n"
    assert len(find_committed_secrets(sample)) == hits


@needs_git
def test_sec02_no_secret_shaped_values_in_any_commit():
    log = _git("log", "--all", "-p", "--no-color", "-U0", "--format=@@COMMIT %h")
    assert log.returncode == 0
    found = find_committed_secrets(log.stdout)
    assert not found, "비밀값으로 보이는 줄이 커밋됨(값은 출력하지 않음):\n" + "\n".join(found)


def _real_secret_values() -> dict[str, str]:
    """`.env.example`에 이름이 있는 비밀 변수 중, 지금 환경(또는 로컬 .env)에 실제 값이 있는 것."""
    names = set()
    for example in _git("ls-files", "*.env.example", ".env.example").stdout.split():
        for line in (REPO / example).read_text(encoding="utf-8").splitlines():
            m = re.match(rf"\s*({SECRET_NAME}|[A-Z0-9_]*(?:_KEY|_TOKEN|_DSN))\s*=", line)
            if m:
                names.add(m.group(1))
    try:
        from dotenv import dotenv_values
        local = dotenv_values(REPO / ".env") if (REPO / ".env").exists() else {}
    except ImportError:
        local = {}
    values = {n: os.environ.get(n) or local.get(n) or "" for n in names}
    return {n: v for n, v in values.items() if len(v) >= 8}


@needs_git
@pytest.mark.skipif(os.environ.get("SEC_SCAN_REAL_VALUES") != "1", reason="실제 값 대조는 SEC_SCAN_REAL_VALUES=1일 때만")
def test_sec02_real_secret_values_never_committed():
    values = _real_secret_values()
    if not values:
        pytest.skip("대조할 실제 비밀값이 이 환경에 없음")
    log = _git("log", "--all", "-p", "--no-color", "--format=@@COMMIT %h").stdout
    tracked = "".join((REPO / p).read_text(encoding="utf-8", errors="replace")
                      for p in _git("ls-files").stdout.splitlines() if (REPO / p).is_file())
    leaked = sorted(name for name, value in values.items() if value in log or value in tracked)
    assert not leaked, f"실제 값이 커밋 기록·추적 파일에 있음(변수 이름만 표시): {leaked}"


# ---------------------------------------------------------------- SEC-04 접속 실패 오류

def _db_modules():
    try:
        from backend.shared.config import DBSettings
        from backend.shared.db.connection import create_service_engine, create_user_engine
    except ImportError as exc:
        pytest.skip(f"DB 연결 코드를 불러올 수 없음: {exc}")
    return DBSettings, create_user_engine, create_service_engine


def _everything_printed(exc: BaseException) -> str:
    return "\n".join([str(exc), repr(exc), "".join(traceback.format_exception(exc))])


def _settings(DBSettings, host: str, port: int, user_pw: str, service_pw: str):
    return DBSettings(host=host, port=port, name=os.environ.get("DB_NAME", "noldaga"),
                      user_username=os.environ.get("DB_USER_USERNAME", "noldaga_app"), user_password=user_pw,
                      service_username=os.environ.get("DB_SERVICE_USERNAME", "noldaga_service"), service_password=service_pw)


def test_sec04_unreachable_db_error_hides_password(caplog):
    """DB가 꺼져 있을 때(닫힌 포트) 나는 오류·로그에 비밀번호가 없는지. DB 없이 실행된다."""
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("psycopg")
    DBSettings, _, create_service_engine = _db_modules()
    caplog.set_level(logging.DEBUG)
    user_pw, service_pw = marker("secU"), marker("secS")
    engine = create_service_engine(_settings(DBSettings, "127.0.0.1", 9, user_pw, service_pw))
    with pytest.raises(Exception) as caught:
        with engine.connect():
            pass
    engine.dispose()
    shown = _everything_printed(caught.value) + "\n".join(r.getMessage() for r in caplog.records)
    assert user_pw not in shown and service_pw not in shown


def test_sec04_migration_dsn_error_hides_password():
    """관리자 접속 주소(DSN)에 비밀번호가 들어 있어도 접속 실패 메시지에는 나오지 않는지. DB 없이 실행된다."""
    psycopg = pytest.importorskip("psycopg")
    pw = marker("secM")
    with pytest.raises(psycopg.OperationalError) as caught:
        psycopg.connect(f"postgresql://postgres:{pw}@127.0.0.1:9/noldaga", connect_timeout=2)
    assert pw not in _everything_printed(caught.value)


@needs_live
def test_sec04_wrong_password_rejected_by_server_hides_password(caplog):
    """실제 서버가 틀린 비밀번호를 거절할 때의 오류·로그에 그 비밀번호가 없는지."""
    import asyncio
    DBSettings, create_user_engine, _ = _db_modules()
    caplog.set_level(logging.DEBUG)
    wrong_user, wrong_service = marker("wrongU"), marker("wrongS")
    settings = _settings(DBSettings, os.environ["DB_HOST"], int(os.environ.get("DB_PORT", "5432")), wrong_user, wrong_service)

    async def go():
        engine = create_user_engine(settings)
        try:
            async with engine.connect():
                pass
        finally:
            await engine.dispose()

    with pytest.raises(Exception) as caught:
        asyncio.run(go())
    shown = _everything_printed(caught.value) + "\n".join(r.getMessage() for r in caplog.records)
    assert "password authentication failed" in shown   # 정말 서버가 거절한 경우인지
    assert wrong_user not in shown and wrong_service not in shown


# ---------------------------------------------------------------- SEC-06 DB 서버 로그

def _container_logs(since: str) -> str:
    out = subprocess.run(["docker", "logs", "--since", since, os.environ["DB_TEST_CONTAINER"]],
                         capture_output=True, text=True, errors="replace")
    return out.stdout + out.stderr


@needs_live
@needs_container
def test_sec06_scram_password_setting_leaves_no_plaintext_in_db_log():
    psycopg = pytest.importorskip("psycopg")
    from psycopg import sql
    role, pw_scram, pw_wrong, pw_plain = "sec06_probe", marker("scram"), marker("wrong"), marker("plain")
    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 1))
    with psycopg.connect(os.environ["DB_MIGRATION_DSN"], autocommit=True) as admin:
        admin.execute("ALTER SYSTEM SET log_statement = 'ddl'")   # 가장 엄격한 조건: DDL 문장을 모두 기록
        admin.execute("SELECT pg_reload_conf()")
        time.sleep(0.5)
        try:
            admin.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role)))
            # 설정 절차와 같은 방식: 클라이언트에서 SCRAM 검증값을 만들어 그 값만 보낸다
            verifier = admin.pgconn.encrypt_password(pw_scram.encode(), role.encode(), b"scram-sha-256").decode()
            admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role), sql.Literal(verifier)))
            info = admin.info
            with psycopg.connect(host=info.host, port=info.port, dbname=info.dbname, user=role, password=pw_scram) as probe:
                assert probe.execute("SELECT current_user").fetchone()[0] == role
            with pytest.raises(psycopg.OperationalError):
                psycopg.connect(host=info.host, port=info.port, dbname=info.dbname, user=role, password=pw_wrong)
            # 대조군: 평문 ALTER ROLE은 실제로 로그에 남는다(로그 수집이 제대로 되는지 확인)
            admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role), sql.Literal(pw_plain)))
        finally:
            admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
            admin.execute("ALTER SYSTEM RESET log_statement")
            admin.execute("SELECT pg_reload_conf()")
    time.sleep(0.5)
    logs = _container_logs(since)
    assert pw_plain in logs, "대조군 평문이 로그에 없음 → 로그를 제대로 읽지 못해 시험 무효"
    assert pw_scram not in logs, "SCRAM 방식으로 설정한 비밀번호가 DB 로그에 남음"
    assert pw_wrong not in logs, "틀린 비밀번호 로그인 시도가 DB 로그에 비밀번호를 남김"
