from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.profile import router as profile_router
from app.api.v1.generations import router as generations_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_router.include_router(generations_router, prefix="/generations", tags=["Generations"])
