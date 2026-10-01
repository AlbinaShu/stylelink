from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_assignment import ABAssignment
from app.models.experiment_event import ExperimentEvent
from app.services.ab.ab_test_service import ABTestService


class ExperimentEventService:
    @classmethod
    async def create_event(
        cls,
        session: AsyncSession,
        user_id: UUID,
        event_type: str,
        session_id: str,
        event_timestamp: datetime,
        payload: dict[str, Any],
    ) -> ExperimentEvent:
        # A/B-группу и страту берём только из БД,
        # а не доверяем данным от frontend.
        result = await session.execute(
            select(ABAssignment).where(
                ABAssignment.user_id == user_id,
                ABAssignment.experiment_name
                == ABTestService.EXPERIMENT_NAME,
            )
        )
        assignment = result.scalar_one_or_none()

        if assignment is None:
            raise ValueError(
                "Пользователь ещё не распределён в A/B-тест"
            )

        event = ExperimentEvent(
            user_id=user_id,
            experiment_name=assignment.experiment_name,
            stratum=assignment.stratum,
            ab_group=assignment.ab_group,
            event_type=event_type,
            session_id=session_id,
            event_timestamp=event_timestamp,
            payload=payload,
        )

        session.add(event)
        await session.commit()
        await session.refresh(event)

        return event
