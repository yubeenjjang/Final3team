import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

from api.schemas.common import DisplayName

_EMAIL_LOCAL = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*$")
_EMAIL_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def check_password_rule(value: SecretStr) -> SecretStr:
    """A32 가입과 A82 비밀번호 변경이 함께 쓰는 비밀번호 규칙."""
    password = value.get_secret_value()
    if not (
        8 <= len(password) <= 64
        and re.search(r"[A-Za-z]", password)
        and re.search(r"[0-9]", password)
    ):
        raise ValueError("비밀번호는 영문과 숫자를 포함해 8~64자로 입력해 주세요.")
    return value


class LoginRequest(BaseModel):
    email: str
    password: SecretStr


class SignupRequest(LoginRequest):
    email: str = Field(max_length=254)
    display_name: DisplayName
    birth_year: int = Field(ge=1900)
    gender: Literal["male", "female"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        local, _, domain = value.partition("@")
        labels = domain.split(".")
        if (
            len(local) > 64
            or not _EMAIL_LOCAL.fullmatch(local)
            or len(labels) < 2
            or not all(_EMAIL_LABEL.fullmatch(label) for label in labels)
        ):
            raise ValueError("이메일 형식을 확인해 주세요.")
        return value.lower()

    @field_validator("birth_year")
    @classmethod
    def validate_birth_year(cls, value: int) -> int:
        if value > date.today().year:
            raise ValueError("출생연도는 올해 이하여야 합니다.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        return check_password_rule(value)


class RefreshRequest(BaseModel):
    refresh_token: SecretStr
