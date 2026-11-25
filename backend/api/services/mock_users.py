import secrets
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

from api.auth.tokens import unauthorized
from api.mocks.store import (
    MockUser,
    access_sessions,
    auth_lock,
    favorites_by_user,
    preferences_by_user,
    refresh_sessions,
    retired_refresh_tokens,
    user_nicknames,
    users_by_email,
)
from api.repositories.users import nickname_taken
from api.schemas.users import CompanionActivity, FestivalPreferences, PreferencesUpdate, Profile, ProfileUpdate
from api.services import mock_friends
from api.services.account_deletion import password_mismatch
from api.services.mock_auth import _password_hash, authenticated_access, update_nickname


def _current_user_id(authorization: str | None) -> str:
    _, access = authenticated_access(authorization, datetime.now(timezone.utc))
    return access.user_id


def _account(authorization: str | None) -> tuple[str, MockUser]:
    user_id = _current_user_id(authorization)
    for email, user in users_by_email.items():
        if user.user_id == user_id:
            return email, user
    raise unauthorized()


def _preferences(user_id: str) -> FestivalPreferences:
    return preferences_by_user.get(user_id) or FestivalPreferences()


def get_preferences(authorization: str | None) -> FestivalPreferences:
    with auth_lock:
        return _preferences(_current_user_id(authorization))


def save_preferences(authorization: str | None, request: PreferencesUpdate) -> FestivalPreferences:
    with auth_lock:
        user_id = _current_user_id(authorization)
        selection = FestivalPreferences.from_update(request)
        selection.updated_at = datetime.now(timezone.utc)
        preferences_by_user[user_id] = selection
        return selection


def get_profile(authorization: str | None, request: ProfileUpdate | None = None) -> Profile:
    with auth_lock:
        email, user = _account(authorization)
        if request is not None and request.display_name:
            name = request.display_name.casefold()
            if name != user.display_name.casefold() and name in user_nicknames:
                raise nickname_taken()
            user = update_nickname(email, user, request.display_name)
        return Profile(
            user_id=user.user_id, display_name=user.display_name, birth_year=user.birth_year,
            gender=user.gender, onboarding_status=_preferences(user.user_id).onboarding_status,
        )


def get_companion_activity(authorization: str | None) -> CompanionActivity:
    with auth_lock:
        _current_user_id(authorization)
        return CompanionActivity(items=[])


def delete_account(authorization: str | None, password: str) -> None:
    with auth_lock:
        email, user = _account(authorization)
        if not secrets.compare_digest(_password_hash(password, user.salt), user.password_hash):
            raise password_mismatch()
        del users_by_email[email]
        user_nicknames.discard(user.display_name.casefold())
        favorites_by_user.pop(user.user_id, None)
        preferences_by_user.pop(user.user_id, None)
        mock_friends.store.remove_account(UUID(user.user_id))
        for token, access in tuple(access_sessions.items()):
            if access.user_id == user.user_id:
                del access_sessions[token]
        for token, refresh in tuple(refresh_sessions.items()):
            if refresh.user.user_id == user.user_id:
                del refresh_sessions[token]
        for token, user_id in tuple(retired_refresh_tokens.items()):
            if user_id == user.user_id:
                del retired_refresh_tokens[token]


def change_password(authorization: str | None, current_password: str, new_password: str) -> None:
    with auth_lock:
        email, user = _account(authorization)
        if not secrets.compare_digest(_password_hash(current_password, user.salt), user.password_hash):
            raise password_mismatch()
        salt = secrets.token_bytes(16)
        users_by_email[email] = replace(user, salt=salt, password_hash=_password_hash(new_password, salt))
        # DB 모드와 같게 이 기기의 Access와 모든 기기의 Refresh를 끝냅니다.
        # 다른 기기의 Access는 남은 수명 동안 유지됩니다(A82).
        access_sessions.pop(authorization.partition(" ")[2], None)
        for token, refresh in tuple(refresh_sessions.items()):
            if refresh.user.user_id == user.user_id:
                del refresh_sessions[token]
