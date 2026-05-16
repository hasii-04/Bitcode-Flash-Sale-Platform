from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.domain.models import Event, Item, EventStateEnum
from app.domain.schemas import EventCreate, EventUpdate, EventStateUpdate
from app.core.redis_client import redis_client

class EventService:
    @staticmethod
    async def get_all_events(db: AsyncSession):
        result = await db.execute(select(Event).options(selectinload(Event.items)))
        return result.scalars().all()

    @staticmethod
    async def get_event_by_id(db: AsyncSession, event_id: int):
        result = await db.execute(
            select(Event).options(selectinload(Event.items)).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
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
            
        await db.commit()
        return event

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
