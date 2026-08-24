from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.wardrobe import router as wardrobe_router
from app.api.v1.outfits import router as outfits_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(wardrobe_router, prefix="/wardrobe", tags=["wardrobe"])
api_router.include_router(outfits_router, prefix="/outfits", tags=["outfits"])
