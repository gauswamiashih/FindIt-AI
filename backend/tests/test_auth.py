import pytest
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.core.config import settings

TEST_JWT_SECRET = "test-secret-key-for-unit-testing-12345"
settings.JWT_SECRET = TEST_JWT_SECRET
settings.JWT_ALGORITHM = "HS256"

def create_test_token(sub="test-supabase-uid-123", email="testuser@example.com", expires_in_minutes=60, user_metadata=None):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
        "user_metadata": user_metadata or {"full_name": "Test User", "avatar_url": "https://example.com/avatar.png"}
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

def test_me_missing_token(client):
    """1. Missing Authorization header -> 401"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_me_invalid_token(client):
    """2. Invalid token -> 401"""
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_me_expired_token(client):
    """3. Expired token -> 401"""
    expired_token = create_test_token(expires_in_minutes=-10)
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]

def test_me_new_user_creation(client):
    """4 & 5. Valid authentication with a new user -> auto-creates user in DB and returns profile"""
    sub = "new-supabase-user-999"
    email = "newuser@example.com"
    token = create_test_token(sub=sub, email=email, user_metadata={"full_name": "New User Name", "avatar_url": "https://example.com/pic.png"})
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["supabase_id"] == sub
    assert data["name"] == "New User Name"
    assert data["avatar_url"] == "https://example.com/pic.png"
    assert data["role"] == "user"

def test_me_existing_user_retrieval(client):
    """6. Valid authentication with an existing user -> retrieves user from DB without duplication"""
    sub = "new-supabase-user-999"
    email = "newuser@example.com"
    token = create_test_token(sub=sub, email=email)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["supabase_id"] == sub
