from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.outfit import Outfit
from app.models.user import User
from app.models.wardrobe import WardrobeItem
from app.schemas.outfit import OutfitCreate, OutfitResponse

router = APIRouter()

@router.post("", response_model=OutfitResponse, status_code=201)
async def create_outfit(data: OutfitCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = []
    if data.item_ids:
        result = await db.execute(select(WardrobeItem).where(WardrobeItem.id.in_(data.item_ids), WardrobeItem.user_id == current_user.id))
        items = list(result.scalars().all())
        if len(items) != len(set(data.item_ids)):
            raise HTTPException(status_code=400, detail="One or more wardrobe items do not belong to the user")
    outfit = Outfit(user_id=current_user.id, name=data.name, occasion=data.occasion, items=items)
    db.add(outfit)
    await db.commit()
    await db.refresh(outfit)
    return outfit

@router.get("", response_model=list[OutfitResponse])
async def list_outfits(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Outfit).where(Outfit.user_id == current_user.id).order_by(Outfit.created_at.desc()))
    return list(result.scalars().all())
