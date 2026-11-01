from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
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
            payload=jsonable_encoder(payload),
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
    return await save_recommendation_event(data, current_user, session, "recommendation_view")


@router.post("/explanation-view")
async def explanation_view(data: RecommendationViewEvent, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await save_recommendation_event(data, current_user, session, "explanation_view")


async def save_recommendation_event(data, current_user, session, event_type):
    from app.services.experiments.recommendation_context import recommendation_snapshots
    try:
        snapshots = await recommendation_snapshots(session, current_user.id, data.outfitItems)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await save_event(
        data=data,
        event_type=event_type,
        payload={
            "device_type": data.device_type,
            "outfitItems": snapshots,
            "schema_version": 3,
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
            "explanation_summary": data.explanation_summary,
            "explanation_text": data.explanation_text,
            "explanation_meta": data.explanation_meta,
            "explanation_stage": "details",
            "schema_version": 3,
            "outfit_id": data.outfit_id,
            "outfit_item_id": data.outfit_item_id,
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
            "product_id": data.product_id,
            "outfit_id": data.outfit_id,
            "outfit_item_id": data.outfit_item_id,
            "recommended_size": data.recommended_size,
            "previous_size": data.previous_size,
            "selected_size": data.selected_size,
        },
        current_user=current_user,
        session=session,
    )



async def save_survey_event(data, event_type, current_user, session):
    from app.services.survey_service import SurveyService
    from app.services.experiments.survey_event_service import record_survey_event

    survey = await SurveyService.get_survey(session, data.survey_id, current_user.id)
    if survey is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    if data.survey_type != "popup":
        raise HTTPException(status_code=400, detail="Email events require the invitation token endpoint")
    try:
        event = await record_survey_event(session, survey, data, event_type)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"event_id": event.id, "event_type": event.event_type, "status": "saved"}


@router.post("/survey-opened")
async def survey_opened(data: SurveyOpenedEvent, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await save_survey_event(data, "survey_opened", current_user, session)


@router.post("/survey-item-view")
async def survey_item_view(data: SurveyOpenedEvent, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await save_survey_event(data, "survey_item_view", current_user, session)


@router.post("/survey-skipped")
async def survey_skipped(data: SurveySkippedEvent, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await save_survey_event(data, "survey_skipped", current_user, session)


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
