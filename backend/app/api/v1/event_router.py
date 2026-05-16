from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domain.schemas import EventCreate, EventResponse, EventUpdate, EventStateUpdate
from app.domain.models import User
from app.api.dependencies import get_current_user, get_current_admin
from app.services.event_service import EventService

router = APIRouter()

# --- Customer / General Routes ---

@router.get("", response_model=List[EventResponse])
async def list_events(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Customers can browse all events."""
    return await EventService.get_all_events(db)

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get single event details and items."""
    return await EventService.get_event_by_id(db, event_id)

# --- Admin Routes ---

@router.post("", response_model=EventResponse)
async def create_event(event_in: EventCreate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    """Admin creates a new locked event."""
    return await EventService.create_event(db, event_in)

@router.put("/{event_id}", response_model=EventResponse)
async def update_event(event_id: int, event_in: EventUpdate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    """Admin updates a locked event."""
    return await EventService.update_event(db, event_id, event_in)

@router.post("/{event_id}/state", response_model=EventResponse)
async def update_event_state(event_id: int, state_in: EventStateUpdate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    """Admin forces event state change (e.g. to Live or Closed)."""
    return await EventService.change_event_state(db, event_id, state_in)
