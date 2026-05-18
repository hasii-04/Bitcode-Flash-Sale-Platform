from fastapi import BackgroundTasks
from sqlalchemy import select
from fastapi import HTTPException
from app.core.redis_client import release_item_reservation, reserve_item_atomically
from app.domain.models import Event, EventStateEnum, Item, Order, OrderStatusEnum
from app.core.database import AsyncSessionLocal
from app.core.websocket_manager import manager

class PurchaseService:
    @staticmethod
    async def process_purchase(event_id: int, item_id: int, user_id: int, background_tasks: BackgroundTasks) -> dict:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Item, Event).join(Item.event).where(Item.id == item_id, Event.id == event_id))
            row = result.one_or_none()
            if not row:
                return {"success": False, "message": "Item not found for this event.", "status_code": 404}
            item, event = row
            if event.state != EventStateEnum.live:
                return {"success": False, "message": "This event is not live.", "status_code": 400}
            existing = await db.execute(
                select(Order).where(
                    Order.user_id == user_id,
                    Order.item_id == item_id,
                    Order.status != OrderStatusEnum.cancelled,
                )
            )
            if existing.scalar_one_or_none():
                return {"success": False, "message": "You have already purchased this item.", "status_code": 400}

        reservation_status = await reserve_item_atomically(item_id, user_id)
        
        if reservation_status == -1:
            return {"success": False, "message": "You have already purchased this item.", "status_code": 400}
        elif reservation_status == -2:
            return {"success": False, "message": "This item is sold out.", "status_code": 400}
            
        remaining_stock = reservation_status

        order_id = await PurchaseService.create_reserved_order(user_id, item_id, event_id, remaining_stock)
        background_tasks.add_task(manager.broadcast_stock_update, event_id, item_id, remaining_stock)
        
        return {
            "success": True,
            "message": "Item reserved successfully. Please confirm payment.",
            "status_code": 200,
            "order_id": order_id,
            "remaining_stock": remaining_stock
        }

    @staticmethod
    async def create_reserved_order(user_id: int, item_id: int, event_id: int, remaining_stock: int) -> int:
        async with AsyncSessionLocal() as db:
            item = await db.get(Item, item_id)
            new_order = Order(
                user_id=user_id,
                item_id=item_id,
                quantity=1,
                price_paid=item.unit_price if item else 0.00,
                status=OrderStatusEnum.reserved
            )
            if item:
                item.current_stock = remaining_stock
                if remaining_stock <= 0:
                    event = await db.get(Event, event_id)
                    if event:
                        await db.refresh(event, ["items"])
                    if event and all(event_item.current_stock <= 0 for event_item in event.items):
                        event.state = EventStateEnum.closed
            db.add(new_order)
            await db.commit()
            await db.refresh(new_order)
            return new_order.id
            
    @staticmethod
    async def confirm_order(order_id: int, user_id: int) -> Order:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).join(Order.item).where(Order.id == order_id, Order.user_id == user_id)
            )
            order = result.scalar_one_or_none()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            if order.status == OrderStatusEnum.cancelled:
                raise HTTPException(status_code=400, detail="This reservation was cancelled")
            order.status = OrderStatusEnum.confirmed
            await db.commit()
            await db.refresh(order)
            return order

    @staticmethod
    async def cancel_order(order_id: int, user_id: int) -> tuple[Order, int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order, Item, Event)
                .join(Order.item)
                .join(Item.event)
                .where(Order.id == order_id, Order.user_id == user_id)
            )
            row = result.one_or_none()
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")
            order, item, event = row
            if order.status == OrderStatusEnum.confirmed:
                raise HTTPException(status_code=400, detail="Confirmed orders cannot be cancelled")
            if order.status == OrderStatusEnum.cancelled:
                return order, item.current_stock

            remaining_stock = await release_item_reservation(item.id, user_id)
            item.current_stock = remaining_stock
            if event.state == EventStateEnum.closed and remaining_stock > 0:
                event.state = EventStateEnum.live
            order.status = OrderStatusEnum.cancelled
            await db.commit()
            await db.refresh(order)
            await manager.broadcast_stock_update(event.id, item.id, remaining_stock)
            return order, remaining_stock
