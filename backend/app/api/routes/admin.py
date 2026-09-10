from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, List, Dict, Any

from app.api.deps import get_current_admin_user
from app.db.database import get_db
from app.models import User, Item, Match, MatchStatus, ItemType, ItemStatus, Role

router = APIRouter()

# ─── 1. Real Database Statistics ──────────────────────────────────────────────
@router.get("/stats")
def get_admin_dashboard_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated database statistics for the admin dashboard.
    Only accessible by users with Role.admin.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_lost_items = db.query(func.count(Item.id)).filter(Item.item_type == ItemType.lost).scalar() or 0
    total_found_items = db.query(func.count(Item.id)).filter(Item.item_type == ItemType.found).scalar() or 0
    active_items = db.query(func.count(Item.id)).filter(Item.status == ItemStatus.active).scalar() or 0
    resolved_items = db.query(func.count(Item.id)).filter(Item.status == ItemStatus.resolved).scalar() or 0
    total_matches = db.query(func.count(Match.id)).scalar() or 0
    confirmed_matches = db.query(func.count(Match.id)).filter(Match.status == MatchStatus.confirmed).scalar() or 0

    return {
        "success": True,
        "data": {
            "totalUsers": total_users,
            "total_users": total_users,
            "totalLostItems": total_lost_items,
            "total_lost_items": total_lost_items,
            "totalFoundItems": total_found_items,
            "total_found_items": total_found_items,
            "activeItems": active_items,
            "active_items": active_items,
            "resolvedItems": resolved_items,
            "resolved_items": resolved_items,
            "totalMatches": total_matches,
            "total_matches": total_matches,
            "confirmedMatches": confirmed_matches,
            "confirmed_matches": confirmed_matches,
        }
    }

# ─── 2. List Users ────────────────────────────────────────────────────────────
@router.get("/users")
def get_admin_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Paginated user list for administrative management.
    """
    query = db.query(User)
    total = query.count()
    offset = (page - 1) * limit
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    formatted_users = [
        {
            "id": u.id,
            "_id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_verified": u.is_verified,
            "isVerified": u.is_verified,
            "avatar_url": u.avatar_url,
            "created_at": u.created_at,
            "createdAt": u.created_at,
        }
        for u in users
    ]

    return {
        "success": True,
        "data": {
            "users": formatted_users,
            "total": total,
            "page": page,
            "limit": limit
        }
    }

# ─── 3. List Items ────────────────────────────────────────────────────────────
@router.get("/items")
def get_admin_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Paginated items list for administrative moderation.
    """
    query = db.query(Item).options(joinedload(Item.reporter))
    total = query.count()
    offset = (page - 1) * limit
    items = query.order_by(Item.created_at.desc()).offset(offset).limit(limit).all()

    formatted_items = [
        {
            "id": i.id,
            "_id": i.id,
            "title": i.title,
            "category": i.category,
            "item_type": i.item_type.value if hasattr(i.item_type, "value") else str(i.item_type),
            "type": i.type,
            "status": i.status.value if hasattr(i.status, "value") else str(i.status),
            "reported_by": i.reported_by,
            "created_at": i.created_at,
            "createdAt": i.created_at,
            "reporter": {
                "id": i.reporter.id,
                "name": i.reporter.name,
                "email": i.reporter.email
            } if i.reporter else None
        }
        for i in items
    ]

    return {
        "success": True,
        "data": {
            "items": formatted_items,
            "total": total,
            "page": page,
            "limit": limit
        }
    }

# ─── 4. Update User Role / Status ──────────────────────────────────────────────
@router.patch("/users/{user_id}/status")
@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: Dict[str, Any],
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update a user's role or status.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = payload.get("role")
    if new_role:
        try:
            user.role = Role(new_role.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role '{new_role}'. Allowed: user, admin.")

    if "is_verified" in payload:
        user.is_verified = bool(payload["is_verified"])

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": f"User {user_id} updated successfully",
        "data": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_verified": user.is_verified
        }
    }

# ─── 5. Update Item Status ────────────────────────────────────────────────────
@router.patch("/items/{item_id}/status")
@router.put("/items/{item_id}/status")
def update_item_status(
    item_id: int,
    payload: Dict[str, Any],
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update an item's status (active, resolved).
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    new_status = payload.get("status")
    if new_status:
        try:
            item.status = ItemStatus(new_status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{new_status}'. Allowed: active, resolved.")

    db.commit()
    db.refresh(item)

    return {
        "success": True,
        "message": f"Item {item_id} status updated successfully",
        "data": {
            "id": item.id,
            "title": item.title,
            "status": item.status.value if hasattr(item.status, "value") else str(item.status)
        }
    }
