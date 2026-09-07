from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileRequest, ProfileResponse
from app.api.deps import get_current_user


router = APIRouter()


# Получение профиля
@router.get("", response_model=ProfileResponse | None)
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )

    return result.scalar_one_or_none()


# Обновление профиля
@router.put("", response_model=ProfileResponse)
async def update_profile(
    data: ProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        profile = Profile(user_id=current_user.id)
        session.add(profile)

    profile.gender = data.gender
    profile.height = data.height
    profile.weight = data.weight
    profile.chest = data.chest
    profile.waist = data.waist
    profile.hips = data.hips

    await session.commit()
    await session.refresh(profile)

    return profile