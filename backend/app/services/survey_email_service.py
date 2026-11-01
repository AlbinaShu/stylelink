from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.survey import Survey, SurveyItem, SurveyBuyClick
from app.models.user import User


class SurveyEmailService:
    @staticmethod
    def email_delay() -> timedelta:
        if settings.survey_test_mode:
            return timedelta(
                minutes=settings.survey_test_email_delay_minutes
            )

        return timedelta(
            days=settings.survey_email_delay_days
        )

    @staticmethod
    def reminder_delay() -> timedelta:
        return timedelta(
            days=settings.survey_reminder_delay_days
        )

    @staticmethod
    def survey_url(token: str) -> str:
        separator = (
            "&"
            if "?" in settings.survey_frontend_url
            else "?"
        )

        return (
            f"{settings.survey_frontend_url}"
            f"{separator}token={token}"
        )

    @classmethod
    async def send(
        cls,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        message = EmailMessage()

        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message["Date"] = formatdate(localtime=False)
        sender_domain = parseaddr(settings.smtp_from)[1].partition("@")[2]
        message["Message-ID"] = make_msgid(domain=sender_domain or None)

        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=settings.smtp_port == 465,
            start_tls=settings.smtp_port != 465,
            username=settings.smtp_user,
            password=settings.smtp_password,
            timeout=30,
        )

    @classmethod
    async def last_click_at(
        cls,
        session: AsyncSession,
        survey: Survey,
    ):
        result = await session.execute(
            select(SurveyItem.clicked_at)
            .where(
                SurveyItem.survey_id == survey.id
            )
            .order_by(
                SurveyItem.clicked_at.desc()
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    @classmethod
    async def send_due_emails(
        cls,
        session: AsyncSession,
    ) -> list[Survey]:
        now = datetime.now(timezone.utc)

        result = await session.execute(
            select(Survey, User)
            .join(
                User,
                User.id == Survey.user_id,
            )
            .where(
                Survey.status == "scheduled",
                Survey.sent_at.is_(None),
                Survey.expires_at > now,
            )
            .order_by(Survey.created_at)
        )

        rows = result.all()
        sent = []

        for survey, user in rows:
            if not user.email:
                survey.status = "no_email"
                continue

            last_click = await cls.last_click_at(
                session,
                survey,
            )

            if last_click is None:
                continue

            send_at = survey.scheduled_at or max(
                survey.period_ended_at or survey.created_at,
                last_click + cls.email_delay(),
            )

            # scheduled_at хранит реальный плановый момент email.
            # Это делает состояние БД понятным при аудите и отладке.
            if survey.scheduled_at != send_at:
                survey.scheduled_at = send_at
                await session.flush()

            if now < send_at:
                continue

            url = cls.survey_url(survey.token)

            body = (
                "Здравствуйте!\n\n"
                "Вы недавно смотрели товары в AI·StyleLink. "
                "Помогите нам понять, подошла ли рекомендация "
                "размера.\n\n"
                "Открыть короткий опрос:\n"
                f"{url}\n\n"
                "Спасибо!"
            )

            try:
                await cls.send(
                    recipient=user.email,
                    subject=(
                        "AI·StyleLink — помогите оценить "
                        "рекомендацию размера"
                    ),
                    body=body,
                )
            except Exception:
                await session.rollback()
                raise

            survey.sent_at = now
            survey.status = "sent"

            await session.commit()
            sent.append(survey)

        await session.commit()

        return sent

    @classmethod
    async def send_due_reminders(
        cls,
        session: AsyncSession,
    ) -> list[Survey]:
        now = datetime.now(timezone.utc)

        result = await session.execute(
            select(Survey, User)
            .join(
                User,
                User.id == Survey.user_id,
            )
            .where(
                Survey.status.in_(
                    ["sent", "opened", "clicked"]
                ),
                Survey.sent_at.is_not(None),
                Survey.reminder_sent_at.is_(None),
                Survey.expires_at > now,
            )
            .order_by(Survey.sent_at)
        )

        rows = result.all()
        reminded = []

        for survey, user in rows:
            if not user.email:
                continue

            reminder_at = (
                survey.sent_at
                + cls.reminder_delay()
            )

            if now < reminder_at:
                continue

            url = cls.survey_url(survey.token)

            body = (
                "Здравствуйте!\n\n"
                "Напоминаем о коротком опросе AI·StyleLink "
                "по рекомендации размера.\n\n"
                "Продолжить опрос:\n"
                f"{url}\n\n"
                "Спасибо!"
            )

            try:
                await cls.send(
                    recipient=user.email,
                    subject=(
                        "AI·StyleLink — напоминание об опросе"
                    ),
                    body=body,
                )
            except Exception:
                await session.rollback()
                raise

            survey.reminder_sent_at = now

            await session.commit()
            reminded.append(survey)

        return reminded
