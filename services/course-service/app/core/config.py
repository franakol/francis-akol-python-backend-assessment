"""Configuration settings for Course Service."""

import json
from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "Course Service"
    SERVICE_NAME: str = "course-service"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://course_user:course_password@localhost:5432/course_service_db"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"
    REDIS_CACHE_TTL: int = 300  # 5 minutes
    REDIS_DECODE_RESPONSES: bool = True

    # CORS - use Any to prevent pydantic-settings from failing on parsing
    CORS_ORIGINS: Any = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
    ]

    # User Service
    USER_SERVICE_URL: str = "http://localhost:8001"

    # OpenAI for AI Recommendations
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"

    # File Storage
    FILE_STORAGE_PATH: str = "/tmp/mlh-uploads"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS_ORIGINS from various formats."""
        default = ["http://localhost:3000", "http://localhost:8000"]
        if v is None:
            return default
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [
                origin.strip() for origin in v.split(",") if origin.strip()
            ]
        return default

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="allow"
    )


settings = Settings()
