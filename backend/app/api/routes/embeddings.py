"""Embeddings router – generate and cache embeddings for items"""
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger("findit.embeddings")
router = APIRouter()


class EmbedImageRequest(BaseModel):
    image_url: str
    item_id: Optional[str] = None


class EmbedTextRequest(BaseModel):
    title: str
    category: str = ""
    brand: str = ""
    color: str = ""
    description: str = ""


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int


@router.post("/image", response_model=EmbeddingResponse)
async def embed_image(request: Request, body: EmbedImageRequest):
    """Generate CLIP image embedding for a given image URL."""
    raise HTTPException(status_code=501, detail="ML features disabled for Free Tier")


@router.post("/text", response_model=EmbeddingResponse)
async def embed_text(request: Request, body: EmbedTextRequest):
    """Generate CLIP text embedding for item metadata."""
    raise HTTPException(status_code=501, detail="ML features disabled for Free Tier")
