from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.crud import users as crud_users
from app.schemas.users import OTPRequest, OTPVerify, Token, UserCreate

router = APIRouter()


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(payload: OTPRequest):
    """
    Generate and 'send' a mock OTP to the provided phone number.
    In development, the OTP is printed to the terminal logs.
    """
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
        
    # Generate OTP (stored in security.OTP_STORE)
    otp = security.generate_otp(phone)
    
    return {
        "message": f"OTP sent successfully to {phone}",
        "otp": otp if settings.ENVIRONMENT == "development" else "sent"
    }


@router.post("/otp/verify", response_model=Token)
async def verify_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    """
    Verify the OTP. If correct, generate a JWT.
    Auto-registers the user as a resident if not already present.
    """
    phone = payload.phone.strip()
    otp = payload.otp.strip()
    
    if not security.verify_otp(phone, otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number or OTP",
        )
        
    # Retrieve user
    user = await crud_users.get_user_by_phone(db, phone)
    
    if not user:
        # Check if this is the first user in the DB. If so, make them an Admin.
        # Otherwise, make them a resident.
        from sqlalchemy import select, func
        from app.models.users import User
        res = await db.execute(select(func.count(User.id)))
        count = res.scalar() or 0
        
        role = "admin" if count == 0 else "resident"
        user = await crud_users.create_user(
            db, 
            UserCreate(
                phone=phone, 
                name=f"Demo {role.capitalize()} {phone[-4:]}", 
                role=role
            )
        )
        print(f"[AUTH] Auto-registered new user: {phone} with role: {role}")
        
    # Generate JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, roles=user.role, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
    }
