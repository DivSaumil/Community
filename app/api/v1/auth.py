import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.crud import users as crud_users
from app.models.users import User
from app.schemas.users import OTPRequest, OTPVerify, Token, UserCreate

router = APIRouter()


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(payload: OTPRequest, request: Request):
    """
    Generate and send an OTP to the provided email address.
    """
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    # Apply backend rate limiting per email and IP
    if not await security.check_otp_rate_limit(email, request.client.host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try again after 5 minutes."
        )
        
    # Generate OTP (stored in Redis or in-memory fallback)
    otp = await security.generate_otp(email)
    
    # Print the mock OTP to standard output in development mode instead of exposing it in JSON
    if settings.ENVIRONMENT == "development":
        print(f"\n[DEVELOPMENT MOCK OTP] Generated OTP for {email}: {otp}\n")
        
    return {
        "message": f"OTP sent successfully to {email}",
        "otp": "sent"
    }


@router.post("/otp/verify", response_model=Token)
async def verify_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify the OTP. If correct, generate a JWT.
    Auto-registers the user as a resident if not already present.
    """
    email = payload.email.strip().lower()
    otp = payload.otp.strip()
    
    if not await security.verify_otp(email, otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP",
        )
        
    # Obtain transaction-level advisory lock to serialize auto-registration checks
    # and prevent race conditions when checking user count for first-time admin promotion.
    await db.execute(text("SELECT pg_advisory_xact_lock(112233)"))
    
    # Retrieve user
    user = await crud_users.get_user_by_email(db, email)
    
    if not user:
        # Check if this is the first user in the DB. If so, make them an Admin.
        # Otherwise, make them a resident.
        res = await db.execute(select(func.count(User.id)))
        count = res.scalar() or 0
        
        role = "admin" if count == 0 else "resident"
        user = await crud_users.create_user(
            db, 
            UserCreate(
                email=email, 
                name=f"Demo {role.capitalize()} ({email.split('@')[0]})", 
                role=role
            )
        )
        await db.commit()  # commit within lock to ensure count is updated for others
        print(f"[AUTH] Auto-registered new user: {email} with role: {role}")
        
    # Generate JWT access and refresh tokens
    access_token = security.create_access_token(subject=user.id, roles=user.role)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token and refresh token.
    """
    payload = security.verify_refresh_token(refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
        
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )
        
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )
        
    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
        
    # Generate new tokens
    access_token = security.create_access_token(subject=user.id, roles=user.role)
    new_refresh_token = security.create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
    }
