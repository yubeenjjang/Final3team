import os

from sqlalchemy import URL, Engine, create_engine


class IngestionDBError(RuntimeError):
    pass


def create_ingestion_engine(url: str | URL | None = None) -> Engine:
    if url is None:
        password = os.environ.get("DB_SERVICE_PASSWORD")
        if not password:
            raise IngestionDBError("DB_SERVICE_PASSWORD를 설정해 주세요.")
        try:
            port = int(os.environ.get("DB_PORT", "5432"))
        except ValueError:
            raise IngestionDBError("DB_PORT는 숫자여야 합니다.") from None
        if not 1 <= port <= 65535:
            raise IngestionDBError("DB_PORT는 1부터 65535 사이여야 합니다.")
        url = URL.create(
            "postgresql+psycopg",
            username="noldaga_service",
            password=password,
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=port,
            database=os.environ.get("DB_NAME", "noldaga"),
        )
    return create_engine(url, hide_parameters=True)
