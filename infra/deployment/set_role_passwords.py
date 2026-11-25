# W64 초안: 'DB 계정 비밀번호 설정 절차 v2'(11/23, 팀장 1차 검토 반영)의 3-3 스크립트. 저장소 위치·확정은 팀장 결정 대기.
"""noldaga_app·noldaga_service 비밀번호를 SCRAM 검증값으로 설정합니다. 값은 출력하지 않습니다.

.env를 자동으로 읽고(이미 설정된 환경변수가 우선), 값이 비어 있는 항목은 이름만 알려 주고 멈춥니다.
평문 비밀번호는 SQL 문장에 넣지 않으므로 DB 로그 설정과 관계없이 로그에 남지 않습니다.
"""

import os

import psycopg
from dotenv import find_dotenv, load_dotenv
from psycopg import sql

REQUIRED = ("DB_MIGRATION_DSN", "DB_USER_USERNAME", "DB_USER_PASSWORD", "DB_SERVICE_USERNAME", "DB_SERVICE_PASSWORD")


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True), override=False)
    empty = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if empty:
        raise SystemExit(f"값이 없거나 비어 있는 항목: {', '.join(empty)} (fill_env_secrets.py로 채운 뒤 다시 실행)")

    roles = (
        (os.environ["DB_USER_USERNAME"].strip(), os.environ["DB_USER_PASSWORD"]),
        (os.environ["DB_SERVICE_USERNAME"].strip(), os.environ["DB_SERVICE_PASSWORD"]),
    )
    try:
        with psycopg.connect(os.environ["DB_MIGRATION_DSN"].strip(), autocommit=True) as conn:
            for role, password in roles:
                verifier = conn.pgconn.encrypt_password(password.encode(), role.encode(), b"scram-sha-256").decode()
                conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role), sql.Literal(verifier)))
    except psycopg.OperationalError as exc:
        raise SystemExit(f"관리자 계정(DB_MIGRATION_DSN)으로 접속하지 못했습니다: {exc}") from None
    except psycopg.errors.UndefinedObject as exc:
        raise SystemExit(f"계정이 없습니다. 마이그레이션(001)을 먼저 적용하세요: {exc}") from None
    print(f"설정한 계정: {', '.join(role for role, _ in roles)} (값은 출력하지 않음)")


if __name__ == "__main__":
    main()
