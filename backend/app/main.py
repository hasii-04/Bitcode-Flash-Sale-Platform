"""
SwiftDrop — FastAPI application entry-point
==========================================
Changes in this revision
------------------------
* Lifespan: loads the Random-Forest bot-detection model (bot_model.joblib) into
  app.state.bot_model at startup.  The model is trained by ml/train.py.
* BotDetectionMiddleware: inspects every POST /api/v1/purchases/* request,
  extracts behavioural features from headers, and rejects suspected bots with
  HTTP 403 Forbidden before the request reaches any route handler.
"""

from __future__ import annotations

import json
import pathlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable

import numpy as np
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import Base, engine, AsyncSessionLocal
from app.core.config import settings
from app.api.v1 import auth_router, event_router, purchase_router, profile_router
from app.domain.models import Event, EventStateEnum, Item, RoleEnum, User
from app.services.auth_service import AuthService
from app.core.redis_client import redis_client

# ── Model path ─────────────────────────────────────────────────────────────────
_MODEL_PATH = pathlib.Path(__file__).parent.parent / "ml" / "bot_model.joblib"
_FEATURES   = ["req_per_sec", "click_latency_ms", "is_mobile", "header_consistency"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Lifespan
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
                cover_photo=(
                    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e"
                    "?auto=format&fit=crop&w=1200&q=80"
                ),
                go_live_time=datetime.now(timezone.utc) - timedelta(minutes=5),
                state=EventStateEnum.live,
            )
            event.items = [
                Item(name="Imported Smart Watch",        unit_price=79,  initial_stock=150, current_stock=150),
                Item(name="Noise Canceling Headphones",  unit_price=129, initial_stock=120, current_stock=120),
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
    # ── DB tables ──────────────────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_demo_data()

    # ── ML model ───────────────────────────────────────────────────────────────
    if _MODEL_PATH.exists():
        import joblib  # lazy import — only needed at runtime
        app.state.bot_model = joblib.load(_MODEL_PATH)
        print(f"[ML] Bot-detection model loaded from {_MODEL_PATH}")
    else:
        app.state.bot_model = None
        print(
            f"[ML] WARNING: model not found at {_MODEL_PATH}. "
            "Run `python -m ml.train` to generate it. Bot detection is DISABLED."
        )

    yield  # ← app is running

    # Shutdown: nothing special needed for the model (it's in-memory)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Bot-detection middleware
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BotDetectionMiddleware(BaseHTTPMiddleware):
    """
    Intercepts POST requests to /api/v1/purchases/*.

    Expected request headers (set by clients/test harness):
        X-Req-Per-Sec       float   requests per second from this client
        X-Click-Latency-Ms  float   milliseconds between UI click and request
        X-Is-Mobile         0 | 1   whether the client is a mobile device
        X-Header-Consistency 0-1    fraction of expected browser headers present

    If any header is missing a safe default is used (human-like value) so that
    ordinary API consumers without the headers are never accidentally blocked.
    """

    # Probability threshold above which a request is classified as a bot
    BOT_THRESHOLD: float = 0.5

    async def dispatch(self, request: Request, call_next: Callable):
        # Only intercept purchase endpoints
        if not request.url.path.startswith("/api/v1/purchases"):
            return await call_next(request)

        model = getattr(request.app.state, "bot_model", None)
        if model is None:
            # Model not loaded — fail open (don't block legitimate traffic)
            return await call_next(request)

        # ── Extract features from headers ──────────────────────────────────────
        try:
            req_per_sec         = float(request.headers.get("X-Req-Per-Sec",        "1.0"))
            click_latency_ms    = float(request.headers.get("X-Click-Latency-Ms",   "3000.0"))
            is_mobile           = float(request.headers.get("X-Is-Mobile",          "0"))
            header_consistency  = float(request.headers.get("X-Header-Consistency", "0.9"))
        except (ValueError, TypeError):
            # Malformed headers — treat as suspicious
            req_per_sec        = 50.0
            click_latency_ms   = 10.0
            is_mobile          = 0.0
            header_consistency = 0.1

        features = np.array([[req_per_sec, click_latency_ms, is_mobile, header_consistency]])
        bot_probability = model.predict_proba(features)[0][1]  # P(is_bot=1)

        if bot_probability >= self.BOT_THRESHOLD:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied: automated bot traffic detected.",
                    "bot_probability": round(float(bot_probability), 4),
                },
            )

        # Attach score to request state for downstream logging if desired
        request.state.bot_probability = round(float(bot_probability), 4)
        return await call_next(request)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Application
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="High-concurrency flash sale API for SwiftDrop",
    lifespan=lifespan,
)

# ── Middleware stack (order matters: outermost first) ──────────────────────────
app.add_middleware(BotDetectionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router.router,     prefix="/api/v1/auth",      tags=["auth"])
app.include_router(event_router.router,    prefix="/api/v1/events",    tags=["events"])
app.include_router(purchase_router.router, prefix="/api/v1/purchases", tags=["purchases"])
app.include_router(profile_router.router,  prefix="/api/v1/profile",   tags=["profile"])


@app.get("/health")
def health_check():
    model_loaded = getattr(app.state, "bot_model", None) is not None
    return {"status": "ok", "bot_model_loaded": model_loaded}


# ── WebSocket ──────────────────────────────────────────────────────────────────
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
