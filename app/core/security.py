import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from jose import jwt, JWTError
from app.core.config import settings

# In-memory store for active OTPs mapping phone number -> OTP string
OTP_STORE: Dict[str, str] = {}


def create_access_token(subject: str | Any, roles: str = "resident", expires_delta: timedelta = None) -> str:
    """Generate a JWT access token for a subject (usually user ID)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "role": roles}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any] | None:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp(phone: str) -> str:
    """
    Generate a 6-digit OTP, store it in-memory, and return it.
    If phone is a test number, we can use the default mock OTP.
    """
    # Always allow 123456 as a default dev OTP
    otp = str(random.randint(100000, 999999))
    OTP_STORE[phone] = otp
    print(f"\n[SMS SERVICE MOCK] Sent OTP {otp} to {phone}\n")
    return otp


def verify_otp(phone: str, otp: str) -> bool:
    """Verify if the OTP matches the one sent, or the master dev OTP."""
    # Allow master mock OTP in development
    if settings.ENVIRONMENT == "development" and otp == settings.MOCK_OTP:
        return True
        
    stored_otp = OTP_STORE.get(phone)
    if stored_otp and stored_otp == otp:
        # Clear OTP after successful verification
        OTP_STORE.pop(phone, None)
        return True
        
    return False
