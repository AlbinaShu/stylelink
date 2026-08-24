from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.wardrobe import WardrobeItem
from app.schemas.wardrobe import WardrobeItemCreate, WardrobeItemResponse

router = APIRouter()

@router.post("", response_model=WardrobeItemResponse, status_code=201)
async def create_item(data: WardrobeItemCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = WardrobeItem(user_id=current_user.id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("", response_model=list[WardrobeItemResponse])
async def list_items(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(WardrobeItem).where(WardrobeItem.user_id == current_user.id).order_by(WardrobeItem.created_at.desc()))
    return list(result.scalars().all())
