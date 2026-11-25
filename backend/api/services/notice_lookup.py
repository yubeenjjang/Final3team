import os

from api.auth.tokens import uses_auth_db
from api.mocks import notices as mock_notices
from api.repositories.notices import postgres_store
from api.services.notices import ControlReader


def uses_notice_db() -> bool:
    return uses_auth_db() or os.environ.get("NOTICES_PROVIDER") == "real"


def control_reader() -> ControlReader:
    return postgres_store if uses_notice_db() else mock_notices.memory_store
