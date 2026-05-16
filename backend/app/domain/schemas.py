from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional, List
from app.domain.models import RoleEnum, EventStateEnum, OrderStatusEnum
import re

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None

class CreateAdminRequest(BaseModel):
    email: str
    display_name: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserResponse(BaseModel):
    id: int
    email: str
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
    item_name: str
    event_name: str
    quantity: int
    price_paid: float
    status: OrderStatusEnum
    created_at: datetime

    class Config:
        from_attributes = True
