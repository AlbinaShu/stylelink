import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.services.survey_email_service import SurveyEmailService
from app.services.survey_generation_service import SurveyGenerationService


logger = logging.getLogger(__name__)

# Проверяем готовые задачи каждые 5 минут
SCHEDULER_INTERVAL_SECONDS = 5 * 60


async def run_survey_jobs() -> None:
    # Формирование готовых опросов
    try:
        async with AsyncSessionLocal() as session:
            surveys = (
                await SurveyGenerationService.generate_ready_surveys(
                    session
                )
            )

            if surveys:
                logger.info(
                    "Survey scheduler: created %s surveys",
                    len(surveys),
                )

    except Exception:
        logger.exception(
            "Survey scheduler: survey generation failed"
        )

    # Отправка email
    try:
        async with AsyncSessionLocal() as session:
            sent = await SurveyEmailService.send_due_emails(
                session
            )

            if sent:
                logger.info(
                    "Survey scheduler: sent %s emails",
                    len(sent),
                )

    except Exception:
        logger.exception(
            "Survey scheduler: email sending failed"
        )

    # Отправка напоминаний
    try:
        async with AsyncSessionLocal() as session:
            reminded = (
                await SurveyEmailService.send_due_reminders(
                    session
                )
            )

            if reminded:
                logger.info(
                    "Survey scheduler: sent %s reminders",
                    len(reminded),
                )

    except Exception:
        logger.exception(
            "Survey scheduler: reminder sending failed"
        )


async def survey_scheduler() -> None:
    logger.info("Survey scheduler started")

    while True:
        await run_survey_jobs()
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)