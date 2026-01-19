from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from models.database import get_db
from models.user import User
from api.schemas import UserCreate, UserLogin, UserResponse, Token, TokenData, PasswordChange
from utils.security import hash_password, verify_password, create_access_token, decode_token
from config.settings import get_settings
from api.middleware.auth import get_current_user as get_current_user_from_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        hashed_password=hash_password(user.password),
        role=user.role if hasattr(user, 'role') else "customer",
        is_active=True,
        is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=dict)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@router.get("/me", response_model=UserResponse)
async def read_me(current_user: User = Depends(get_current_user_from_token)):
    """Get current user information (Authorization: Bearer <token>)"""
    return current_user

@router.post("/refresh")
async def refresh_token(token: str):
    """Refresh access token"""
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_change: PasswordChange,
    db: Session = Depends(get_db),
    token: str = None
):
    """Change user password"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify old password
    if not verify_password(password_change.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )
    
    # Update password
    user.hashed_password = hash_password(password_change.new_password)
    db.commit()
    
    return {"detail": "Password changed successfully"}
