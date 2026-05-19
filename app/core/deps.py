import uuid
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.users import User

# OAuth2 scheme looking for 'Authorization: Bearer <token>'
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/otp/verify", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str | None = Depends(oauth2_scheme)
) -> User:
    """Dependency to retrieve the currently logged-in user from the JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
        
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception
        
    # Fetch user from DB
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user


class RoleChecker:
    """Dependency factory to enforce role-based access control (RBAC)."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' does not have permission to access this resource. Allowed: {self.allowed_roles}",
            )
        return current_user
