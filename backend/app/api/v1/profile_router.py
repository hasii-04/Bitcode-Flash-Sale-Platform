from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.domain.models import User, Order, Item, RoleEnum
from app.domain.schemas import CustomerListResponse, OrderHistoryResponse, PasswordChange, ProfileUpdate, UserResponse
from app.api.dependencies import get_current_admin, get_current_user
from app.services.auth_service import AuthService

router = APIRouter()

@router.get("/orders", response_model=List[OrderHistoryResponse])
async def get_my_orders(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Customer views their purchase history (FRO01)"""
    result = await db.execute(
        select(Order).options(
            joinedload(Order.item).joinedload(Item.event)
        ).where(Order.user_id == current_user.id)
    )
    orders = result.scalars().all()
    
    # Map to schema with calculated names
    response = []
    for o in orders:
        response.append(OrderHistoryResponse(
            id=o.id,
            item_id=o.item_id,
            item_name=o.item.name,
            event_name=o.item.event.name,
            quantity=o.quantity,
            price_paid=float(o.price_paid),
            status=o.status,
            created_at=o.created_at
        ))
    return response

@router.put("/me", response_model=UserResponse)
async def update_my_profile(profile_in: ProfileUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.display_name = profile_in.display_name
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/change-password")
async def change_password(password_in: PasswordChange, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not AuthService.verify_password(password_in.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = AuthService.get_password_hash(password_in.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.get("/admin/customers", response_model=List[CustomerListResponse])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    order_counts = (
        select(Order.user_id, func.count(Order.id).label("order_count"))
        .group_by(Order.user_id)
        .subquery()
    )
    result = await db.execute(
        select(User, func.coalesce(order_counts.c.order_count, 0))
        .outerjoin(order_counts, User.id == order_counts.c.user_id)
        .where(User.role == RoleEnum.customer)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [
        CustomerListResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            order_count=order_count,
        )
        for user, order_count in result.all()
    ]

@router.post("/admin/customers/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_customer(user_id: int, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = await db.get(User, user_id)
    if not user or user.role != RoleEnum.customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/admin/customers/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_customer(user_id: int, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = await db.get(User, user_id)
    if not user or user.role != RoleEnum.customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user
