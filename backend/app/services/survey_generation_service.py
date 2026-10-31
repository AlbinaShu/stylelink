from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.config import settings
from app.models.survey import Survey, SurveyBuyClick, SurveyItem


def click_periods(clicks, period):
    """Reconstruct anchored periods, including repeat clicks in their original period."""
    ordered = sorted(clicks, key=lambda click: click.clicked_at)
    index = 0
    while index < len(ordered):
        start = ordered[index].clicked_at
        end = start + period
        group = []
        while index < len(ordered) and ordered[index].clicked_at < end:
            group.append(ordered[index])
            index += 1
        yield start, end, group


class SurveyGenerationService:
    @staticmethod
    def collection_period():
        return timedelta(minutes=settings.survey_test_period_minutes) if settings.survey_test_mode else timedelta(days=settings.survey_period_days)

    @staticmethod
    def token_lifetime():
        return timedelta(days=settings.survey_token_lifetime_days)

    @classmethod
    async def generate_ready_surveys(cls, session):
        from app.services.survey_email_service import SurveyEmailService

        now = datetime.now(timezone.utc)
        result = await session.execute(select(SurveyBuyClick).order_by(SurveyBuyClick.user_id, SurveyBuyClick.clicked_at))
        by_user = {}
        for click in result.scalars().all():
            by_user.setdefault(click.user_id, []).append(click)
        existing = await session.execute(
            select(Survey.user_id, SurveyItem.product_id).join(SurveyItem, SurveyItem.survey_id == Survey.id)
        )
        used = set(existing.all())
        created = []
        for user_id, clicks in by_user.items():
            seen_products = set()
            for start, end, group in click_periods(clicks, cls.collection_period()):
                first_by_product = {}
                for click in group:
                    if click.recommended_size and click.recommended_size.strip() and click.selected_size != "not_applicable" and click.product_id not in seen_products:
                        seen_products.add(click.product_id)
                        first_by_product[click.product_id] = click
                if end > now:
                    break
                candidates = [click for product_id, click in first_by_product.items() if (user_id, product_id) not in used]
                if not candidates:
                    continue
                scheduled = max(end, max(click.clicked_at for click in group) + SurveyEmailService.email_delay())
                survey = Survey(
                    user_id=user_id, token=str(uuid4()), status="scheduled",
                    period_started_at=start, period_ended_at=end, scheduled_at=scheduled,
                    expires_at=max(now, scheduled) + cls.token_lifetime(),
                )
                session.add(survey)
                await session.flush()
                for click in candidates:
                    session.add(SurveyItem(
                        survey_id=survey.id, product_id=click.product_id,
                        buy_click_id=click.id, recommended_size=click.recommended_size,
                        selected_size=click.selected_size, clicked_at=click.clicked_at,
                    ))
                    used.add((user_id, click.product_id))
                created.append(survey)
        if created:
            await session.commit()
        return created
