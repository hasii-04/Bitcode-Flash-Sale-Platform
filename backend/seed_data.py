import asyncio
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.domain.models import User, Event, Item, EventStateEnum
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_data():
    async with AsyncSessionLocal() as db:
        # Check if users already exist
        admin = User(
            email="admin@swiftdrop.com",
            display_name="Super Admin",
            hashed_password=pwd_context.hash("password123"),
            role="admin",
            is_active=True
        )
        customer = User(
            email="maya@swiftdrop.test",
            display_name="Maya Fernando",
            hashed_password=pwd_context.hash("password123"),
            role="customer",
            is_active=True
        )
        db.add(admin)
        db.add(customer)
        await db.commit()
        
        # Create an event going live in 5 minutes
        event = Event(
            name="Aurora Tech Import Drop",
            cover_photo="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80",
            go_live_time=datetime.utcnow() + timedelta(minutes=5),
            state=EventStateEnum.locked
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Create items for the event
        item1 = Item(
            event_id=event.id,
            name="NoiseLock Pro Earbuds",
            unit_price=69.00,
            initial_stock=240,
            current_stock=240
        )
        item2 = Item(
            event_id=event.id,
            name="Nine-Port Travel Hub",
            unit_price=42.00,
            initial_stock=180,
            current_stock=180
        )
        db.add_all([item1, item2])
        await db.commit()
        print("Successfully seeded Admin, Customer, and Event data!")

if __name__ == "__main__":
    asyncio.run(seed_data())
