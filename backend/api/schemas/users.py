from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from api.schemas.auth import check_password_rule

from api.schemas.common import DisplayName

Scenario = Literal["family_relaxed", "friends_activity", "couple_photo", "pet", "solo"]
OnboardingStatus = Literal["pending", "completed", "skipped"]
ActivityType = Literal["posts", "applications"]
Gender = Literal["male", "female"]


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarios: list[Scenario] = Field(max_length=5)
    skip: bool = Field(strict=True)


class FestivalPreferences(BaseModel):
    scenarios: list[Scenario] = Field(default_factory=list)
    onboarding_status: OnboardingStatus = "pending"
    updated_at: datetime | None = None

    @classmethod
    def from_update(cls, request: PreferencesUpdate) -> "FestivalPreferences":
        if request.skip or not request.scenarios:
            return cls(onboarding_status="skipped")
        return cls(scenarios=list(dict.fromkeys(request.scenarios)), onboarding_status="completed")


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName = ""


class Profile(BaseModel):
    user_id: UUID
    display_name: str | None
    birth_year: int | None
    gender: Gender | None
    onboarding_status: OnboardingStatus


class CompanionPost(BaseModel):
    post_id: str
    festival_id: str
    meet_at: datetime
    capacity: int
    approved_count: int
    age_pref: Literal["any", "20s", "30s", "40s", "50s_plus"] | None
    gender_pref: Literal["any", "female", "male"]
    memo: str | None
    status: Literal["open", "full", "ended", "cancelled"]


class CompanionApplication(BaseModel):
    application_id: str
    post_id: str
    message: str | None
    status: Literal["pending", "approved", "rejected", "cancelled"]
    created_at: datetime


class CompanionActivity(BaseModel):
    items: list[CompanionPost | CompanionApplication]


class AccountDeletion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: SecretStr


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: SecretStr
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: SecretStr) -> SecretStr:
        return check_password_rule(value)

    @model_validator(mode="after")
    def differs_from_current(self) -> "PasswordChange":
        if self.new_password.get_secret_value() == self.current_password.get_secret_value():
            raise ValueError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
        return self
