import pytest
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.core.config import settings

TEST_JWT_SECRET = "test-secret-key-for-unit-testing-12345"
settings.JWT_SECRET = TEST_JWT_SECRET
settings.JWT_ALGORITHM = "HS256"

def create_test_token(sub="test-user-1", email="user1@example.com"):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "user_metadata": {"full_name": "Test User 1"}
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

token_user1 = create_test_token(sub="sub-user-1", email="user1@example.com")
token_user2 = create_test_token(sub="sub-user-2", email="user2@example.com")

def test_create_lost_item(client):
    """1. Create lost item with valid authentication"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    payload = {
        "title": "Black Leather Wallet",
        "category": "Wallets",
        "brand": "Tommy Hilfiger",
        "color": "Black",
        "description": "Lost my leather wallet containing cards and ID near the central park library.",
        "item_type": "lost",
        "location_lat": 40.7128,
        "location_lng": -74.0060,
        "location_address": "Central Park, NY"
    }
    response = client.post("/api/v1/items", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Black Leather Wallet"
    assert data["item_type"] == "lost"
    assert data["type"] == "lost"

def test_create_found_item(client):
    """2. Create found item with valid authentication"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    payload = {
        "title": "Silver Apple iPhone 14",
        "category": "Electronics",
        "brand": "Apple",
        "color": "Silver",
        "description": "Found a silver iPhone 14 on a bench near Starbucks.",
        "item_type": "found",
        "location_lat": 40.7130,
        "location_lng": -74.0055
    }
    response = client.post("/api/v1/items", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Silver Apple iPhone 14"
    assert data["item_type"] == "found"

def test_get_items_list(client):
    """3. Get items list"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    client.post("/api/v1/items", json={
        "title": "Item List Test 1", "category": "Wallets", "description": "Long enough description 1", "item_type": "lost"
    }, headers=headers)
    client.post("/api/v1/items", json={
        "title": "Item List Test 2", "category": "Electronics", "description": "Long enough description 2", "item_type": "found"
    }, headers=headers)

    response = client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 2
    assert "total" in data
    assert data["total"] >= 2

def test_get_single_item(client):
    """4. Get single item by ID and verify view count increment"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    res_create = client.post("/api/v1/items", json={
        "title": "Single Item Test", "category": "Wallets", "description": "Long enough description", "item_type": "lost"
    }, headers=headers)
    assert res_create.status_code == 201
    item_id = res_create.json()["id"]

    response = client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["views"] >= 1

def test_update_own_item(client):
    """5. Update own item"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    res_create = client.post("/api/v1/items", json={
        "title": "Initial Title", "category": "Wallets", "description": "Long enough description", "item_type": "lost"
    }, headers=headers)
    assert res_create.status_code == 201
    item_id = res_create.json()["id"]

    update_payload = {"title": "Updated Black Wallet Title"}
    response = client.patch(f"/api/v1/items/{item_id}", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Black Wallet Title"

def test_prevent_updating_another_user_item(client):
    """6. Prevent updating another user's item (403)"""
    headers1 = {"Authorization": f"Bearer {token_user1}"}
    res_create = client.post("/api/v1/items", json={
        "title": "User1 Item", "category": "Wallets", "description": "Long enough description", "item_type": "lost"
    }, headers=headers1)
    assert res_create.status_code == 201
    item_id = res_create.json()["id"]

    headers2 = {"Authorization": f"Bearer {token_user2}"}
    update_payload = {"title": "Hacked Title"}
    response = client.patch(f"/api/v1/items/{item_id}", json=update_payload, headers=headers2)
    assert response.status_code == 403
    assert "do not have permission" in response.json()["detail"]

def test_prevent_deleting_another_user_item(client):
    """8. Prevent deleting another user's item (403)"""
    headers1 = {"Authorization": f"Bearer {token_user1}"}
    res_create = client.post("/api/v1/items", json={
        "title": "User1 Item to Delete", "category": "Wallets", "description": "Long enough description", "item_type": "lost"
    }, headers=headers1)
    assert res_create.status_code == 201
    item_id = res_create.json()["id"]

    headers2 = {"Authorization": f"Bearer {token_user2}"}
    response = client.delete(f"/api/v1/items/{item_id}", headers=headers2)
    assert response.status_code == 403

def test_delete_own_item(client):
    """7. Delete own item"""
    headers1 = {"Authorization": f"Bearer {token_user1}"}
    res_create = client.post("/api/v1/items", json={
        "title": "Item To Self Delete", "category": "Wallets", "description": "Long enough description", "item_type": "lost"
    }, headers=headers1)
    assert res_create.status_code == 201
    item_id = res_create.json()["id"]

    response = client.delete(f"/api/v1/items/{item_id}", headers=headers1)
    assert response.status_code == 204
    
    # Confirm item is deleted
    get_res = client.get(f"/api/v1/items/{item_id}")
    assert get_res.status_code == 404


def test_authentication_required(client):
    """9. Authentication required for item creation (401)"""
    payload = {
        "title": "Unauthenticated Item",
        "category": "Keys",
        "description": "Keys found near building A",
        "item_type": "found"
    }
    response = client.post("/api/v1/items", json=payload)
    assert response.status_code == 401

def test_invalid_item_data(client):
    """10. Invalid item data validation (400/422)"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    payload = {
        "title": "A", # Title too short (<2 chars)
        "category": "Wallets",
        "description": "Short",
        "item_type": "invalid_type",
        "location_lat": 999.0 # Invalid latitude
    }
    response = client.post("/api/v1/items", json=payload, headers=headers)
    assert response.status_code in (400, 422)

def test_pagination(client):
    """11. Pagination test"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    # Create item to paginate
    client.post("/api/v1/items", json={
        "title": "Pagination Item 1",
        "category": "Other",
        "description": "Item description for pagination testing",
        "item_type": "lost"
    }, headers=headers)

    response = client.get("/api/v1/items?page=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 1
    assert len(data["items"]) == 1

def test_filters(client):
    """12. Filter by type and status"""
    headers = {"Authorization": f"Bearer {token_user1}"}
    client.post("/api/v1/items", json={
        "title": "Filter Active Lost Item",
        "category": "Wallets",
        "description": "Filter desc",
        "item_type": "lost"
    }, headers=headers)

    response = client.get("/api/v1/items?type=lost&status=active")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["item_type"] == "lost"
        assert item["status"] == "active"

