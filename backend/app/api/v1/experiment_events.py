from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.survey import SurveyBuyClick
from app.schemas.experiment_event import (
    BuyClickEvent,
    RecommendationViewEvent,
    SessionEndEvent,
    SizeChangedEvent,
    SurveyOpenedEvent,
    SurveySkippedEvent,
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

        # Для обычных analytics events транзакция заканчивается здесь.
        await session.commit()

    except ValueError as exc:
        await session.rollback()
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
    """
    Сохраняет два вида данных:

    1. ExperimentEvent — полная аналитика A/B эксперимента.
    2. SurveyBuyClick — минимальная operational-запись,
       необходимая для формирования post-purchase survey.

    user_id берём только из JWT, а не из frontend payload.
    """

    try:
        event = await ExperimentEventService.create_event(
            session=session,
            user_id=current_user.id,
            event_type="buy_click",
            session_id=data.session_id,
            event_timestamp=data.timestamp,
            payload={
                "product_id": str(data.product_id),
                "recommended_size": data.recommended_size,
                "price": data.price,
                "outfit_id": (
                    str(data.outfit_id)
                    if data.outfit_id is not None
                    else None
                ),
                "selected_size": data.selected_size,
                "match": data.match,
            },
        )

        # Минимальные данные, которые нужны backend для будущего survey.
        survey_click = SurveyBuyClick(
            user_id=current_user.id,
            session_id=data.session_id,
            product_id=data.product_id,
            recommended_size=data.recommended_size,
            selected_size=data.selected_size,
            clicked_at=data.timestamp,
        )

        session.add(survey_click)
        await session.commit()

    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "status": "saved",
    }


@router.post("/size-changed")
async def size_changed(
    data: SizeChangedEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="size_changed",
        payload={
            "item_id": data.item_id,
            "recommended_size": data.recommended_size,
            "previous_size": data.previous_size,
            "selected_size": data.selected_size,
        },
        current_user=current_user,
        session=session,
    )


@router.post("/survey-opened")
async def survey_opened(
    data: SurveyOpenedEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="survey_opened",
        payload={
            "survey_type": data.survey_type,
            "items_count": data.items_count,
            "device_type": data.device_type,
        },
        current_user=current_user,
        session=session,
    )


@router.post("/survey-skipped")
async def survey_skipped(
    data: SurveySkippedEvent,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await save_event(
        data=data,
        event_type="survey_skipped",
        payload={
            "survey_type": data.survey_type,
            "questions_answered": data.questions_answered,
            "last_question_key": data.last_question_key,
            "last_question_value": data.last_question_value,
            "time_spent_ms": data.time_spent_ms,
            "skip_reason": data.skip_reason,
            "device_type": data.device_type,
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
