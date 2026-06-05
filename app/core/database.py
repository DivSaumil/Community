from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create async engine for PostgreSQL connection
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True to log SQL statements
    pool_pre_ping=True,  # Verify connections are alive before use
    # Connection pool tuning for 2GB Droplet with 3 Uvicorn workers:
    # Each worker gets pool_size connections — total max = workers × (pool_size + max_overflow)
    pool_size=5,           # Persistent connections per worker
    max_overflow=10,       # Extra connections allowed under burst load
    pool_timeout=30,       # Seconds to wait for a connection before raising
    pool_recycle=1800,     # Recycle connections every 30 min (avoids stale conn issues)
)

# Async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get db session in FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
