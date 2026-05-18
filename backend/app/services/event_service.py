from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from fastapi import HTTPException
from app.domain.models import Event, Item, EventStateEnum, Order, OrderStatusEnum
from app.domain.schemas import EventCreate, EventUpdate, EventStateUpdate
from app.core.redis_client import redis_client

class EventService:
    @staticmethod
    async def sync_event_state(db: AsyncSession, event: Event):
        now = datetime.now(timezone.utc)
        go_live = event.go_live_time
        if go_live.tzinfo is None:
            go_live = go_live.replace(tzinfo=timezone.utc)

        if event.state == EventStateEnum.locked and now >= go_live:
            event.state = EventStateEnum.live
            for item in event.items:
                exists = await redis_client.exists(f"item:{item.id}:stock")
                if not exists:
                    await redis_client.set(f"item:{item.id}:stock", item.current_stock)

        if event.items and all(item.current_stock <= 0 for item in event.items):
            event.state = EventStateEnum.closed

        return event

    @staticmethod
    async def get_all_events(db: AsyncSession):
        result = await db.execute(select(Event).options(selectinload(Event.items)))
        events = result.scalars().all()
        for event in events:
            await EventService.sync_event_state(db, event)
        await db.commit()
        return events

    @staticmethod
    async def get_event_by_id(db: AsyncSession, event_id: int):
        result = await db.execute(
            select(Event).options(selectinload(Event.items)).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        await EventService.sync_event_state(db, event)
        await db.commit()
        return event

    @staticmethod
    async def create_event(db: AsyncSession, event_in: EventCreate):
        # Validate items
        if not event_in.items:
            raise HTTPException(status_code=400, detail="Event must have at least one item")
        for item in event_in.items:
            if not (100 <= item.initial_stock <= 500):
                raise HTTPException(status_code=400, detail=f"Stock for {item.name} must be between 100 and 500 units")
                
        new_event = Event(
            name=event_in.name,
            cover_photo=event_in.cover_photo,
            go_live_time=event_in.go_live_time,
            state=EventStateEnum.locked
        )
        db.add(new_event)
        await db.flush() # Get event ID
        
        for item_in in event_in.items:
            new_item = Item(
                event_id=new_event.id,
                name=item_in.name,
                unit_price=item_in.unit_price,
                initial_stock=item_in.initial_stock,
                current_stock=item_in.initial_stock
            )
            db.add(new_item)
            
        await db.commit()
        return await EventService.get_event_by_id(db, new_event.id)

    @staticmethod
    async def update_event(db: AsyncSession, event_id: int, event_in: EventUpdate):
        event = await EventService.get_event_by_id(db, event_id)
        if event.state != EventStateEnum.locked:
            raise HTTPException(status_code=400, detail="Can only edit locked events")
            
        if event_in.name is not None:
            event.name = event_in.name
        if event_in.cover_photo is not None:
            event.cover_photo = event_in.cover_photo
        if event_in.go_live_time is not None:
            event.go_live_time = event_in.go_live_time

        if event_in.items is not None:
            seen_ids = set()
            existing = {item.id: item for item in event.items}
            for item_in in event_in.items:
                if not (100 <= item_in.initial_stock <= 500):
                    raise HTTPException(status_code=400, detail=f"Stock for {item_in.name} must be between 100 and 500 units")
                if item_in.id and item_in.id in existing:
                    item = existing[item_in.id]
                    item.name = item_in.name
                    item.unit_price = item_in.unit_price
                    item.initial_stock = item_in.initial_stock
                    item.current_stock = item_in.initial_stock
                    seen_ids.add(item.id)
                else:
                    new_item = Item(
                        event_id=event.id,
                        name=item_in.name,
                        unit_price=item_in.unit_price,
                        initial_stock=item_in.initial_stock,
                        current_stock=item_in.initial_stock,
                    )
                    db.add(new_item)
            
        await db.commit()
        return await EventService.get_event_by_id(db, event_id)

    @staticmethod
    async def change_event_state(db: AsyncSession, event_id: int, state_in: EventStateUpdate):
        event = await EventService.get_event_by_id(db, event_id)
        
        # If transitioning to LIVE, populate Redis stock
        if state_in.state == EventStateEnum.live and event.state != EventStateEnum.live:
            for item in event.items:
                await redis_client.set(f"item:{item.id}:stock", item.current_stock)
                
        event.state = state_in.state
        await db.commit()
        return event
