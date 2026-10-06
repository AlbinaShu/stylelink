from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, select
from uuid import UUID


from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.generation import Generation
from app.models.user import User
from app.models.profile import Profile
from app.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationsPageResponse,
)

from app.models.outfit import Outfit
from app.schemas.outfit import OutfitResponse, OutfitControlResponse
from app.services.generation_pipeline import GenerationPipeline
from app.services.ab.ab_test_service import ABTestService


router = APIRouter()


# Генерация образов
@router.post("", response_model=GenerationResponse)
async def create_generation(
    data: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    generation = Generation(
        user_id=current_user.id,
        occasion=data.occasion,
        style=data.style,
        season=data.season,
        budget=data.budget,
        gender=data.gender,
        height=data.height,
        weight=data.weight,
        chest=data.chest,
        waist=data.waist,
        hips=data.hips,
        prompt=data.prompt,
        status="created",
    )

    session.add(generation)
    await session.commit()
    await session.refresh(generation)

    background_tasks.add_task(
        GenerationPipeline().run,
        generation.id,
    )

    return generation


# Получение генераций
@router.get("", response_model=GenerationsPageResponse)
async def get_generations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    total_result = await session.execute(
        select(func.count(Generation.id))
        .where(Generation.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * page_size

    result = await session.execute(
        select(Generation)
        .where(Generation.user_id == current_user.id)
        .order_by(Generation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    items = result.scalars().all()
    pages = (total + page_size - 1) // page_size

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }

# Получение аутфитов генерации
@router.get(
    "/{generation_id}/outfits",
)
async def get_generation_outfits(
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # Проверяем, что generation принадлежит текущему пользователю.
    generation_result = await session.execute(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == current_user.id,
        )
    )

    generation = generation_result.scalar_one_or_none()

    if generation is None:
        raise HTTPException(
            status_code=404,
            detail="Generation not found",
        )

    # Получаем профиль текущего пользователя.
    profile_result = await session.execute(
        select(Profile).where(
            Profile.user_id == current_user.id,
        )
    )

    profile = profile_result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=409,
            detail="Profile is required for A/B assignment",
        )

    # Получаем уже существующую группу или назначаем её один раз.
    assignment = await ABTestService.get_or_assign(
        session=session,
        profile=profile,
    )

    # Если assignment был создан только что, сохраняем его.
    await session.commit()

    result = await session.execute(
        select(Outfit)
        .options(selectinload(Outfit.items))
        .where(Outfit.generation_id == generation_id)
        .order_by(Outfit.created_at.asc())
    )

    outfits = result.scalars().all()

    # Control A:
    # Size Shift существует в БД, но наружу не отдаётся.
    if assignment.ab_group == "A":
        payload = [
            OutfitControlResponse.model_validate(outfit).model_dump(
                mode="json",
            )
            for outfit in outfits
        ]

        return JSONResponse(content=payload)

    # Treatment B:
    # Отдаём recommended_size + fit.
    payload = [
        OutfitResponse.model_validate(outfit).model_dump(
            mode="json",
        )
        for outfit in outfits
    ]

    return JSONResponse(content=payload)

# Получение одной генерации
@router.get(
    "/{generation_id}",
    response_model=GenerationResponse,
)
async def get_generation(
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == current_user.id,
        )
    )

    generation = result.scalar_one_or_none()

    if generation is None:
        raise HTTPException(
            status_code=404,
            detail="Generation not found",
        )

    return generation
