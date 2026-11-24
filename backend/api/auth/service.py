import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ulid import ULID

from api.auth.state import (
    AuthStateUnavailable,
    auth_check_unavailable,
    get_auth_state,
    refresh_in_progress,
    refresh_lock,
)
from api.auth.tokens import (
    AccessClaims,
    hash_password,
    issue_access_token,
    password_matches,
    positive_setting,
    refresh_hash,
    unauthorized,
)
from api.errors import ApiError
from api.schemas.auth import LoginRequest, SignupRequest
from shared.db.session import service_db_session

_KST = timezone(timedelta(hours=9))


def _email_taken() -> ApiError:
    return ApiError(409, "EMAIL_ALREADY_EXISTS", "이미 가입한 이메일입니다.")


def signup(request: SignupRequest) -> dict[str, object]:
    user_id = uuid4()
    digest = hash_password(request.password.get_secret_value())
    try:
        with service_db_session() as db:
            # 001의 UNIQUE는 대소문자를 구분하므로 기존 행도 소문자로 비교합니다.
            if db.scalar(text("SELECT EXISTS (SELECT 1 FROM public.users WHERE lower(email) = :email)"),
                         {"email": request.email}):
                raise _email_taken()
            db.execute(text("""
                INSERT INTO public.users (user_id, email, password_hash)
                VALUES (:user_id, :email, :password_hash)
            """), {"user_id": user_id, "email": request.email, "password_hash": digest})
            db.execute(text("""
                INSERT INTO public.profiles (user_id, display_name, birth_year, gender)
                VALUES (:user_id, :display_name, :birth_year, :gender)
            """), {
                "user_id": user_id, "display_name": request.display_name,
                "birth_year": request.birth_year, "gender": request.gender,
            })
    except IntegrityError as error:
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint == "users_email_key":
            raise _email_taken() from None
        if constraint == "uq_profiles_nickname":
            raise ApiError(409, "NICKNAME_TAKEN", "이미 사용 중인 닉네임입니다.") from None
        raise
    return {"user_id": str(user_id), "display_name": request.display_name, "is_mock": False}


def _invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "이메일이나 비밀번호를 확인해 주세요.")


def _account_disabled() -> ApiError:
    return ApiError(403, "ACCOUNT_DISABLED", "사용할 수 없는 계정입니다.")


def login(request: LoginRequest) -> dict[str, object]:
    with service_db_session() as db:
        rows = db.execute(text("""
            SELECT user_id, status, password_hash
            FROM public.users WHERE lower(email) = :email LIMIT 2
        """), {"email": request.email.lower()}).all()
    account = rows[0] if len(rows) == 1 else None
    correct_password = password_matches(
        request.password.get_secret_value(), account.password_hash if account else None,
    )
    if account is None or not correct_password:
        raise _invalid_credentials()
    if account.status != "active":
        raise _account_disabled()

    with service_db_session() as db:
        now = datetime.now(timezone.utc)
        updated = db.execute(text("""
            UPDATE public.users SET last_login_at = :now
            WHERE user_id = :user_id AND status = 'active' AND password_hash = :password_hash
            RETURNING user_id
        """), {"now": now, "user_id": account.user_id, "password_hash": account.password_hash})
        if updated.scalar_one_or_none() is None:
            raise _invalid_credentials()
        return _issue_tokens(db, account.user_id, now)


def _issue_tokens(db: Session, user_id: UUID, now: datetime) -> dict[str, object]:
    profile = db.execute(text("""
        SELECT display_name, role FROM public.profiles WHERE user_id = :user_id
    """), {"user_id": user_id}).one()
    access_duration = positive_setting("ACCESS_JWT_TTL_MIN", 30) * 60
    access = issue_access_token(user_id, profile.role, now, access_duration)
    refresh = secrets.token_urlsafe(32)
    refresh_expires = now + timedelta(days=positive_setting("REFRESH_TTL_DAYS", 14))
    db.execute(text("""
        INSERT INTO public.refresh_tokens (token_id, user_id, token_hash, expires_at)
        VALUES (:token_id, :user_id, :token_hash, :expires_at)
    """), {
        "token_id": f"rt_{ULID()}", "user_id": user_id,
        "token_hash": refresh_hash(refresh), "expires_at": refresh_expires,
    })
    return {
        "access_token": access, "refresh_token": refresh, "token_type": "bearer",
        "expires_in": access_duration, "refresh_expires_at": refresh_expires.astimezone(_KST).isoformat(),
        "user": {"user_id": str(user_id), "display_name": profile.display_name, "role": profile.role},
        "is_mock": False,
    }


