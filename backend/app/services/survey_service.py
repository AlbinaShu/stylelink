from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.models.product import Product
from app.models.survey import Survey, SurveyAnswer, SurveyItem
from app.schemas.survey import SurveyAnswerItem


class SurveyService:
    @staticmethod
    async def get_survey(session, survey_id: UUID, user_id: UUID):
        result = await session.execute(select(Survey).where(Survey.id == survey_id, Survey.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_survey_for_user(session, user_id: UUID):
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Survey).where(
                Survey.user_id == user_id,
                Survey.status.notin_(["answered", "expired"]),
                Survey.expires_at > now,
            ).order_by(Survey.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_items(session, survey, offset, limit):
        count_result = await session.execute(select(func.count(SurveyItem.id)).where(SurveyItem.survey_id == survey.id))
        total = count_result.scalar_one()
        result = await session.execute(
            select(SurveyItem, Product, SurveyAnswer)
            .join(Product, Product.id == SurveyItem.product_id)
            .outerjoin(SurveyAnswer, (SurveyAnswer.survey_id == SurveyItem.survey_id) & (SurveyAnswer.product_id == SurveyItem.product_id))
            .where(SurveyItem.survey_id == survey.id)
            .order_by(SurveyItem.clicked_at.desc()).offset(offset).limit(limit)
        )
        fields = set(SurveyAnswerItem.model_fields) - {"product_id"}
        items = []
        for item, product, answer in result.all():
            items.append({
                "product_id": product.id, "name": product.name, "image_url": product.image_url,
                "recommended_size": item.recommended_size, "selected_size": item.selected_size,
                "buy_click_id": item.buy_click_id,
                "status": "answered" if answer is not None else "not_answered",
                "clicked_at": item.clicked_at,
                "answer": {"product_id": str(product.id), **{key: getattr(answer, key) for key in fields}} if answer else None,
            })
        return items, total

    @staticmethod
    async def save_answers(session, survey, answers):
        # Serialize edits of this invitation; the unique survey/product key remains intact.
        await session.execute(select(Survey.id).where(Survey.id == survey.id).with_for_update())
        now = datetime.now(timezone.utc)
        if survey.expires_at <= now:
            raise ValueError("Survey expired")
        product_ids = [answer.product_id for answer in answers]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate products in answer batch")
        allowed_result = await session.execute(
            select(SurveyItem.product_id).where(SurveyItem.survey_id == survey.id, SurveyItem.product_id.in_(product_ids))
        )
        if set(product_ids) - set(allowed_result.scalars().all()):
            raise ValueError("One or more products do not belong to this survey")
        result = await session.execute(
            select(SurveyAnswer).where(SurveyAnswer.survey_id == survey.id, SurveyAnswer.product_id.in_(product_ids))
        )
        existing = {answer.product_id: answer for answer in result.scalars().all()}
        for answer in answers:
            row = existing.get(answer.product_id)
            if row is None:
                row = SurveyAnswer(survey_id=survey.id, product_id=answer.product_id)
                session.add(row)
            for key, value in answer.model_dump(exclude={"product_id"}).items():
                setattr(row, key, value)
            row.updated_at = now
        # Keep the specification's suppression of unsolicited popup/email after a submit.
        # The user can still complete or update this same invitation until expiry.
        if answers:
            survey.status = "answered"
        await session.commit()
        return len(answers)

    @staticmethod
    async def validate_token(session, token):
        result = await session.execute(select(Survey).where(Survey.token == token))
        survey = result.scalar_one_or_none()
        if survey is None:
            return None, "not_found"
        if survey.expires_at <= datetime.now(timezone.utc):
            if survey.status != "expired":
                survey.status = "expired"
                await session.commit()
            return survey, "expired"
        return survey, None
