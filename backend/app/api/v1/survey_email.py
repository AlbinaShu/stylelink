from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.survey import Survey
from app.schemas.survey import (
    SurveyAnswerItem,
    SurveyItemResponse,
    SurveyItemsResponse,
    SurveyValidateResponse,
)
from app.services.survey_service import SurveyService


router = APIRouter()


async def get_valid_survey(
    token: str,
    session: AsyncSession,
) -> Survey:
    survey, reason = await SurveyService.validate_token(
        session=session,
        token=token,
    )

    if survey is None:
        raise HTTPException(
            status_code=404,
            detail="Survey token not found",
        )

    if reason == "expired":
        raise HTTPException(
            status_code=410,
            detail="Survey token expired",
        )

    if reason == "already_answered":
        raise HTTPException(
            status_code=409,
            detail="Survey already answered",
        )

    return survey


@router.get(
    "/items",
    response_model=SurveyItemsResponse,
)
async def email_survey_items(
    token: str = Query(min_length=1),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """
    Public endpoint для страницы, открытой из email.

    JWT не нужен.
    Доступ определяется только валидным survey token.
    """

    survey = await get_valid_survey(
        token=token,
        session=session,
    )

    items, total = await SurveyService.get_items(
        session=session,
        survey=survey,
        offset=offset,
        limit=limit,
    )

    if survey.status in {"scheduled", "sent"}:
        survey.status = "clicked"
        await session.commit()

    return SurveyItemsResponse(
        survey_id=survey.id,
        items=items,
        total=total,
        has_more=(offset + len(items)) < total,
    )


@router.post("/answers")
async def email_survey_answers(
    token: str,
    answers: list[SurveyAnswerItem],
    session: AsyncSession = Depends(get_db),
):
    """
    Сохраняет ответы пользователя, пришедшего по email token.

    JWT не нужен.
    user_id из frontend не принимается.
    """

    if not answers:
        raise HTTPException(
            status_code=422,
            detail="answers must not be empty",
        )

    survey = await get_valid_survey(
        token=token,
        session=session,
    )

    created = await SurveyService.save_answers(
        session=session,
        survey=survey,
        answers=answers,
    )

    return {
        "status": "saved",
        "survey_id": str(survey.id),
        "answers_created": created,
    }


@router.get(
    "/validate",
    response_model=SurveyValidateResponse,
)
async def email_validate_token(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    survey, reason = await SurveyService.validate_token(
        session=session,
        token=token,
    )

    if survey is None:
        return SurveyValidateResponse(
            valid=False,
            reason="not_found",
        )

    if reason is not None:
        return SurveyValidateResponse(
            valid=False,
            survey_id=survey.id,
            expires_at=survey.expires_at,
            reason=reason,
        )

    return SurveyValidateResponse(
        valid=True,
        survey_id=survey.id,
        expires_at=survey.expires_at,
    )


from app.schemas.experiment_event import SurveyOpenedEvent, SurveySkippedEvent
from app.services.experiments.survey_event_service import record_survey_event


async def save_email_event(token, data, event_type, session):
    survey = await get_valid_survey(token=token, session=session)
    if data.survey_type != "email":
        raise HTTPException(status_code=400, detail="Expected an email survey event")
    try:
        event = await record_survey_event(session, survey, data, event_type)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"event_id": event.id, "status": "saved"}


@router.post("/events/opened")
async def email_opened(data: SurveyOpenedEvent, token: str = Query(...), session: AsyncSession = Depends(get_db)):
    return await save_email_event(token, data, "survey_opened", session)


@router.post("/events/item-view")
async def email_item_view(data: SurveyOpenedEvent, token: str = Query(...), session: AsyncSession = Depends(get_db)):
    return await save_email_event(token, data, "survey_item_view", session)


@router.post("/events/skipped")
async def email_skipped(data: SurveySkippedEvent, token: str = Query(...), session: AsyncSession = Depends(get_db)):
    return await save_email_event(token, data, "survey_skipped", session)