def _refresh_invalid() -> ApiError:
    return ApiError(401, "REFRESH_INVALID", "유효한 인증 갱신 토큰을 보내 주세요.")


def _lock_account(db: Session, user_id: UUID) -> str | None:
    # 이 행을 기준으로 같은 계정의 발급·교체·재사용 폐기·로그아웃을 직렬화합니다.
    return db.scalar(text("""
        SELECT status FROM public.users WHERE user_id = :user_id FOR UPDATE
    """), {"user_id": user_id})


def refresh(token: str) -> dict[str, object]:
    digest = refresh_hash(token)
    with service_db_session() as db:
        record = db.execute(text("""
            SELECT token_id, user_id FROM public.refresh_tokens WHERE token_hash = :digest
        """), {"digest": digest}).one_or_none()
    if record is None:
        raise _refresh_invalid()

    with refresh_lock(record.token_id), service_db_session() as db:
        # 프로세스가 다르거나 메모리 잠금 TTL이 지나도 같은 행을 동시에 교체하지 않습니다.
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:token_id, 0))"),
                         {"token_id": record.token_id}):
            raise refresh_in_progress()
        status = _lock_account(db, record.user_id)
        current = db.execute(text("""
            SELECT expires_at, revoked_at
            FROM public.refresh_tokens WHERE token_id = :token_id AND token_hash = :digest
        """), {"token_id": record.token_id, "digest": digest}).one_or_none()
        now = datetime.now(timezone.utc)
        if current is None:
            raise _refresh_invalid()
        if current.revoked_at is not None:
            db.execute(text("""
                UPDATE public.refresh_tokens SET revoked_at = :now
                WHERE user_id = :user_id AND revoked_at IS NULL
            """), {"now": now, "user_id": record.user_id})
        else:
            if current.expires_at <= now or status != "active":
                raise _refresh_invalid()
            db.execute(text("""
                UPDATE public.refresh_tokens SET revoked_at = :now WHERE token_id = :token_id
            """), {"now": now, "token_id": record.token_id})
            return _issue_tokens(db, record.user_id, now)
    # 401을 만들기 전에 재사용으로 폐기한 행을 커밋합니다.
    raise ApiError(401, "REFRESH_REUSED", "이미 폐기된 인증 갱신 토큰입니다. 다시 로그인해 주세요.")


def account_is_active(user_id: UUID) -> bool:
    with service_db_session() as db:
        return db.scalar(text("""
            SELECT status = 'active' FROM public.users WHERE user_id = :user_id
        """), {"user_id": user_id}) is True


def logout(claims: AccessClaims, refresh_token: str) -> None:
    digest = refresh_hash(refresh_token)
    with service_db_session() as db:
        if _lock_account(db, claims.user_id) != "active":
            raise unauthorized()
        updated = db.execute(text("""
            UPDATE public.refresh_tokens SET revoked_at = COALESCE(revoked_at, :now)
            WHERE user_id = :user_id AND token_hash = :digest
            RETURNING token_id
        """), {"now": datetime.now(timezone.utc), "user_id": claims.user_id, "digest": digest})
        if updated.scalar_one_or_none() is None:
            raise _refresh_invalid()

    # Refresh를 먼저 커밋합니다. 상태 저장소 장애 뒤 같은 요청을 재시도할 수 있습니다.
    ttl = claims.expires_at - int(datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        try:
            get_auth_state().revoke(claims.jti, ttl)
        except AuthStateUnavailable:
            raise auth_check_unavailable() from None
