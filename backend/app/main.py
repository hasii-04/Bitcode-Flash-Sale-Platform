import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth_router, event_router, purchase_router, profile_router
from app.core.websocket_manager import manager
from app.core.database import AsyncSessionLocal
from app.services.event_service import EventService


async def event_scheduler():
    """Background loop: every 30 seconds, auto-open events whose time has come."""
    while True:
        await asyncio.sleep(30)
        try:
            async with AsyncSessionLocal() as db:
                await EventService.auto_activate_scheduled_events(db)
        except Exception as e:
            print(f"[Scheduler] Error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background scheduler
    task = asyncio.create_task(event_scheduler())
    yield
    task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="High-concurrency flash sale API for SwiftDrop",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(event_router.router, prefix="/api/v1/events", tags=["events"])
app.include_router(purchase_router.router, prefix="/api/v1/purchases", tags=["purchases"])
app.include_router(profile_router.router, prefix="/api/v1/profile", tags=["profile"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.websocket("/ws/events/{event_id}")
async def event_websocket(websocket: WebSocket, event_id: int):
    await manager.connect(websocket, event_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, event_id)
