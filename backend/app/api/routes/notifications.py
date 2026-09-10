from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models import User
from app.schemas.notification import (
    NotificationResponse, NotificationListResponse, UnreadCountResponse
)
from app.services.notification_service import notification_service

router = APIRouter()

def helper_format_notification(notif) -> dict:
    """Format notification record into dictionary matching NotificationResponse schema."""
    return {
        "id": notif.id,
        "_id": notif.id,
        "user_id": notif.user_id,
        "title": notif.title,
        "message": notif.message,
        "type": notif.type.value if hasattr(notif.type, "value") else str(notif.type),
        "is_read": notif.is_read,
        "related_id": notif.related_id,
        "related_item_id": getattr(notif, "related_item_id", None),
        "related_match_id": getattr(notif, "related_match_id", None),
        "created_at": notif.created_at,
        "createdAt": notif.created_at,
    }

# ─── 1. Get Unread Notification Count ──────────────────────────────────────────
@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get count of unread notifications for the current authenticated user.
    """
    count = notification_service.get_unread_count(db, current_user.id)
    return UnreadCountResponse(unread_count=count)

# ─── 2. List User Notifications ───────────────────────────────────────────────
@router.get("", response_model=NotificationListResponse)
@router.get("/", response_model=NotificationListResponse)
def list_user_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated notifications for the current authenticated user.
    Users can only see their own notifications.
    """
    skip = (page - 1) * limit
    notifications, total = notification_service.get_user_notifications(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    formatted = [helper_format_notification(n) for n in notifications]
    return NotificationListResponse(notifications=formatted, total=total)

# ─── 3. Mark Notification as Read ────────────────────────────────────────────
@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a notification as read. Users cannot modify another user's notifications.
    """
    updated_notif = notification_service.mark_as_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if not updated_notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )
    return helper_format_notification(updated_notif)
