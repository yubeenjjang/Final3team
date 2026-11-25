"""A82 비밀번호 변경 (FR-COM22 마이페이지)."""
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from api.auth.state import AuthStateUnavailable, get_auth_state
from api.auth.tokens import AccessClaims, hash_password, password_matches, unauthorized
from api.services.account_deletion import password_mismatch
from shared.db.session import service_db_session

_logger = logging.getLogger(__name__)


def change_password(claims: AccessClaims, current_password: str, new_password: str) -> None:
    owner = {"uid": claims.user_id}
    digest = hash_password(new_password)
    with service_db_session() as db:
        # A33~A35와 같은 행 잠금으로 같은 계정의 토큰 발급·교체와 순서를 맞춥니다.
        account = db.execute(text("""
            SELECT status, password_hash FROM public.users WHERE user_id = :uid FOR UPDATE
        """), owner).one_or_none()
        if account is None or account.status != "active":
            raise unauthorized()
        if not password_matches(current_password, account.password_hash):
            raise password_mismatch()
        db.execute(text("UPDATE public.users SET password_hash = :digest WHERE user_id = :uid"),
                   {**owner, "digest": digest})
        # 모든 기기의 Refresh를 폐기합니다. 다른 기기의 Access는 남은 수명(최대 30분) 뒤 끝납니다.
        db.execute(text("""
            UPDATE public.refresh_tokens SET revoked_at = :now WHERE user_id = :uid AND revoked_at IS NULL
        """), {**owner, "now": datetime.now(timezone.utc)})

    ttl = claims.expires_at - int(datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        try:
            get_auth_state().revoke(claims.jti, ttl)
        except AuthStateUnavailable:
            # 변경은 이미 커밋됐습니다. 현재 Access는 남은 수명 뒤 끝나고 Refresh는 이미 폐기됐습니다.
            _logger.warning("Password changed while the token revocation store was unavailable.")
