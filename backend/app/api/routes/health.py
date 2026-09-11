"""Health check router"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    model_loaded: bool
    device: str
    clip_model: str


@router.get("/api/v1/health", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint for Docker and load balancers."""
    from app.core.config import settings
    clip = getattr(request.app.state, "clip", None)
    return HealthResponse(
        status="ok",
        service="findit-api",
        model_loaded=False,
        device="cpu",
        clip_model="disabled_for_free_tier",
    )


@router.get("/")
async def root():
    return {"message": "FindIt AI Service", "version": "1.0.0", "docs": "/docs"}
