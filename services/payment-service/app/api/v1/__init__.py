"""API v1 router configuration."""

from app.api.v1.endpoints import payments
from fastapi import APIRouter

api_router = APIRouter()

# Include payment endpoints
api_router.include_router(
    payments.router, prefix="/payments", tags=["Payments"]
)
