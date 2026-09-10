import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import User, Item, ItemType, ItemStatus, AIProcessingStatus
from app.api.routes.items import python_haversine

def create_user(db: Session, email: str, name: str) -> User:
    user = User(email=email, name=name, is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_item(
    db: Session,
    user_id: int,
    item_type: ItemType,
    title: str,
    category: str = "electronics",
    color: str = "black",
    brand: str = "Apple",
    description: str = "Test item description",
    status: ItemStatus = ItemStatus.active,
    lat: float = 23.0225,
    lng: float = 72.5714
) -> Item:
    item = Item(
        reported_by=user_id,
        item_type=item_type,
        title=title,
        category=category,
        color=color,
        brand=brand,
        description=description,
        status=status,
        ai_processing_status=AIProcessingStatus.completed,
        location_lat=lat,
        location_lng=lng,
        location_city="Ahmedabad",
        location_country="India"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ─── 1. Text Search ───────────────────────────────────────────────────────────
def test_search_by_text_query(client, db_session):
    u = create_user(db_session, "text_search@example.com", "Text User")
    i1 = create_item(db_session, u.id, ItemType.lost, "Leather Wallet", category="wallet", description="Lost brown leather wallet")
    i2 = create_item(db_session, u.id, ItemType.found, "Stainless Steel Watch", category="accessories")

    res = client.get("/api/v1/items/search?q=leather")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == i1.id


# ─── 2. Type Filtering ────────────────────────────────────────────────────────
def test_search_by_type_filter(client, db_session):
    u = create_user(db_session, "type_search@example.com", "Type User")
    create_item(db_session, u.id, ItemType.lost, "Lost iPhone 14")
    create_item(db_session, u.id, ItemType.found, "Found iPhone 14")

    res_lost = client.get("/api/v1/items/search?type=lost")
    assert res_lost.status_code == 200
    data_lost = res_lost.json()
    assert all(item["item_type"] == "lost" for item in data_lost["items"])

    res_found = client.get("/api/v1/items/search?type=found")
    assert res_found.status_code == 200
    data_found = res_found.json()
    assert all(item["item_type"] == "found" for item in data_found["items"])


# ─── 3. Category Filtering ───────────────────────────────────────────────────
def test_search_by_category_filter(client, db_session):
    u = create_user(db_session, "cat_search@example.com", "Cat User")
    i1 = create_item(db_session, u.id, ItemType.lost, "House Keys", category="keys")
    i2 = create_item(db_session, u.id, ItemType.lost, "MacBook Pro", category="electronics")

    res = client.get("/api/v1/items/search?category=keys")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["category"] == "keys"


# ─── 4. Status Filtering ─────────────────────────────────────────────────────
def test_search_by_status_filter(client, db_session):
    u = create_user(db_session, "status_search@example.com", "Status User")
    i1 = create_item(db_session, u.id, ItemType.lost, "Active Ring", status=ItemStatus.active)
    i2 = create_item(db_session, u.id, ItemType.lost, "Resolved Ring", status=ItemStatus.resolved)

    res = client.get("/api/v1/items/search?status=resolved")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "resolved"


# ─── 5. Pagination ────────────────────────────────────────────────────────────
def test_search_pagination(client, db_session):
    u = create_user(db_session, "page_search@example.com", "Page User")
    for k in range(5):
        create_item(db_session, u.id, ItemType.lost, f"Item Page Test {k}")

    res_p1 = client.get("/api/v1/items/search?page=1&limit=2")
    assert res_p1.status_code == 200
    d1 = res_p1.json()
    assert d1["page"] == 1
    assert d1["limit"] == 2
    assert d1["hasNext"] is True
    assert len(d1["items"]) == 2


# ─── 6. Sorting (Recent, Oldest, Distance) ───────────────────────────────────
def test_search_sorting(client, db_session):
    u = create_user(db_session, "sort_search@example.com", "Sort User")
    i1 = create_item(db_session, u.id, ItemType.lost, "Item 1", lat=23.0, lng=72.0)
    i2 = create_item(db_session, u.id, ItemType.lost, "Item 2", lat=23.1, lng=72.1)

    res_oldest = client.get("/api/v1/items/search?sort=oldest")
    assert res_oldest.status_code == 200
    d_oldest = res_oldest.json()
    assert d_oldest["items"][0]["id"] == i1.id

    res_dist = client.get("/api/v1/items/search?lat=23.0&lng=72.0&sort=distance")
    assert res_dist.status_code == 200
    d_dist = res_dist.json()
    assert d_dist["items"][0]["distance_km"] == 0.0


# ─── 7. Invalid Coordinates Validation ───────────────────────────────────────
def test_invalid_coordinates(client):
    res_lat = client.get("/api/v1/items/search?lat=95.0&lng=72.0")
    assert res_lat.status_code == 400

    res_lng = client.get("/api/v1/items/search?lat=23.0&lng=200.0")
    assert res_lng.status_code == 400


# ─── 8. Invalid Radius Validation ────────────────────────────────────────────
def test_invalid_radius(client):
    res = client.get("/api/v1/items/search?lat=23.0&lng=72.0&radius_km=-5")
    assert res.status_code == 400


# ─── 9. Location-based Search ─────────────────────────────────────────────────
def test_location_radius_search(client, db_session):
    u = create_user(db_session, "loc_search@example.com", "Loc User")
    near = create_item(db_session, u.id, ItemType.found, "Near Item", lat=23.0225, lng=72.5714)
    far = create_item(db_session, u.id, ItemType.found, "Far Item", lat=28.6139, lng=77.2090) # Delhi (~750km away)

    res = client.get("/api/v1/items/search?lat=23.0225&lng=72.5714&radius_km=20")
    assert res.status_code == 200
    data = res.json()
    ids = [item["id"] for item in data["items"]]
    assert near.id in ids
    assert far.id not in ids


# ─── 10. Distance Calculation ────────────────────────────────────────────────
def test_haversine_distance_calculation():
    # Ahmedabad to Vadodara (~100-110 km)
    dist = python_haversine(23.0225, 72.5714, 22.3072, 73.1812)
    assert 90.0 < dist < 120.0


# ─── 11. Combined Filters ─────────────────────────────────────────────────────
def test_combined_search_filters(client, db_session):
    u = create_user(db_session, "combo@example.com", "Combo User")
    target = create_item(db_session, u.id, ItemType.lost, "Black Dell Laptop", category="electronics", color="black", lat=23.0225, lng=72.5714)
    other = create_item(db_session, u.id, ItemType.found, "Red Dell Laptop", category="electronics", color="red", lat=23.0225, lng=72.5714)

    res = client.get("/api/v1/items/search?q=dell&type=lost&category=electronics&color=black&lat=23.0225&lng=72.5714&radius_km=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == target.id


# ─── 12. Authorization & Privacy Checks ──────────────────────────────────────
def test_search_response_privacy(client, db_session):
    u = create_user(db_session, "private_user@example.com", "Private User")
    u.password_hash = "super_secret_hash"
    db_session.commit()

    create_item(db_session, u.id, ItemType.lost, "Public Search Item")

    res = client.get("/api/v1/items/search?q=Public")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0

    item_out = data["items"][0]
    # Verify no sensitive user fields (e.g. password_hash, tokens) are exposed
    assert "password_hash" not in item_out
    if item_out.get("reporter"):
        assert "password_hash" not in item_out["reporter"]
