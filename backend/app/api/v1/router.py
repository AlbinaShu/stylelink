from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.profile import router as profile_router
from app.api.v1.generations import router as generations_router
from app.api.v1.feedback import router as feedback_router

from app.api.v1.experiment_events import router as experiment_events_router
from app.api.v1.survey import router as survey_router
from app.api.v1.survey_email import router as survey_email_router
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_router.include_router(generations_router, prefix="/generations", tags=["Generations"])
api_router.include_router(experiment_events_router, prefix="/experiment-events", tags=["Experiment Events"])
api_router.include_router(survey_router, prefix="/survey", tags=["Survey"])
api_router.include_router(survey_email_router, prefix="/survey/email", tags=["Survey Email"])

api_router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
