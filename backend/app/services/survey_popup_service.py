from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.survey import Survey, SurveyPopupSession


class SurveyPopupService:
    """
    Operational logic for survey popup.

    Rules:
    - popup is processed once per session_id;
    - after Skip, two next new sessions are suppressed;
    - on the third new session popup becomes available again.
    """

    SKIP_SESSIONS = 2

    @classmethod
    async def get_session(
        cls,
        session: AsyncSession,
        survey: Survey,
        user_id: UUID,
        session_id: str,
    ) -> SurveyPopupSession | None:
        result = await session.execute(
            select(SurveyPopupSession).where(
                SurveyPopupSession.survey_id == survey.id,
                SurveyPopupSession.user_id == user_id,
                SurveyPopupSession.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_last_skip(
        cls,
        session: AsyncSession,
        survey: Survey,
        user_id: UUID,
    ) -> SurveyPopupSession | None:
        result = await session.execute(
            select(SurveyPopupSession)
            .where(
                SurveyPopupSession.survey_id == survey.id,
                SurveyPopupSession.user_id == user_id,
                SurveyPopupSession.skipped_at.is_not(None),
            )
            .order_by(SurveyPopupSession.skipped_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def sessions_after_skip(
        cls,
        session: AsyncSession,
        survey: Survey,
        user_id: UUID,
        skipped: SurveyPopupSession,
    ) -> int:
        result = await session.execute(
            select(SurveyPopupSession.session_id).where(
                SurveyPopupSession.survey_id == survey.id,
                SurveyPopupSession.user_id == user_id,
                SurveyPopupSession.shown_at > skipped.shown_at,
            )
        )

        return len(set(result.scalars().all()))

    @classmethod
    async def evaluate(
        cls,
        session: AsyncSession,
        survey: Survey,
        user_id: UUID,
        session_id: str,
    ) -> tuple[bool, str]:
        if survey.status == "answered":
            return False, "no_survey"

        # Текущую session уже обрабатывали.
        existing = await cls.get_session(
            session=session,
            survey=survey,
            user_id=user_id,
            session_id=session_id,
        )

        if existing is not None:
            return False, "already_shown"

        last_skip = await cls.get_last_skip(
            session=session,
            survey=survey,
            user_id=user_id,
        )

        if last_skip is None:
            return True, "available"

        passed = await cls.sessions_after_skip(
            session=session,
            survey=survey,
            user_id=user_id,
            skipped=last_skip,
        )

        if passed < cls.SKIP_SESSIONS:
            return False, "skip_cooldown"

        return True, "available"

    @classmethod
    async def register_session(
        cls,
        session: AsyncSession,
        survey: Survey,
        user_id: UUID,
        session_id: str,
    ) -> SurveyPopupSession:
        existing = await cls.get_session(
            session=session,
            survey=survey,
            user_id=user_id,
            session_id=session_id,
        )

        if existing is not None:
            return existing

        row = SurveyPopupSession(
            survey_id=survey.id,
            user_id=user_id,
            session_id=session_id,
        )

        session.add(row)
        await session.commit()
        await session.refresh(row)

        return row

    @classmethod
    async def mark_skipped(
        cls,
        session: AsyncSession,
        survey: Survey,
        user_id: UUID,
        session_id: str,
    ) -> SurveyPopupSession:
        row = await cls.get_session(
            session=session,
            survey=survey,
            user_id=user_id,
            session_id=session_id,
        )

        if row is None:
            row = SurveyPopupSession(
                survey_id=survey.id,
                user_id=user_id,
                session_id=session_id,
            )
            session.add(row)

        row.skipped_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(row)

        return row
