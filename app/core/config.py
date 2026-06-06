from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "Society / RWA Management API"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/rwa_management"
    
    # Redis for OTP
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Authentication
    SECRET_KEY: str  # Enforced: No default fallback, must be in env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived (15 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7    # Long-lived (7 days)

    # Uvicorn workers — set via WORKERS env var in production
    # Recommended: (2 × vCPU) + 1
    WORKERS: int = 3

    # OTP — leave empty in production to enforce real OTP flow
    MOCK_OTP: str = ""
    
    # SMTP Email Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "Co-Habitat"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str], None]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        return []

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if not v:
            return v
        # Convert postgres:// or postgresql:// to postgresql+asyncpg:// for asyncpg driver
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # asyncpg compatibility: replace sslmode=require with ssl=require
        if "sslmode=" in v:
            v = v.replace("sslmode=", "ssl=")
        return v


settings = Settings()

