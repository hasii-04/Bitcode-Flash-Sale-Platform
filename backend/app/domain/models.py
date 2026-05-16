import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class RoleEnum(str, enum.Enum):
    admin = "admin"
    customer = "customer"

class EventStateEnum(str, enum.Enum):
    locked = "locked"
    live = "live"
    closed = "closed"

class OrderStatusEnum(str, enum.Enum):
    reserved = "reserved"
    confirmed = "confirmed"
    cancelled = "cancelled"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.customer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    orders = relationship("Order", back_populates="user")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cover_photo = Column(String)
    go_live_time = Column(DateTime(timezone=True), nullable=False)
    state = Column(Enum(EventStateEnum), default=EventStateEnum.locked, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("Item", back_populates="event", cascade="all, delete-orphan")

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    initial_stock = Column(Integer, nullable=False)
    current_stock = Column(Integer, nullable=False)

    event = relationship("Event", back_populates="items")
    orders = relationship("Order", back_populates="item")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    price_paid = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.reserved, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="orders")
    item = relationship("Item", back_populates="orders")
