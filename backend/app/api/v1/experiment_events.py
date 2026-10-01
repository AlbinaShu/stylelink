from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.experiment_event import (
    BuyClickEvent,
    RecommendationViewEvent,
    SessionEndEvent,
    TooltipOpenEvent,
)
from app.services.experiments.experiment_event_service import (
    ExperimentEventService,
)

router = APIRouter()


async def save_event(
    *,
    data,
    event_type: str,
    payload: dict,
    current_user: User,
    session: AsyncSession,
):
    try:
        event = await ExperimentEventService.create_event(
            session=session,
            user_id=current_user.id,
            event_type=event_type,
            session_id=data.session_id,
            event_timestamp=data.timestamp,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "status": "saved",
    }


@router.post("/recommendation-view")
async def recommendation_view(
    data: RecommendationViewEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="recommendation_view",
        payload={
            "device_type": data.device_type,
            "outfitItems": [
                item.model_dump()
                for item in data.outfitItems
            ],
        },
        current_user=current_user,
        session=session,
    )


@router.post("/tooltip-open")
async def tooltip_open(
    data: TooltipOpenEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="tooltip_open",
        payload={
            "product_id": data.product_id,
            "tooltip_type": data.tooltip_type,
        },
        current_user=current_user,
        session=session,
    )


@router.post("/buy-click")
async def buy_click(
    data: BuyClickEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="buy_click",
        payload={
            "product_id": data.product_id,
            "recommended_size": data.recommended_size,
            "price": data.price,
            "outfit_id": data.outfit_id,
        },
        current_user=current_user,
        session=session,
    )


@router.post("/session-end")
async def session_end(
    data: SessionEndEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="session_end",
        payload={
            "duration_ms": data.duration_ms,
            "device_type": data.device_type,
        },
        current_user=current_user,
        session=session,
    )
