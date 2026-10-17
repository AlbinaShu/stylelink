from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.survey import Survey, SurveyAnswer, SurveyItem
from app.schemas.survey import SurveyAnswerItem


class SurveyService:
    """
    Операционная логика survey.

    ExperimentEvent здесь не используется как основное хранилище:
    survey и ответы должны существовать независимо от аналитических событий.
    """

    @staticmethod
    async def get_survey(
        session: AsyncSession,
        survey_id: UUID,
        user_id: UUID,
    ) -> Survey | None:
        result = await session.execute(
            select(Survey).where(
                Survey.id == survey_id,
                Survey.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_survey_for_user(
        session: AsyncSession,
        user_id: UUID,
    ) -> Survey | None:
        """
        Возвращает последний ещё не завершённый опрос пользователя.
        Используется pop-up сценарием.
        """
        now = datetime.now(timezone.utc)

        result = await session.execute(
            select(Survey)
            .where(
                Survey.user_id == user_id,
                Survey.status.notin_(["answered", "expired"]),
                Survey.expires_at > now,
            )
            .order_by(Survey.created_at.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_items(
        session: AsyncSession,
        survey: Survey,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        """
        Backend сам сортирует товары:
        от последнего buy_click к более старым.
        """

        count_result = await session.execute(
            select(func.count(SurveyItem.id)).where(
                SurveyItem.survey_id == survey.id
            )
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(
                SurveyItem,
                Product,
                SurveyAnswer.id.label("answer_id"),
            )
            .join(
                Product,
                Product.id == SurveyItem.product_id,
            )
            .outerjoin(
                SurveyAnswer,
                (SurveyAnswer.survey_id == SurveyItem.survey_id)
                & (SurveyAnswer.product_id == SurveyItem.product_id),
            )
            .where(
                SurveyItem.survey_id == survey.id
            )
            .order_by(SurveyItem.clicked_at.desc())
            .offset(offset)
            .limit(limit)
        )

        items = []

        for survey_item, product, answer_id in result.all():
            items.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "image_url": product.image_url,
                    "recommended_size": survey_item.recommended_size,
                    "selected_size": survey_item.selected_size,
                    "status": (
                        "answered"
                        if answer_id is not None
                        else "not_answered"
                    ),
                    "clicked_at": survey_item.clicked_at,
                }
            )

        return items, total

    @staticmethod
    async def save_answers(
        session: AsyncSession,
        survey: Survey,
        answers: list[SurveyAnswerItem],
    ) -> int:
        """
        Сохраняет ответы только по товарам,
        действительно принадлежащим этому survey.
        """

        product_ids = [answer.product_id for answer in answers]

        allowed_result = await session.execute(
            select(SurveyItem.product_id).where(
                SurveyItem.survey_id == survey.id,
                SurveyItem.product_id.in_(product_ids),
            )
        )
        allowed_ids = set(allowed_result.scalars().all())

        unknown_ids = set(product_ids) - allowed_ids
        if unknown_ids:
            raise ValueError(
                "One or more products do not belong to this survey"
            )

        existing_result = await session.execute(
            select(SurveyAnswer.product_id).where(
                SurveyAnswer.survey_id == survey.id,
                SurveyAnswer.product_id.in_(product_ids),
            )
        )
        existing_ids = set(existing_result.scalars().all())

        created = 0

        for answer in answers:
            # Повторную отправку одного и того же товара не дублируем.
            if answer.product_id in existing_ids:
                continue

            session.add(
                SurveyAnswer(
                    survey_id=survey.id,
                    product_id=answer.product_id,
                    order_placed=answer.order_placed,
                    sizes_ordered=answer.sizes_ordered,
                    purchased_size=answer.purchased_size,
                    added_to_cart=answer.added_to_cart,
                    sizes_in_cart=answer.sizes_in_cart,
                    cart_size=answer.cart_size,
                    fit_result=answer.fit_result,
                    action=answer.action,
                    return_reason=answer.return_reason,
                    return_reason_text=answer.return_reason_text,
                )
            )
            created += 1

        # По ТЗ даже частичная отправка означает, что пользователь ответил.
        if created > 0:
            survey.status = "answered"

        await session.commit()

        return created

    @staticmethod
    async def validate_token(
        session: AsyncSession,
        token: str,
    ) -> tuple[Survey | None, str | None]:
        result = await session.execute(
            select(Survey).where(Survey.token == token)
        )
        survey = result.scalar_one_or_none()

        if survey is None:
            return None, "not_found"

        if survey.status == "answered":
            return survey, "already_answered"

        now = datetime.now(timezone.utc)

        if survey.expires_at <= now:
            if survey.status != "expired":
                survey.status = "expired"
                await session.commit()

            return survey, "expired"

        return survey, None
