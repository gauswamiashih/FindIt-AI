"""
Match Router – POST /match
Accepts a found item's images + metadata and compares against
a list of lost item candidates, returning sorted similarity scores.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from app.core.config import settings

logger = logging.getLogger("findit.match")
router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LostItemCandidate(BaseModel):
    item_id: str
    image_urls: List[str]
    title: str = ""
    category: str = ""
    brand: str = ""
    color: str = ""
    description: str = ""


class MatchRequest(BaseModel):
    found_item_id: str
    found_image_urls: List[str]
    found_title: str = ""
    found_category: str = ""
    found_brand: str = ""
    found_color: str = ""
    found_description: str = ""
    lost_item_candidates: List[LostItemCandidate]
    threshold: float = settings.SIMILARITY_THRESHOLD


class MatchResult(BaseModel):
    item_id: str
    similarity_score: float
    is_match: bool


class MatchResponse(BaseModel):
    found_item_id: str
    matches: List[MatchResult]
    total_candidates: int
    matches_found: int
    threshold: float


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=MatchResponse)
async def match_items(request: Request, body: MatchRequest):
    """ML features disabled for Free Tier."""
    logger.info("Skipping matching: ML features disabled for Free Tier.")
    return MatchResponse(
        found_item_id=body.found_item_id,
        matches=[],
        total_candidates=len(body.lost_item_candidates),
        matches_found=0,
        threshold=body.threshold,
    )


@router.post("/single-image")
async def match_single_image(
    request: Request,
    image: UploadFile = File(...),
    item_ids: str = Form(...),          # comma-separated item IDs
    image_urls: str = Form(...),        # JSON array of arrays
):
    """Upload a single image and match against pre-computed embeddings."""
    raise HTTPException(status_code=501, detail="ML features disabled for Free Tier")
