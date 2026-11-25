# W64 초안: 'DB 계정 비밀번호 설정 절차 v2'의 3-1 스크립트. 저장소 루트에서 실행(python3 infra/deployment/fill_env_secrets.py).
"""로컬 .env에서 비어 있거나 없는 비밀값만 무작위로 채웁니다. 값은 출력하지 않습니다.

- 이미 값이 있는 항목은 건드리지 않습니다(DB를 처음 띄운 뒤 POSTGRES_PASSWORD를 바꾸면 접속이 안 되기 때문).
- `KEY=`, `KEY=""`, `KEY= # 설명`처럼 값이 빈 줄은 그 자리에서 값을 채웁니다.
- DB_MIGRATION_DSN이 비어 있으면 로컬 기본 관리자(postgres)와 POSTGRES_PASSWORD로 만듭니다.
"""

import os
import re
import secrets
from pathlib import Path
from urllib.parse import quote

ENV_PATH = Path(".env")
SECRET_NAMES = ("POSTGRES_PASSWORD", "DB_USER_PASSWORD", "DB_SERVICE_PASSWORD")
LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def parse_value(raw: str) -> str:
    """python-dotenv와 같은 기준으로 값만 꺼냅니다(따옴표, 줄 끝 # 설명)."""
    raw = raw.strip()
    if raw.startswith("#"):  # `KEY= # 설명`은 빈 값
        return ""
    if raw[:1] in {'"', "'"}:
        end = raw.find(raw[0], 1)
        return raw[1:end] if end != -1 else raw[1:]
    return re.split(r"\s+#", raw, maxsplit=1)[0].strip()


def main() -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    index = {}
    for i, line in enumerate(lines):
        match = LINE.match(line)
        if match:
            index[match.group(1)] = i

    def current(name: str) -> str:
        return parse_value(LINE.match(lines[index[name]]).group(2)) if name in index else ""

    def put(name: str, value: str) -> None:
        if name in index:
            lines[index[name]] = f"{name}={value}"
        else:
            index[name] = len(lines)
            lines.append(f"{name}={value}")

    filled = []
    for name in SECRET_NAMES:
        if not current(name):
            put(name, secrets.token_urlsafe(32))
            filled.append(name)

    if not current("DB_MIGRATION_DSN"):
        host = current("DB_HOST") or "localhost"
        port = current("DB_PORT") or "5432"
        db = current("DB_NAME") or "noldaga"
        password = quote(current("POSTGRES_PASSWORD"), safe="")
        put("DB_MIGRATION_DSN", f"postgresql://postgres:{password}@{host}:{port}/{db}")
        filled.append("DB_MIGRATION_DSN")

    # 처음부터 본인만 읽고 쓸 수 있는 권한(600)으로 씁니다.
    fd = os.open(ENV_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")
    os.chmod(ENV_PATH, 0o600)
    print("채운 항목: " + (", ".join(filled) if filled else "없음") + " (값은 출력하지 않음)")


if __name__ == "__main__":
    main()
