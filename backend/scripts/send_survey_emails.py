import asyncio

from app.core.database import AsyncSessionLocal
from app.services.survey_email_service import SurveyEmailService


async def main():
    async with AsyncSessionLocal() as session:
        sent = await SurveyEmailService.send_due_emails(
            session
        )

        print("EMAILS SENT:", len(sent))

        for survey in sent:
            print(
                "EMAIL SURVEY:",
                survey.id,
            )

    async with AsyncSessionLocal() as session:
        reminded = (
            await SurveyEmailService.send_due_reminders(
                session
            )
        )

        print("REMINDERS SENT:", len(reminded))

        for survey in reminded:
            print(
                "REMINDER SURVEY:",
                survey.id,
            )


if __name__ == "__main__":
    asyncio.run(main())
