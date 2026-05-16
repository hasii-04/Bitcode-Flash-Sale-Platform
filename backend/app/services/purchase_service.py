from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis_client import reserve_item_atomically
from app.domain.models import Order, OrderStatusEnum
from app.core.database import AsyncSessionLocal
from app.core.websocket_manager import manager

class PurchaseService:
    @staticmethod
    async def process_purchase(event_id: int, item_id: int, user_id: int, background_tasks: BackgroundTasks) -> dict:
        reservation_status = await reserve_item_atomically(item_id, user_id)
        
        if reservation_status == -1:
            return {"success": False, "message": "You have already purchased this item.", "status_code": 400}
        elif reservation_status == -2:
            return {"success": False, "message": "This item is sold out.", "status_code": 400}
            
        remaining_stock = reservation_status
        
        # Offload Postgres write AND WebSocket broadcast
        background_tasks.add_task(PurchaseService.finalize_order_in_db, user_id, item_id, event_id, remaining_stock)
        
        return {
            "success": True,
            "message": "Item reserved successfully. Processing order...",
            "status_code": 200
        }

    @staticmethod
    async def finalize_order_in_db(user_id: int, item_id: int, event_id: int, remaining_stock: int):
        async with AsyncSessionLocal() as db:
            # Fetch price from DB
            from sqlalchemy.future import select
            from app.domain.models import Item
            result = await db.execute(select(Item).where(Item.id == item_id))
            item = result.scalar_one_or_none()
            price = float(item.unit_price) if item else 0.0

            # Mark order as confirmed (directly bought, no pending payment gateway)
            new_order = Order(
                user_id=user_id,
                item_id=item_id,
                quantity=1,
                price_paid=price,
                status=OrderStatusEnum.confirmed
            )
            db.add(new_order)

            # Update DB stock
            if item:
                item.current_stock = max(0, item.current_stock - 1)

            await db.commit()

            # Real-time WebSocket broadcast
            await manager.broadcast_stock_update(event_id, item_id, remaining_stock)
