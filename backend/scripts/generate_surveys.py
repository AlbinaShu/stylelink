import asyncio

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.survey_generation_service import (
    SurveyGenerationService,
)


async def main():
    print(
        "MODE:",
        "TEST" if settings.survey_test_mode
        else "PRODUCTION",
    )

    print(
        "PERIOD:",
        SurveyGenerationService.collection_period(),
    )

    async with AsyncSessionLocal() as session:
        surveys = (
            await SurveyGenerationService.generate_ready_surveys(
                session
            )
        )

        print("CREATED:", len(surveys))

        for survey in surveys:
            print(
                "SURVEY:",
                survey.id,
                "USER:",
                survey.user_id,
            )


if __name__ == "__main__":
    asyncio.run(main())
