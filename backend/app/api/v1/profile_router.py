from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.domain.models import User, Order
from app.domain.schemas import OrderHistoryResponse
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/orders", response_model=List[OrderHistoryResponse])
async def get_my_orders(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Customer views their purchase history (FRO01)"""
    result = await db.execute(
        select(Order).options(joinedload(Order.item)).where(Order.user_id == current_user.id)
    )
    orders = result.scalars().all()
    return orders
