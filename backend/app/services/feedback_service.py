"""Business rules and persistence for selection/service feedback."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_assignment import ABAssignment
from app.models.feedback import FeedbackEvent, FeedbackPrompt, FeedbackRating
from app.models.generation import Generation
from app.models.outfit import Outfit
from app.models.user import User
from app.schemas.feedback import FeedbackAnswer, FeedbackEventRequest, FeedbackRatingResponse, FeedbackScope
from app.services.ab.ab_test_service import ABTestService


class FeedbackError(ValueError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code


class FeedbackService:
    # Mutations lock the account row; the API owns the transaction commit.
    @staticmethod
    async def lock_user(session: AsyncSession, user_id: UUID) -> None:
        # Serialize updates and prompt claims across tabs/devices on PostgreSQL.
        await session.execute(select(User.id).where(User.id == user_id).with_for_update())

    @staticmethod
    async def context(session: AsyncSession, user_id: UUID, generation_id: UUID) -> dict[str, Any]:
        generation = await session.scalar(select(Generation).where(
            Generation.id == generation_id, Generation.user_id == user_id,
        ))
        if generation is None:
            raise FeedbackError(404, "Generation not found")
        has_outfits = select(Outfit.id).where(Outfit.generation_id == Generation.id).exists()
        if generation.status != "completed" or not await session.scalar(
            select(has_outfits).select_from(Generation).where(Generation.id == generation.id)
        ):
            raise FeedbackError(409, "Feedback requires a completed non-empty generation")
        successful = (
            Generation.user_id == user_id, Generation.status == "completed", has_outfits,
        )
        count = await session.scalar(select(func.count()).select_from(Generation).where(*successful))
        number = await session.scalar(select(func.count()).select_from(Generation).where(
            *successful,
            or_(Generation.created_at < generation.created_at,
                (Generation.created_at == generation.created_at) & (Generation.id <= generation.id)),
        ))
        assignment = await session.scalar(select(ABAssignment).where(
            ABAssignment.user_id == user_id,
            ABAssignment.experiment_name == ABTestService.EXPERIMENT_NAME,
        ))
        return {
            "generation_number": number,
            "completed_count": count,
            "ab_group": assignment.ab_group if assignment else None,
            "stratum": assignment.stratum if assignment else None,
            "questionnaire_version": 1,
        }

    @staticmethod
    def target(scope: FeedbackScope, generation_id: UUID) -> str:
        return "service" if scope == "service" else str(generation_id)

    @staticmethod
    async def rating_for(session: AsyncSession, user_id: UUID, scope: FeedbackScope, generation_id: UUID) -> FeedbackRating | None:
        return await session.scalar(select(FeedbackRating).where(
            FeedbackRating.user_id == user_id,
            FeedbackRating.target == FeedbackService.target(scope, generation_id),
        ))

    @staticmethod
    def serialize_rating(row: FeedbackRating | None) -> FeedbackRatingResponse | None:
        return FeedbackRatingResponse.model_validate(row) if row else None

    @staticmethod
    def add_event(session: AsyncSession, user_id: UUID, generation_id: UUID, scope: FeedbackScope, event_type: str, ctx: dict[str, Any], **values: Any) -> None:
        session.add(FeedbackEvent(user_id=user_id, generation_id=generation_id, scope=scope,
                                  event_type=event_type, payload={**ctx, **values}))

    @staticmethod
    async def get_feedback(session: AsyncSession, user_id: UUID, generation_id: UUID) -> dict[str, Any]:
        ctx = await FeedbackService.context(session, user_id, generation_id)
        selection = await FeedbackService.rating_for(session, user_id, "selection", generation_id)
        service = await FeedbackService.rating_for(session, user_id, "service", generation_id)
        prompt = await session.get(FeedbackPrompt, user_id)
        return {**ctx, "selection": FeedbackService.serialize_rating(selection), "service": FeedbackService.serialize_rating(service),
                "invitation_eligible": ctx["generation_number"] >= 3 and service is None and prompt is None}

    @staticmethod
    async def save_feedback(session: AsyncSession, user_id: UUID, generation_id: UUID, scope: FeedbackScope, data: FeedbackAnswer) -> FeedbackRatingResponse:
        await FeedbackService.lock_user(session, user_id)
        ctx = await FeedbackService.context(session, user_id, generation_id)
        if data.source == "invitation":
            prompt = await session.get(FeedbackPrompt, user_id)
            if scope != "service" or prompt is None or prompt.generation_id != generation_id:
                raise FeedbackError(409, "No service invitation has been shown")
        row = await FeedbackService.rating_for(session, user_id, scope, generation_id)
        updated = row is not None
        if row is None:
            row = FeedbackRating(user_id=user_id, target=FeedbackService.target(scope, generation_id), scope=scope)
            session.add(row)
        row.generation_id = generation_id
        row.generation_number = ctx["generation_number"]
        row.score, row.comment, row.source = data.score, data.comment, data.source
        row.ab_group, row.stratum = ctx["ab_group"], ctx["stratum"]
        row.questionnaire_version = ctx["questionnaire_version"]
        row.updated_at = datetime.now(timezone.utc)
        FeedbackService.add_event(session, user_id, generation_id, scope, "rating_updated" if updated else "rating_submitted",
                  ctx, score=data.score, comment=data.comment, source=data.source)
        await session.flush()
        return FeedbackRatingResponse.model_validate(row)

    @staticmethod
    async def claim_invitation(session: AsyncSession, user_id: UUID, generation_id: UUID) -> dict[str, bool]:
        await FeedbackService.lock_user(session, user_id)
        ctx = await FeedbackService.context(session, user_id, generation_id)
        service = await FeedbackService.rating_for(session, user_id, "service", generation_id)
        if ctx["generation_number"] < 3 or service is not None or await session.get(FeedbackPrompt, user_id):
            await session.flush()
            return {"show": False}
        session.add(FeedbackPrompt(user_id=user_id, generation_id=generation_id))
        FeedbackService.add_event(session, user_id, generation_id, "service", "invitation_shown", ctx)
        await session.flush()
        return {"show": True}

    @staticmethod
    async def record_event(session: AsyncSession, user_id: UUID, generation_id: UUID, data: FeedbackEventRequest) -> dict[str, str]:
        await FeedbackService.lock_user(session, user_id)
        ctx = await FeedbackService.context(session, user_id, generation_id)
        if data.event_type == "invitation_dismissed":
            prompt = await session.get(FeedbackPrompt, user_id)
            if data.scope != "service" or prompt is None or prompt.generation_id != generation_id:
                raise FeedbackError(409, "No service invitation for this generation")
            if prompt.dismissed_at is not None:
                await session.flush()
                return {"status": "ok"}
            prompt.dismissed_at = datetime.now(timezone.utc)
        else:
            # Count an inline question once per user + generation + scope.
            existing = await session.scalar(select(FeedbackEvent.id).where(
                FeedbackEvent.user_id == user_id, FeedbackEvent.generation_id == generation_id,
                FeedbackEvent.scope == data.scope, FeedbackEvent.event_type == "inline_view",
            ).limit(1))
            if existing is not None:
                await session.flush()
                return {"status": "ok"}
        FeedbackService.add_event(session, user_id, generation_id, data.scope, data.event_type, ctx)
        await session.flush()
        return {"status": "ok"}
