from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.generation import Generation

FREE_GENERATION_LIMIT = 5


async def get_generation_usage(session: AsyncSession, user_id: UUID) -> dict:
    # In-progress requests reserve a slot; failed attempts are refunded.
    used = await session.scalar(select(func.count(Generation.id)).where(
        Generation.user_id == user_id, Generation.status != "failed",
    ))
    used = used or 0
    return {"used": used, "limit": FREE_GENERATION_LIMIT,
            "remaining": max(0, FREE_GENERATION_LIMIT - used),
            "exhausted": used >= FREE_GENERATION_LIMIT}
