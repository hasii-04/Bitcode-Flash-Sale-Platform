from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.domain.schemas import UserCreate, UserLogin, Token, UserResponse, ChangePasswordRequest, CreateAdminRequest
from app.domain.models import User, RoleEnum
from app.services.auth_service import AuthService
from app.api.dependencies import get_current_user, get_current_admin

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Public registration — always creates a customer account."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_in.email,
        display_name=user_in.display_name,
        hashed_password=AuthService.get_password_hash(user_in.password),
        role=RoleEnum.customer
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and receive a JWT access token."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()

    if not user or not AuthService.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated. Contact support.")

    access_token = AuthService.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return current_user

@router.post("/change-password", status_code=200)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change password — requires current password. New password must be strong."""
    if not AuthService.verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = AuthService.get_password_hash(body.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.post("/admin/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    user_in: CreateAdminRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    """Admin-only: create another admin account."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_admin = User(
        email=user_in.email,
        display_name=user_in.display_name,
        hashed_password=AuthService.get_password_hash(user_in.password),
        role=RoleEnum.admin
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin
