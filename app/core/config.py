from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "Society / RWA Management API"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/rwa_management"
    
    # JWT Authentication
    SECRET_KEY: str = "super_secret_key_rwa_app_development_2026_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # OTP
    MOCK_OTP: str = "123456"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]


settings = Settings()
