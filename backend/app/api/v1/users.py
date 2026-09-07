from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse, UpdateCurrentUserRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()

# Получение текущего пользователя
@router.get("/current_user", response_model=UserResponse)
async def current_user(current_user: User = Depends(get_current_user)):
    return current_user

# Обновление данных пользователя
@router.patch("/current", response_model=UserResponse)
async def update_current_user(
    data: UpdateCurrentUserRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    current_user.name = data.name.strip() if data.name else None

    await session.commit()
    await session.refresh(current_user)

    return current_user
