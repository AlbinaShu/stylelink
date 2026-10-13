import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_assignment import ABAssignment
from app.models.profile import Profile


class ABTestService:
    EXPERIMENT_NAME = "size_shift_v1"

    @staticmethod
    def determine_stratum(profile: Profile) -> str:
        gender = (profile.gender or "").lower()

        chest = profile.chest
        waist = profile.waist
        hips = profile.hips

        if chest is None or waist is None or hips is None:
            return "unknown"

        if gender in {"female", "woman", "женский", "ж"}:
            is_large = (
                chest >= 94
                or waist >= 73
                or hips >= 102
            )
            return "woman_large" if is_large else "woman_small"

        if gender in {"male", "man", "мужской", "м"}:
            is_large = (
                chest >= 100
                or waist >= 86
                or hips >= 104
            )
            return "man_large" if is_large else "man_small"

        return "unknown"

    @classmethod
    async def get_or_assign(
        cls,
        session: AsyncSession,
        profile: Profile,
    ) -> ABAssignment:
        # Если пользователь уже распределён, группу не меняем.
        result = await session.execute(
            select(ABAssignment).where(
                ABAssignment.user_id == profile.user_id,
                ABAssignment.experiment_name == cls.EXPERIMENT_NAME,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            return existing

        stratum = cls.determine_stratum(profile)

        # Считаем количество A и B только внутри этой страты.
        result = await session.execute(
            select(
                ABAssignment.ab_group,
                func.count(ABAssignment.id),
            )
            .where(
                ABAssignment.experiment_name == cls.EXPERIMENT_NAME,
                ABAssignment.stratum == stratum,
            )
            .group_by(ABAssignment.ab_group)
        )

        counts = {"A": 0, "B": 0}

        for group, count in result.all():
            if group in counts:
                counts[group] = count

        if counts["A"] < counts["B"]:
            ab_group = "A"
        elif counts["B"] < counts["A"]:
            ab_group = "B"
        else:
            ab_group = random.choice(("A", "B"))

        assignment = ABAssignment(
            user_id=profile.user_id,
            experiment_name=cls.EXPERIMENT_NAME,
            stratum=stratum,
            ab_group=ab_group,
        )

        session.add(assignment)
        await session.flush()

        return assignment
