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
    
    # OTP
    MOCK_OTP: str = "123456"
    
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


settings = Settings()

