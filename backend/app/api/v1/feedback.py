from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.feedback import (
    FeedbackAnswer,
    FeedbackContextResponse,
    FeedbackEventRequest,
    FeedbackEventResponse,
    FeedbackInvitationResponse,
    FeedbackRatingResponse,
    FeedbackScope,
)
from app.services.feedback_service import FeedbackError, FeedbackService

router = APIRouter()


@router.get("/{generation_id}", response_model=FeedbackContextResponse)
async def get_feedback(
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await FeedbackService.get_feedback(session, current_user.id, generation_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put("/{generation_id}/ratings/{scope}", response_model=FeedbackRatingResponse)
async def save_feedback(
    generation_id: UUID,
    scope: FeedbackScope,
    data: FeedbackAnswer,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await FeedbackService.save_feedback(
            session, current_user.id, generation_id, scope, data,
        )
        await session.commit()
        return result
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{generation_id}/invitation", response_model=FeedbackInvitationResponse)
async def claim_invitation(
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await FeedbackService.claim_invitation(session, current_user.id, generation_id)
        await session.commit()
        return result
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{generation_id}/events", response_model=FeedbackEventResponse)
async def feedback_event(
    generation_id: UUID,
    data: FeedbackEventRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await FeedbackService.record_event(session, current_user.id, generation_id, data)
        await session.commit()
        return result
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
