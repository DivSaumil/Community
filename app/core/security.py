import logging
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import anyio
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


async def send_otp_email(email: str, otp: str) -> bool:
    """
    Asynchronously send an OTP email using standard SMTP.
    """
    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD or not from_email:
        logger.warning(f"SMTP credentials not fully configured. Falling back to console logging. (Email: {email}, OTP: {otp})")
        return False
        
    try:
        # Construct email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{otp} is your Co-Habitat verification code"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
        msg["To"] = email
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e1e1e1; border-radius: 8px; background-color: #fcfcfc;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #4A90E2; margin-top: 10px;">Co-Habitat</h2>
                    <p style="color: #888; font-size: 14px;">Society & RWA Management Platform</p>
                </div>
                <hr style="border: 0; border-top: 1px solid #eee; margin-bottom: 20px;">
                <p>Hello,</p>
                <p>We received a request to log in to your Co-Habitat account. Use the following verification code to sign in. This code is valid for 5 minutes.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #4A90E2; background-color: #eef5fc; padding: 12px 24px; border-radius: 6px; border: 1px dashed #4A90E2;">{otp}</span>
                </div>
                <p style="color: #666; font-size: 14px;">If you did not request this code, you can safely ignore this email.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px; margin-bottom: 20px;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated email. Please do not reply directly.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(f"Your Co-Habitat OTP is {otp}", "plain"))
        msg.attach(MIMEText(html, "html"))
        
        # Run standard blocking smtplib in a worker thread to keep FastAPI async loop non-blocking
        def _send():
            if settings.SMTP_SSL:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()
            
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(from_email, email, msg.as_string())
            server.quit()
            
        await anyio.to_thread.run_sync(_send)
        logger.info(f"Successfully sent OTP email to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False


async def generate_otp(email: str) -> str:
    """
    Generate a 6-digit OTP, store it in Redis or in-memory fallback with a 5-minute TTL,
    send it to the user's email, and return it.
    """
    otp = str(random.randint(100000, 999999))
    redis_client = await get_redis_client()
    if redis_client:
        try:
            await redis_client.setex(f"otp:{email}", 300, otp)
            logger.info(f"OTP stored in Redis for {email}")
        except Exception as e:
            logger.error(f"Failed to store OTP in Redis: {e}. Falling back to in-memory.")
            OTP_STORE[email] = {
                "otp": otp,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
            }
    else:
        OTP_STORE[email] = {
            "otp": otp,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        
    # Send email in background
    sent = await send_otp_email(email, otp)
    if not sent:
        print(f"\n[EMAIL MOCK] Sent OTP {otp} to {email}\n")
        
    return otp


async def verify_otp(email: str, otp: str) -> bool:
    """Verify if the OTP matches the one sent, or the master dev OTP."""
    # Allow master mock OTP in development
    if settings.ENVIRONMENT == "development" and otp == settings.MOCK_OTP:
        return True

    redis_client = await get_redis_client()
    if redis_client:
        try:
            stored_otp = await redis_client.get(f"otp:{email}")
            if stored_otp and stored_otp == otp:
                await redis_client.delete(f"otp:{email}")
                return True
        except Exception as e:
            logger.error(f"Failed to verify/delete OTP in Redis: {e}. Checking in-memory fallback.")
            
    # Check in-memory fallback
    stored_entry = OTP_STORE.get(email)
    if stored_entry:
        if datetime.now(timezone.utc) > stored_entry["expires_at"]:
            OTP_STORE.pop(email, None)
            return False
        if stored_entry["otp"] == otp:
            OTP_STORE.pop(email, None)
            return True
            
    return False


# Rate limiting store for in-memory fallback
RATE_LIMIT_STORE: Dict[str, list[datetime]] = {}


def check_in_memory_limit(key: str, limit: int, window: int = 300) -> bool:
    """Check in-memory rate limits."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window)
    
    # Get and clean old requests
    requests = RATE_LIMIT_STORE.get(key, [])
    requests = [t for t in requests if t > cutoff]
    
    if len(requests) >= limit:
        RATE_LIMIT_STORE[key] = requests
        return False
        
    requests.append(now)
    RATE_LIMIT_STORE[key] = requests
    return True


async def check_otp_rate_limit(email: str, ip: str) -> bool:
    """
    Rate limit OTP requests:
    - Max 3 requests per 5 minutes per email
    - Max 5 requests per 5 minutes per IP
    """
    redis_client = await get_redis_client()
    if redis_client:
        try:
            email_key = f"rl:email:{email}"
            ip_key = f"rl:ip:{ip}"
            
            # Increment and set TTL if new
            e_count = await redis_client.incr(email_key)
            if e_count == 1:
                await redis_client.expire(email_key, 300)
                
            ip_count = await redis_client.incr(ip_key)
            if ip_count == 1:
                await redis_client.expire(ip_key, 300)
                
            if e_count > 3 or ip_count > 5:
                return False
            return True
        except Exception as e:
            logger.error(f"Redis rate limiting failed: {e}. Falling back to in-memory.")
            
    # In-memory fallback
    email_ok = check_in_memory_limit(f"email:{email}", limit=3)
    ip_ok = check_in_memory_limit(f"ip:{ip}", limit=5)
    return email_ok and ip_ok

