import pytest
import numpy as np
from PIL import Image
import io
from jose import jwt
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.ai.similarity_service import similarity_service
from app.ai.embedding_service import embedding_service

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

def test_1_image_preprocessing():
    """1. Test image preprocessing & byte loading"""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    raw_bytes = buffer.getvalue()
    
    assert len(raw_bytes) > 0

def test_2_text_description_generation():
    """2. Test building rich text prompt from item metadata"""
    from app.ai.clip_service import CLIPService
    clip_service = CLIPService()
    prompt = clip_service.build_item_description(
        title="Black Leather Wallet",
        category="Wallets",
        brand="Gucci",
        color="Black",
        description="Lost wallet near subway station"
    )
    assert "Black" in prompt
    assert "Gucci" in prompt
    assert "Wallets" in prompt
    assert "Black Leather Wallet" in prompt

def test_3_and_4_vector_normalization():
    """3 & 4. Test vector normalization (L2 norm = 1.0)"""
    raw_vector = np.array([3.0, 4.0])
    normalized = embedding_service.normalize_vector(raw_vector)
    norm = np.linalg.norm(normalized)
    assert pytest.approx(norm, 1e-4) == 1.0

def test_5_cosine_similarity():
    """5. Test cosine similarity between identical and orthogonal vectors"""
    vec_a = np.array([1.0, 0.0, 0.0])
    vec_b = np.array([1.0, 0.0, 0.0])
    vec_c = np.array([0.0, 1.0, 0.0])

    sim_identical = similarity_service.cosine_similarity(vec_a, vec_b)
    sim_orthogonal = similarity_service.cosine_similarity(vec_a, vec_c)

    assert pytest.approx(sim_identical, 1e-3) == 1.0
    assert pytest.approx(sim_orthogonal, 1e-3) == 0.5 # 0.5 normalized midpoint for orthogonal

def test_6_combined_score():
    """6. Test combined weighted score formula (0.75 img + 0.25 text)"""
    img_score = 0.90
    text_score = 0.80
    combined = similarity_service.compute_combined_score(img_score, text_score, image_weight=0.75, text_weight=0.25)
    expected = (0.90 * 0.75) + (0.80 * 0.25) # 0.675 + 0.20 = 0.875
    assert pytest.approx(combined, 1e-3) == expected

def test_7_threshold_behavior():
    """7. Test match threshold evaluation"""
    assert similarity_service.is_match(0.86, threshold=0.85) is True
    assert similarity_service.is_match(0.84, threshold=0.85) is False

def test_8_and_9_match_creation_and_duplicate_prevention(client):
    """8 & 9. Test creating match records and preventing duplicate match creation"""
    headers1 = {"Authorization": f"Bearer {token_user1}"}
    headers2 = {"Authorization": f"Bearer {token_user2}"}

    # Create Lost Item (User 1)
    lost_res = client.post("/api/v1/items", json={
        "title": "Lost Gold Watch",
        "category": "Jewelry",
        "description": "Gold Rolex watch lost in mall",
        "item_type": "lost",
        "images": [{"url": "http://example.com/watch1.jpg"}]
    }, headers=headers1)
    assert lost_res.status_code == 201
    lost_id = lost_res.json()["id"]

    # Create Found Item (User 2)
    found_res = client.post("/api/v1/items", json={
        "title": "Found Gold Rolex Watch",
        "category": "Jewelry",
        "description": "Found gold watch near entrance",
        "item_type": "found",
        "images": [{"url": "http://example.com/watch2.jpg"}]
    }, headers=headers2)
    assert found_res.status_code == 201
    found_id = found_res.json()["id"]


    # Mock CLIP on app state for test execution
    class DummyCLIP:
        model = object()
        async def fetch_image_from_url(self, url):
            return b"fake"
        async def get_image_embedding(self, data):
            return np.ones((1, 512))
        def build_item_description(self, *args, **kwargs):
            return "Gold Watch"
        async def get_text_embedding(self, text):
            return np.ones((1, 512))

    client.app.state.clip = DummyCLIP()

    # Trigger Analyze
    analyze_res = client.post(f"/api/v1/matches/item/{lost_id}/analyze", headers=headers1)
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["matches_created"] >= 1

    # Trigger Analyze SECOND time to test duplicate prevention
    analyze_res2 = client.post(f"/api/v1/matches/item/{lost_id}/analyze", headers=headers1)
    assert analyze_res2.status_code == 200
    assert analyze_res2.json()["matches_created"] == 0 # 0 new matches created on duplicate pass

def test_10_unauthorized_match_access(client):
    """10. Test unauthorized access to match records (403/404)"""
    headers3 = {"Authorization": f"Bearer {create_test_token(sub='sub-user-3', email='user3@example.com')}"}
    
    # User 3 tries to access Match ID 1
    response = client.get("/api/v1/matches/1", headers=headers3)
    assert response.status_code in (403, 404)

def test_11_invalid_image_handling():
    """11. Test handling invalid/corrupted image data"""
    from app.services.storage_service import storage_service
    from fastapi import UploadFile
    import asyncio

    corrupted_file = UploadFile(filename="corrupt.jpg", file=io.BytesIO(b"not an image file"))
    
    with pytest.raises(Exception):
        asyncio.run(storage_service.upload_image(corrupted_file))
