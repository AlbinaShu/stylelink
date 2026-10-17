from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.survey import Survey, SurveyBuyClick, SurveyItem


class SurveyGenerationService:
    @staticmethod
    def collection_period() -> timedelta:
        if settings.survey_test_mode:
            return timedelta(
                minutes=settings.survey_test_period_minutes
            )

        return timedelta(days=settings.survey_period_days)

    @staticmethod
    def token_lifetime() -> timedelta:
        return timedelta(
            days=settings.survey_token_lifetime_days
        )

    @classmethod
    async def generate_ready_surveys(
        cls,
        session: AsyncSession,
    ) -> list[Survey]:
        now = datetime.now(timezone.utc)
        period = cls.collection_period()

        result = await session.execute(
            select(SurveyBuyClick).order_by(
                SurveyBuyClick.user_id,
                SurveyBuyClick.clicked_at,
            )
        )
        clicks = list(result.scalars().all())

        if not clicks:
            return []

        existing_result = await session.execute(
            select(
                Survey.user_id,
                SurveyItem.product_id,
                SurveyItem.clicked_at,
            ).join(
                SurveyItem,
                SurveyItem.survey_id == Survey.id,
            )
        )

        already_used = {
            (user_id, product_id, clicked_at)
            for user_id, product_id, clicked_at
            in existing_result.all()
        }

        by_user = {}

        for click in clicks:
            key = (
                click.user_id,
                click.product_id,
                click.clicked_at,
            )

            if key in already_used:
                continue

            by_user.setdefault(
                click.user_id,
                [],
            ).append(click)

        created = []

        for user_id, user_clicks in by_user.items():
            user_clicks.sort(
                key=lambda x: x.clicked_at
            )

            while user_clicks:
                first = user_clicks[0]
                period_end = first.clicked_at + period

                if now < period_end:
                    break

                period_clicks = [
                    click
                    for click in user_clicks
                    if click.clicked_at <= period_end
                ]

                latest_by_product = {}

                for click in period_clicks:
                    previous = latest_by_product.get(
                        click.product_id
                    )

                    if (
                        previous is None
                        or click.clicked_at
                        > previous.clicked_at
                    ):
                        latest_by_product[
                            click.product_id
                        ] = click

                survey = Survey(
                    user_id=user_id,
                    token=str(uuid4()),
                    status="scheduled",
                    scheduled_at=period_end,
                    expires_at=(
                        now + cls.token_lifetime()
                    ),
                )

                session.add(survey)
                await session.flush()

                for click in sorted(
                    latest_by_product.values(),
                    key=lambda x: x.clicked_at,
                    reverse=True,
                ):
                    session.add(
                        SurveyItem(
                            survey_id=survey.id,
                            product_id=click.product_id,
                            recommended_size=(
                                click.recommended_size
                            ),
                            selected_size=(
                                click.selected_size
                            ),
                            clicked_at=click.clicked_at,
                        )
                    )

                created.append(survey)

                used_ids = {
                    click.id
                    for click in period_clicks
                }

                user_clicks = [
                    click
                    for click in user_clicks
                    if click.id not in used_ids
                ]

        if created:
            await session.commit()

            for survey in created:
                await session.refresh(survey)

        return created
