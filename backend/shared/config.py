"""API와 워커가 함께 사용하는 PostgreSQL 접속 설정."""

import os
from dataclasses import dataclass, field
from typing import Literal


DBRole = Literal["user", "service"]


@dataclass(frozen=True)
class DBSettings:
    host: str
    port: int
    name: str
    user_username: str
    user_password: str = field(repr=False)
    service_username: str
    service_password: str = field(repr=False)

    def credentials(self, role: DBRole) -> tuple[str, str]:
        """요청용과 내부 작업용 DB 계정이 섞이지 않게 선택합니다."""
        if role == "user":
            return self.user_username, self.user_password
        if role == "service":
            return self.service_username, self.service_password
        raise ValueError(f"알 수 없는 DB 역할: {role}")


def load_db_settings() -> DBSettings:
    """환경변수를 읽고, 누락된 설정 이름만 오류에 표시합니다."""
    from dotenv import find_dotenv, load_dotenv

    # 로컬 .env를 읽되, 배포 환경에서 이미 설정한 값은 덮어쓰지 않습니다.
    load_dotenv(find_dotenv(usecwd=True), override=False)
    required = (
        "DB_HOST",
        "DB_NAME",
        "DB_USER_USERNAME",
        "DB_USER_PASSWORD",
        "DB_SERVICE_USERNAME",
        "DB_SERVICE_PASSWORD",
    )
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise ValueError(f"필수 DB 환경변수가 없습니다: {', '.join(missing)}")

    port_text = os.environ.get("DB_PORT", "5432")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("DB_PORT는 1~65535 사이의 숫자여야 합니다") from exc
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT는 1~65535 사이의 숫자여야 합니다")

    return DBSettings(
        host=os.environ["DB_HOST"].strip(),
        port=port,
        name=os.environ["DB_NAME"].strip(),
        user_username=os.environ["DB_USER_USERNAME"].strip(),
        user_password=os.environ["DB_USER_PASSWORD"],
        service_username=os.environ["DB_SERVICE_USERNAME"].strip(),
        service_password=os.environ["DB_SERVICE_PASSWORD"],
    )
