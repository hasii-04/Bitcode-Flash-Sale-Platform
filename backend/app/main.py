from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth_router, event_router, purchase_router, profile_router
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="High-concurrency flash sale API for SwiftDrop"
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
