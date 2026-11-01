from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.survey import SurveyBuyClick, SurveyItem
from app.schemas.survey import (
    SurveyAnswersRequest,
    SurveyAnswersResponse,
    SurveyItemsResponse,
    SurveyPopupResponse,
    SurveySkipRequest,
    SurveySkipResponse,
    SurveyValidateResponse,
)
from app.services.survey_service import SurveyService
from app.services.survey_popup_service import SurveyPopupService


router = APIRouter()


@router.get("/items", response_model=SurveyItemsResponse)
async def get_survey_items(
    survey_id: UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Возвращает товары активного pop-up survey.

    user_id не принимаем от frontend:
    авторизованный пользователь определяется по JWT.
    """

    survey = (
        await SurveyService.get_survey(session, survey_id, current_user.id)
        if survey_id else await SurveyService.get_active_survey_for_user(session, current_user.id)
    )

    if survey is None:
        raise HTTPException(
            status_code=404,
            detail="No active survey",
        )

    items, total = await SurveyService.get_items(
        session=session,
        survey=survey,
        offset=offset,
        limit=limit,
    )

    return SurveyItemsResponse(
        survey_id=survey.id,
        items=items,
        total=total,
        has_more=offset + len(items) < total,
    )


@router.post("/answers", response_model=SurveyAnswersResponse)
async def submit_survey_answers(
    data: SurveyAnswersRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Сохраняет ответы пользователя.

    Даже частичный submit считается ответом:
    после него pop-up повторно не показывается.
    """

    survey = await SurveyService.get_survey(
        session=session,
        survey_id=data.survey_id,
        user_id=current_user.id,
    )

    if survey is None:
        raise HTTPException(
            status_code=404,
            detail="Survey not found",
        )

    try:
        answered_count = await SurveyService.save_answers(
            session=session,
            survey=survey,
            answers=data.answers,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return SurveyAnswersResponse(
        status="ok",
        answered_count=answered_count,
        continuation_path="/survey?token=" + survey.token,
    )


@router.post("/skip", response_model=SurveySkipResponse)
async def skip_survey(
    data: SurveySkipRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Операционный skip.

    Не переводим survey в answered:
    по ТЗ после пропуска pop-up может быть показан снова.

    Подробная аналитика survey_skipped уже хранится
    отдельным experiment event.
    """

    survey = await SurveyService.get_survey(
        session=session,
        survey_id=data.survey_id,
        user_id=current_user.id,
    )

    if survey is None:
        raise HTTPException(
            status_code=404,
            detail="Survey not found",
        )

    if survey.status == "answered":
        raise HTTPException(
            status_code=409,
            detail="Survey already answered",
        )

    if not data.session_id:
        raise HTTPException(
            status_code=422,
            detail="session_id is required for popup skip",
        )

    await SurveyPopupService.mark_skipped(
        session=session,
        survey=survey,
        user_id=current_user.id,
        session_id=data.session_id,
    )

    return SurveySkipResponse(status="skipped")


@router.get("/validate", response_model=SurveyValidateResponse)
async def validate_survey_token(
    token: str = Query(min_length=1),
    session: AsyncSession = Depends(get_db),
):
    """
    Публичная проверка email-token.

    Здесь JWT не нужен: пользователь приходит по ссылке из письма.
    """

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
            reason=reason,
        )

    return SurveyValidateResponse(
        valid=True,
        survey_id=survey.id,
        expires_at=survey.expires_at,
    )


@router.get("/popup", response_model=SurveyPopupResponse)
async def survey_popup(
    session_id: str = Query(min_length=1, max_length=255),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Возвращает решение о показе popup survey.

    Пользователь определяется только по JWT.
    session_id передаётся frontend для ограничения показа по сессиям.
    """

    survey = await SurveyService.get_active_survey_for_user(
        session=session,
        user_id=current_user.id,
    )

    if survey is None:
        return SurveyPopupResponse(
            show=False,
            reason="no_survey",
        )

    previous_visit = await session.execute(
        select(SurveyBuyClick.id)
        .join(SurveyItem, SurveyItem.buy_click_id == SurveyBuyClick.id)
        .where(SurveyItem.survey_id == survey.id, SurveyBuyClick.session_id == session_id)
        .limit(1)
    )
    if previous_visit.scalar_one_or_none() is not None:
        return SurveyPopupResponse(show=False, reason="same_session")

    show, reason = await SurveyPopupService.evaluate(
        session=session,
        survey=survey,
        user_id=current_user.id,
        session_id=session_id,
    )

    # Любую новую session регистрируем.
    # Это позволяет посчитать две сессии после Skip.
    if reason != "already_shown":
        await SurveyPopupService.register_session(
            session=session,
            survey=survey,
            user_id=current_user.id,
            session_id=session_id,
        )

    return SurveyPopupResponse(
        show=show,
        survey_id=survey.id,
        reason=reason,
    )
