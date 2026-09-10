from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models import User, Item, Match, MatchStatus, Role
from app.schemas.match import (
    MatchResponse, MatchListResponse, MatchAnalyzeResponse, MatchStatusUpdate,
    MatchStatusEnum
)
from app.ai.matching_service import matching_service
from app.core.config import settings

router = APIRouter()

def helper_format_match(match: Match) -> dict:
    """Format Match object into JSON response dictionary with alias properties."""
    return {
        "id": match.id,
        "_id": match.id,
        "lost_item_id": match.lost_item_id,
        "found_item_id": match.found_item_id,
        "score": match.score,
        "similarity_score": match.score,
        "combined_score": match.score,
        "image_score": match.image_score,
        "text_score": match.text_score,
        "status": match.status.value if hasattr(match.status, "value") else str(match.status),
        "created_at": match.created_at,
        "createdAt": match.created_at,
        "updated_at": match.updated_at,
        "lost_item": match.lost_item,
        "found_item": match.found_item
    }

# ─── 1. Trigger AI Match Analysis for Item ────────────────────────────────────
@router.post("/item/{item_id}/analyze", response_model=MatchAnalyzeResponse)
async def analyze_item_matches(
    item_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    threshold: Optional[float] = Query(None, description="Custom similarity threshold"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger AI similarity analysis for a reported lost or found item.
    Compares against active candidates using CLIP image & text embeddings.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if item.reported_by != current_user.id and current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to trigger analysis for this item"
        )

    clip = getattr(request.app.state, "clip", None)
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI CLIP model service is not available"
        )

    # Perform analysis
    matches = await matching_service.analyze_item_and_find_matches(
        item_id=item_id,
        clip=clip,
        db=db,
        threshold=threshold
    )

    formatted_matches = [helper_format_match(m) for m in matches]

    return MatchAnalyzeResponse(
        item_id=item_id,
        total_candidates=len(matches),
        matches_created=len(matches),
        matches=formatted_matches
    )

# ─── 2. List User Matches ──────────────────────────────────────────────────────
@router.get("", response_model=MatchListResponse)
@router.get("/", response_model=MatchListResponse)
def get_user_matches(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: pending, confirmed, rejected"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all AI matches related to items reported by the current user.
    Only returns matches involving the authenticated user's items.
    """
    # Query matches where lost_item or found_item belongs to current_user
    query = (
        db.query(Match)
        .join(Item, or_(Match.lost_item_id == Item.id, Match.found_item_id == Item.id))
        .options(
            joinedload(Match.lost_item).joinedload(Item.reporter),
            joinedload(Match.found_item).joinedload(Item.reporter)
        )
        .filter(Item.reported_by == current_user.id)
    )

    if status_filter:
        try:
            query = query.filter(Match.status == MatchStatus(status_filter.lower()))
        except ValueError:
            pass

    matches = query.order_by(Match.score.desc()).all()
    formatted = [helper_format_match(m) for m in matches]

    return MatchListResponse(matches=formatted, total=len(formatted))

# ─── 3. Get Single Match Detail ────────────────────────────────────────────────
@router.get("/{match_id}", response_model=MatchResponse)
def get_match_by_id(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve single match details. Requires ownership of either involved item or admin privileges.
    """
    match = (
        db.query(Match)
        .options(
            joinedload(Match.lost_item).joinedload(Item.reporter),
            joinedload(Match.found_item).joinedload(Item.reporter)
        )
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    is_lost_owner = match.lost_item and match.lost_item.reported_by == current_user.id
    is_found_owner = match.found_item and match.found_item.reported_by == current_user.id
    is_admin = current_user.role == Role.admin

    if not (is_lost_owner or is_found_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this match"
        )

    return helper_format_match(match)

# ─── 4. Confirm Match ──────────────────────────────────────────────────────────
@router.post("/{match_id}/confirm", response_model=MatchResponse)
def confirm_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirm a match status to CONFIRMED.
    Requires ownership of an item involved in the match.
    """
    match = (
        db.query(Match)
        .options(
            joinedload(Match.lost_item),
            joinedload(Match.found_item)
        )
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    is_lost_owner = match.lost_item and match.lost_item.reported_by == current_user.id
    is_found_owner = match.found_item and match.found_item.reported_by == current_user.id
    is_admin = current_user.role == Role.admin

    if not (is_lost_owner or is_found_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this match"
        )

    match.status = MatchStatus.confirmed
    db.commit()
    db.refresh(match)
    return helper_format_match(match)

# ─── 5. Reject Match ───────────────────────────────────────────────────────────
@router.post("/{match_id}/reject", response_model=MatchResponse)
def reject_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a match status to REJECTED.
    Requires ownership of an item involved in the match.
    """
    match = (
        db.query(Match)
        .options(
            joinedload(Match.lost_item),
            joinedload(Match.found_item)
        )
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    is_lost_owner = match.lost_item and match.lost_item.reported_by == current_user.id
    is_found_owner = match.found_item and match.found_item.reported_by == current_user.id
    is_admin = current_user.role == Role.admin

    if not (is_lost_owner or is_found_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this match"
        )

    match.status = MatchStatus.rejected
    db.commit()
    db.refresh(match)
    return helper_format_match(match)
