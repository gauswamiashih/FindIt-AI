from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import Optional, List
import math

from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.db.database import get_db
from app.models import User, Item, Role, ItemType, ItemStatus
from app.schemas.item import (
    ItemCreate, ItemUpdate, ItemResponse, PaginatedItemResponse,
    ItemTypeEnum, ItemStatusEnum
)
from app.services.storage_service import storage_service

router = APIRouter()

def apply_distance_filter(query, lat: float, lng: float, max_distance_km: float):
    lat_delta = max_distance_km / 111.0
    lng_delta = max_distance_km / (111.0 * math.cos(math.radians(lat)))
    
    return query.filter(
        Item.location_lat.between(lat - lat_delta, lat + lat_delta),
        Item.location_lng.between(lng - lng_delta, lng + lng_delta)
    )

# ─── 1. Create Item (JSON) ───────────────────────────────────────────────────
@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_in: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new Lost or Found item via JSON payload.
    Requires authentication.
    """
    item_data = item_in.model_dump()
    
    lat = item_data.get("location_lat")
    lng = item_data.get("location_lng")
    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if lng is not None and not (-180.0 <= lng <= 180.0):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    db_item = Item(
        reported_by=current_user.id,
        item_type=ItemType(item_data["item_type"]),
        title=item_data["title"],
        category=item_data["category"],
        brand=item_data.get("brand"),
        color=item_data.get("color"),
        description=item_data["description"],
        item_date=item_data.get("item_date"),
        item_time=item_data.get("item_time"),
        location_lat=lat,
        location_lng=lng,
        location_address=item_data.get("location_address"),
        location_city=item_data.get("location_city"),
        location_state=item_data.get("location_state"),
        location_country=item_data.get("location_country"),
        images=item_data.get("images", []),
        reward=item_data.get("reward", {}),
        status=ItemStatus(item_data.get("status", ItemStatus.active)),
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Increment user stats
    if current_user.stats is None:
        current_user.stats = {}
    stats = dict(current_user.stats)
    key = "lostItemsReported" if db_item.item_type == ItemType.lost else "foundItemsReported"
    stats[key] = stats.get(key, 0) + 1
    current_user.stats = stats
    db.commit()

    # Queue background AI matching task
    try:
        from app.tasks.matching_tasks import process_item_ai_matching_task
        process_item_ai_matching_task.delay(db_item.id)
    except Exception as e:
        pass

    return db_item

# ─── 1b. Create Item with File Uploads (Multipart Form) ──────────────────────
@router.post("/form", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item_with_files(
    title: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    item_type: str = Form(...),
    brand: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    item_date: Optional[str] = Form(None),
    item_time: Optional[str] = Form(None),
    location_lat: Optional[float] = Form(None),
    location_lng: Optional[float] = Form(None),
    location_address: Optional[str] = Form(None),
    location_city: Optional[str] = Form(None),
    location_state: Optional[str] = Form(None),
    location_country: Optional[str] = Form(None),
    reward_offered: Optional[bool] = Form(None),
    reward_amount: Optional[float] = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new Lost or Found item with multipart file uploads.
    Uploaded images are automatically processed and stored in Cloudinary.
    """
    uploaded_images = []
    if files and len(files) > 0 and files[0].filename:
        uploaded_images = await storage_service.upload_multiple_images(files)

    try:
        type_enum = ItemType(item_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid item_type '{item_type}'. Allowed values: lost, found."
        )

    parsed_date = None
    if item_date:
        try:
            from datetime import datetime
            parsed_date = datetime.fromisoformat(item_date.replace("Z", "+00:00"))
        except Exception:
            pass

    reward_dict = {}
    if reward_offered is not None:
        reward_dict = {"offered": reward_offered, "amount": reward_amount or 0}

    if location_lat is not None and not (-90.0 <= location_lat <= 90.0):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if location_lng is not None and not (-180.0 <= location_lng <= 180.0):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    db_item = Item(
        reported_by=current_user.id,
        item_type=type_enum,
        title=title,
        category=category,
        brand=brand,
        color=color,
        description=description,
        item_date=parsed_date,
        item_time=item_time,
        location_lat=location_lat,
        location_lng=location_lng,
        location_address=location_address,
        location_city=location_city,
        location_state=location_state,
        location_country=location_country,
        images=uploaded_images,
        reward=reward_dict,
        status=ItemStatus.active
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Queue background AI matching task
    try:
        from app.tasks.matching_tasks import process_item_ai_matching_task
        process_item_ai_matching_task.delay(db_item.id)
    except Exception as e:
        pass

    return db_item

def python_haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate Great Circle Haversine distance in kilometers between two lat/lng coordinates."""
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

def helper_format_item(item: Item, user_lat: Optional[float] = None, user_lng: Optional[float] = None) -> dict:
    dist = None
    if user_lat is not None and user_lng is not None and item.location_lat is not None and item.location_lng is not None:
        dist = python_haversine(user_lat, user_lng, item.location_lat, item.location_lng)

    return {
        "id": item.id,
        "_id": item.id,
        "reported_by": item.reported_by,
        "user_id": item.reported_by,
        "item_type": item.item_type,
        "type": item.type,
        "title": item.title,
        "category": item.category,
        "brand": item.brand,
        "color": item.color,
        "description": item.description,
        "item_date": item.item_date,
        "item_time": item.item_time,
        "location_lat": item.location_lat,
        "location_lng": item.location_lng,
        "location_address": item.location_address,
        "location_city": item.location_city,
        "location_state": item.location_state,
        "location_country": item.location_country,
        "location": item.location,
        "images": item.images or [],
        "image_url": item.image_url,
        "reward": item.reward or {},
        "status": item.status,
        "ai_processing_status": item.ai_processing_status.value if hasattr(item.ai_processing_status, "value") else str(item.ai_processing_status),
        "distance_km": dist,
        "views": item.views or 0,
        "qr_code": item.qr_code,
        "created_at": item.created_at,
        "createdAt": item.created_at,
        "updated_at": item.updated_at,
        "updatedAt": item.updated_at,
        "reporter": item.reporter,
    }

def execute_items_search(
    db: Session,
    q: Optional[str] = None,
    type_val: Optional[str] = None,
    category_val: Optional[str] = None,
    color_val: Optional[str] = None,
    brand_val: Optional[str] = None,
    status_val: Optional[str] = None,
    my_val: bool = False,
    current_user: Optional[User] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    sort_by: Optional[str] = "recent",
    page: int = 1,
    limit: int = 20
) -> PaginatedItemResponse:
    # 1. Coordinate & Radius Validation
    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90 degrees")
    if lng is not None and not (-180.0 <= lng <= 180.0):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180 degrees")
    if (lat is not None and lng is None) or (lng is not None and lat is None):
        raise HTTPException(status_code=400, detail="Both latitude and longitude must be provided for spatial search")
    if radius_km is not None and (radius_km <= 0 or radius_km > 1000):
        raise HTTPException(status_code=400, detail="radius_km must be greater than 0 and at most 1000 km")

    query = db.query(Item).options(joinedload(Item.reporter))

    # 2. Type & Ownership
    if type_val and type_val.lower() != "all":
        try:
            query = query.filter(Item.item_type == ItemType(type_val.lower()))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid type '{type_val}'. Allowed values: lost, found.")

    if my_val:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required to fetch personal items")
        query = query.filter(Item.reported_by == current_user.id)

    # 3. Category, Color, Brand, Status
    if category_val:
        query = query.filter(Item.category.ilike(f"%{category_val}%"))
    if color_val:
        query = query.filter(Item.color.ilike(f"%{color_val}%"))
    if brand_val:
        query = query.filter(Item.brand.ilike(f"%{brand_val}%"))
    if status_val:
        try:
            query = query.filter(Item.status == ItemStatus(status_val.lower()))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status_val}'. Allowed: active, resolved.")

    # 4. Text Search
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Item.title.ilike(pattern),
                Item.description.ilike(pattern),
                Item.category.ilike(pattern),
                Item.color.pattern if hasattr(Item.color, "pattern") else Item.color.ilike(pattern),
                Item.brand.ilike(pattern)
            )
        )

    # 5. Geolocation Bounding Filter
    is_spatial = lat is not None and lng is not None
    r_km = radius_km or 50.0

    if is_spatial:
        lat_delta = r_km / 111.0
        lng_delta = r_km / (111.0 * max(0.01, math.cos(math.radians(lat))))
        query = query.filter(
            Item.location_lat.between(lat - lat_delta, lat + lat_delta),
            Item.location_lng.between(lng - lng_delta, lng + lng_delta)
        )

    # 6. Sorting Whitelist
    sort_clean = (sort_by or "recent").lower()
    if sort_clean not in ("recent", "oldest", "distance"):
        raise HTTPException(status_code=400, detail=f"Invalid sort option '{sort_by}'. Allowed: recent, oldest, distance")

    if sort_clean == "distance" and not is_spatial:
        raise HTTPException(status_code=400, detail="lat and lng coordinates are required to sort by distance")

    # Execute DB query
    all_matched_items = query.all()

    # Calculate exact distance and filter strictly within radius
    processed_items = []
    for item in all_matched_items:
        formatted = helper_format_item(item, user_lat=lat, user_lng=lng)
        if is_spatial:
            if formatted["distance_km"] is not None and formatted["distance_km"] <= r_km:
                processed_items.append(formatted)
        else:
            processed_items.append(formatted)

    # Sort in Python for exact order
    if sort_clean == "oldest":
        processed_items.sort(key=lambda x: x["created_at"] or "")
    elif sort_clean == "distance" and is_spatial:
        processed_items.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else float("inf"))
    else:  # recent
        processed_items.sort(key=lambda x: x["created_at"] or "", reverse=True)

    # Paginate
    total = len(processed_items)
    limit_val = min(max(1, limit), 100)
    pages = math.ceil(total / limit_val) if total > 0 else 1
    page_val = min(max(1, page), pages) if total > 0 else 1
    offset = (page_val - 1) * limit_val

    paginated_slice = processed_items[offset:offset + limit_val]

    return PaginatedItemResponse(
        items=paginated_slice,
        page=page_val,
        limit=limit_val,
        total=total,
        pages=pages,
        hasNext=page_val < pages,
        hasPrev=page_val > 1
    )

# ─── 2a. Search Items Endpoint ────────────────────────────────────────────────
@router.get("/search", response_model=PaginatedItemResponse)
def search_items(
    q: Optional[str] = Query(None, description="Full-text query across title, description, category, color, brand"),
    type: Optional[str] = Query(None, description="Filter by type: lost or found"),
    category: Optional[str] = Query(None, description="Filter by category"),
    color: Optional[str] = Query(None, description="Filter by color"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: active, resolved"),
    lat: Optional[float] = Query(None, alias="lat", description="Latitude (-90 to 90)"),
    latitude: Optional[float] = Query(None, alias="latitude", description="Latitude alias (-90 to 90)"),
    lng: Optional[float] = Query(None, alias="lng", description="Longitude (-180 to 180)"),
    longitude: Optional[float] = Query(None, alias="longitude", description="Longitude alias (-180 to 180)"),
    radius_km: Optional[float] = Query(None, alias="radius_km", description="Radius distance in km"),
    max_distance: Optional[float] = Query(None, alias="max_distance", description="Max distance alias in km"),
    sort: Optional[str] = Query("recent", description="Sorting: recent, oldest, distance"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Full-text search and geolocation distance query endpoint for Lost & Found items.
    """
    final_lat = lat if lat is not None else latitude
    final_lng = lng if lng is not None else longitude
    final_radius = radius_km if radius_km is not None else max_distance

    return execute_items_search(
        db=db,
        q=q,
        type_val=type,
        category_val=category,
        color_val=color,
        brand_val=brand,
        status_val=status_filter,
        my_val=False,
        current_user=current_user,
        lat=final_lat,
        lng=final_lng,
        radius_km=final_radius,
        sort_by=sort,
        page=page,
        limit=limit
    )

# ─── 2b. Get All Items ────────────────────────────────────────────────────────
@router.get("", response_model=PaginatedItemResponse)
@router.get("/", response_model=PaginatedItemResponse)
def get_items(
    type: Optional[str] = Query(None, description="Filter by item type: lost or found"),
    category: Optional[str] = Query(None, description="Filter by category"),
    color: Optional[str] = Query(None, description="Filter by color"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: active, resolved"),
    search: Optional[str] = Query(None, alias="q", description="Search query in title, description, category, color"),
    my: Optional[bool] = Query(False, description="Fetch items reported by current user"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    lng: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_distance: Optional[float] = Query(50.0, description="Max distance in km for geolocation search"),
    sort: Optional[str] = Query("recent", description="Sorting option: recent, oldest, distance"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get paginated items list with flexible filters. Public access supported.
    """
    return execute_items_search(
        db=db,
        q=search,
        type_val=type,
        category_val=category,
        color_val=color,
        brand_val=brand,
        status_val=status_filter,
        my_val=my or False,
        current_user=current_user,
        lat=lat,
        lng=lng,
        radius_km=max_distance,
        sort_by=sort,
        page=page,
        limit=limit
    )

from fastapi.responses import Response
import io
import qrcode

# ─── 2c. Item QR Code Generation ───────────────────────────────────────────────
@router.get("/{item_id}/qr")
def generate_item_qr_code(item_id: int, db: Session = Depends(get_db)):
    """
    Generate a public QR code image (PNG) for an item.
    Encodes safe public item URL without private tokens or credentials.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item_type = item.type if hasattr(item, "type") else "lost"
    public_url = f"{settings.FRONTEND_URL}/items/{item_type}/{item.id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(public_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")

# ─── 3. Get Single Item ────────────────────────────────────────────────────────
@router.get("/{item_id}", response_model=ItemResponse)
def get_item_by_id(item_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information for a single item. Increments view count.
    """
    item = db.query(Item).options(joinedload(Item.reporter)).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.views = (item.views or 0) + 1
    db.commit()
    db.refresh(item)

    return item

# ─── 4. Update Item ────────────────────────────────────────────────────────────
@router.patch("/{item_id}", response_model=ItemResponse)
@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_in: Optional[ItemUpdate] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing item. Only the owner or an admin can update.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if item.reported_by != current_user.id and current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this item"
        )

    if item_in:
        update_data = item_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == "item_type":
                    value = ItemType(value)
                elif field == "status":
                    value = ItemStatus(value)
                setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item

# ─── 5. Delete Item ────────────────────────────────────────────────────────────
@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an item. Only the owner or an admin can delete.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if item.reported_by != current_user.id and current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this item"
        )

    db.delete(item)
    db.commit()
    return None
