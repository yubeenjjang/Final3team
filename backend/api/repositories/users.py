from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.tokens import unauthorized
from api.errors import ApiError
from api.schemas.users import (
    ActivityType,
    CompanionActivity,
    FestivalPreferences,
    PreferencesUpdate,
    Profile,
    ProfileUpdate,
)


def nickname_taken() -> ApiError:
    return ApiError(409, "NICKNAME_TAKEN", "이미 사용 중인 닉네임입니다.")


async def get_preferences(db: AsyncSession) -> FestivalPreferences:
    row = (await db.execute(text("""
        SELECT scenarios, onboarding_status, updated_at
        FROM public.user_festival_preferences WHERE user_id = public.app_current_user()
    """))).mappings().one_or_none()
    return FestivalPreferences.model_validate(row) if row is not None else FestivalPreferences()


async def save_preferences(db: AsyncSession, request: PreferencesUpdate) -> FestivalPreferences:
    selection = FestivalPreferences.from_update(request)
    row = (await db.execute(text("""
        INSERT INTO public.user_festival_preferences (user_id, scenarios, onboarding_status)
        VALUES (public.app_current_user(), CAST(:scenarios AS text[]), :onboarding_status)
        ON CONFLICT (user_id) DO UPDATE
        SET scenarios = EXCLUDED.scenarios, onboarding_status = EXCLUDED.onboarding_status,
            updated_at = statement_timestamp()
        RETURNING scenarios, onboarding_status, updated_at
    """), {"scenarios": selection.scenarios, "onboarding_status": selection.onboarding_status})).mappings().one()
    return FestivalPreferences.model_validate(row)


async def get_profile(db: AsyncSession) -> Profile:
    row = (await db.execute(text("""
        SELECT p.user_id, p.display_name, p.birth_year, p.gender,
               COALESCE(prefs.onboarding_status, 'pending') AS onboarding_status
        FROM public.profiles p LEFT JOIN public.user_festival_preferences prefs USING (user_id)
        WHERE p.user_id = public.app_current_user()
    """))).mappings().one_or_none()
    if row is None:
        raise unauthorized()
    return Profile.model_validate(row)


async def update_profile(db: AsyncSession, request: ProfileUpdate) -> Profile:
    if request.display_name:
        try:
            await db.execute(text("""
                UPDATE public.profiles SET display_name = :display_name
                WHERE user_id = public.app_current_user()
            """), {"display_name": request.display_name})
        except IntegrityError as error:
            if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "uq_profiles_nickname":
                raise nickname_taken() from None
            raise
    return await get_profile(db)


async def get_companion_activity(db: AsyncSession, activity: ActivityType) -> CompanionActivity:
    if activity == "posts":
        query = """
            SELECT post_id, festival_id, meet_at, capacity, approved_count, age_pref, gender_pref, memo, status
            FROM public.companion_posts WHERE author_id = public.app_current_user()
            ORDER BY created_at DESC, post_id ASC
        """
    else:
        query = """
            SELECT application_id, post_id, message, status, created_at
            FROM public.companion_applications WHERE applicant_id = public.app_current_user()
            ORDER BY created_at DESC, application_id ASC
        """
    rows = (await db.execute(text(query))).mappings().all()
    return CompanionActivity(items=[dict(row) for row in rows])
