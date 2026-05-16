from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.database import Base, engine, AsyncSessionLocal
from app.core.config import settings
from app.api.v1 import auth_router, event_router, purchase_router, profile_router
from app.domain.models import Event, EventStateEnum, Item, RoleEnum, User
from app.services.auth_service import AuthService
from app.core.redis_client import redis_client


async def seed_demo_data() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@swiftdropdemo.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                email="admin@swiftdropdemo.com",
                display_name="SwiftDrop Admin",
                hashed_password=AuthService.get_password_hash("password123"),
                role=RoleEnum.admin,
            ))

        result = await db.execute(select(User).where(User.email == "kalana@gamil.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                email="kalana@gamil.com",
                display_name="Kalana",
                hashed_password=AuthService.get_password_hash("password123"),
                role=RoleEnum.admin,
            ))

        result = await db.execute(select(User).where(User.email == "kalana@gmail.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                email="kalana@gmail.com",
                display_name="Kalana",
                hashed_password=AuthService.get_password_hash("password123"),
                role=RoleEnum.admin,
            ))

        result = await db.execute(select(User).where(User.email == "maya@swiftdropdemo.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                email="maya@swiftdropdemo.com",
                display_name="Maya Chen",
                hashed_password=AuthService.get_password_hash("password123"),
                role=RoleEnum.customer,
            ))

        result = await db.execute(select(Event).where(Event.name == "Weekend Import Drop"))
        if not result.scalar_one_or_none():
            event = Event(
                name="Weekend Import Drop",
                cover_photo="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
                go_live_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                state=EventStateEnum.live,
            )
            event.items = [
                Item(name="Imported Smart Watch", unit_price=79, initial_stock=150, current_stock=150),
                Item(name="Noise Canceling Headphones", unit_price=129, initial_stock=120, current_stock=120),
            ]
            db.add(event)

        await db.commit()

        live_events = await db.execute(select(Event).where(Event.state == EventStateEnum.live))
        for event in live_events.scalars().all():
            await db.refresh(event, ["items"])
            for item in event.items:
                await redis_client.set(f"item:{item.id}:stock", item.current_stock)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_demo_data()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="High-concurrency flash sale API for SwiftDrop",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(event_router.router, prefix="/api/v1/events", tags=["events"])
app.include_router(purchase_router.router, prefix="/api/v1/purchases", tags=["purchases"])
app.include_router(profile_router.router, prefix="/api/v1/profile", tags=["profile"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

from fastapi import WebSocketDisconnect
from app.core.websocket_manager import manager

@app.websocket("/ws/events/{event_id}")
async def event_websocket(websocket: WebSocket, event_id: int):
    await manager.connect(websocket, event_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, event_id)
