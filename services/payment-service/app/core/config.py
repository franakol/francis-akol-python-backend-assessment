"""Configuration settings for Payment Service."""

import json
from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "Payment Service"
    SERVICE_NAME: str = "payment-service"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://payment_user:payment_password@localhost:5432/payment_service_db"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # CORS - use Any to prevent pydantic-settings from failing on parsing
    CORS_ORIGINS: Any = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:8003",
        "http://localhost:8004",
    ]

    # External Services
    USER_SERVICE_URL: str = "http://localhost:8001"
    COURSE_SERVICE_URL: str = "http://localhost:8002"
    ENROLLMENT_SERVICE_URL: str = "http://localhost:8003"

    # Payment Gateway (Stripe mock)
    STRIPE_SECRET_KEY: str = "sk_test_mock_key"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_mock_key"
    STRIPE_WEBHOOK_SECRET: str = "whsec_test_mock_secret"

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
