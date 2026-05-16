from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from app.domain.models import RoleEnum, EventStateEnum, OrderStatusEnum

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    role: RoleEnum
    is_active: bool

    class Config:
        from_attributes = True

# --- Item Schemas ---
class ItemCreate(BaseModel):
    name: str
    unit_price: float
    initial_stock: int

class ItemResponse(BaseModel):
    id: int
    event_id: int
    name: str
    unit_price: float
    initial_stock: int
    current_stock: int

    class Config:
        from_attributes = True

# --- Event Schemas ---
class EventCreate(BaseModel):
    name: str
    cover_photo: Optional[str] = None
    go_live_time: datetime
    items: List[ItemCreate]

class EventUpdate(BaseModel):
    name: Optional[str] = None
    cover_photo: Optional[str] = None
    go_live_time: Optional[datetime] = None

class EventStateUpdate(BaseModel):
    state: EventStateEnum

class EventResponse(BaseModel):
    id: int
    name: str
    cover_photo: Optional[str]
    go_live_time: datetime
    state: EventStateEnum
    items: List[ItemResponse] = []

    class Config:
        from_attributes = True

# --- Purchase Schemas ---
class PurchaseRequest(BaseModel):
    event_id: int
    item_id: int

class PurchaseResponse(BaseModel):
    success: bool
    message: str
    status_code: int

# --- Order Schemas ---
class OrderHistoryResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    price_paid: float
    status: OrderStatusEnum
    created_at: datetime
    
    class Config:
        from_attributes = True
