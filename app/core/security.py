import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from jose import jwt, JWTError
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback in-memory store for active OTPs mapping phone number -> {"otp": otp, "expires_at": datetime}
OTP_STORE: Dict[str, Dict[str, Any]] = {}

# Single Redis client instance
_redis_client: redis.Redis | None = None
_redis_unreachable = False


async def get_redis_client() -> redis.Redis | None:
    global _redis_client, _redis_unreachable
    if _redis_unreachable:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Ping connection to check if server is running
        await client.ping()
        _redis_client = client
        logger.info("Connected to Redis successfully for OTP storage.")
        return _redis_client
    except Exception as e:
        logger.warning(f"Could not connect to Redis at {settings.REDIS_URL}: {e}. Falling back to in-memory OTP storage.")
        _redis_unreachable = True
        return None


def create_access_token(subject: str | Any, roles: str = "resident", expires_delta: timedelta = None) -> str:
    """Generate a JWT access token for a subject (usually user ID)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "role": roles, "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    """Generate a JWT refresh token for a subject (usually user ID)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any] | None:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") == "refresh":
            return None
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Dict[str, Any] | None:
    """Decode and verify a JWT refresh token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


async def generate_otp(phone: str) -> str:
    """
    Generate a 6-digit OTP, store it in Redis or in-memory fallback with a 5-minute TTL, and return it.
    """
    otp = str(random.randint(100000, 999999))
    redis_client = await get_redis_client()
    if redis_client:
        try:
            await redis_client.setex(f"otp:{phone}", 300, otp)
            logger.info(f"OTP stored in Redis for {phone}")
        except Exception as e:
            logger.error(f"Failed to store OTP in Redis: {e}. Falling back to in-memory.")
            OTP_STORE[phone] = {
                "otp": otp,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
            }
    else:
        OTP_STORE[phone] = {
            "otp": otp,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        }
    print(f"\n[SMS SERVICE MOCK] Sent OTP {otp} to {phone}\n")
    return otp


async def verify_otp(phone: str, otp: str) -> bool:
    """Verify if the OTP matches the one sent, or the master dev OTP."""
    # Allow master mock OTP in development
    if settings.ENVIRONMENT == "development" and otp == settings.MOCK_OTP:
        return True

    redis_client = await get_redis_client()
    if redis_client:
        try:
            stored_otp = await redis_client.get(f"otp:{phone}")
            if stored_otp and stored_otp == otp:
                await redis_client.delete(f"otp:{phone}")
                return True
        except Exception as e:
            logger.error(f"Failed to verify/delete OTP in Redis: {e}. Checking in-memory fallback.")
            
    # Check in-memory fallback
    stored_entry = OTP_STORE.get(phone)
    if stored_entry:
        if datetime.now(timezone.utc) > stored_entry["expires_at"]:
            OTP_STORE.pop(phone, None)
            return False
        if stored_entry["otp"] == otp:
            OTP_STORE.pop(phone, None)
            return True
            
    return False
