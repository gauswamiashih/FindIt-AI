import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

from app.services.storage_service import storage_service
from app.core.config import settings

from starlette.datastructures import Headers

def test_health_check_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "findit-api"


def test_global_exception_handler_masks_stack_traces():
    # Test that unhandled exception returns clean 500 without stack trace
    from app.main import app
    client_no_raise = TestClient(app, raise_server_exceptions=False)
    res = client_no_raise.get("/api/v1/test-500-trigger")
    assert res.status_code == 500
    data = res.json()
    assert data["detail"] == "An unexpected internal server error occurred."
    assert "Traceback" not in str(data)



@pytest.mark.asyncio
async def test_storage_service_invalid_file_format():
    fake_file = UploadFile(
        filename="virus.exe",
        file=io.BytesIO(b"not an image"),
        headers=Headers({"content-type": "application/x-msdownload"})
    )

    with pytest.raises(Exception) as exc_info:
        await storage_service.upload_image(fake_file)
    assert "Invalid file format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_storage_service_corrupted_image_content():
    fake_file = UploadFile(
        filename="corrupt.jpg",
        file=io.BytesIO(b"corrupted binary data"),
        headers=Headers({"content-type": "image/jpeg"})
    )

    with pytest.raises(Exception) as exc_info:
        await storage_service.upload_image(fake_file)
    assert "not a valid image or is corrupted" in str(exc_info.value)


def test_rate_limiting_trigger(client):
    # Trigger rate limit on sensitive POST endpoint (MAX_REQUESTS_PER_WINDOW is 60)
    res = None
    for _ in range(61):
        res = client.post("/api/v1/items")
    
    assert res.status_code == 429
    assert "Too many requests" in res.json()["detail"]






def test_env_example_safety():
    # Verify .env.example contains placeholders rather than real secret keys
    import os
    env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    if os.path.exists(env_example_path):
        with open(env_example_path, "r") as f:
            content = f.read()
            assert "XkMyp0MQlEVleRNe" not in content  # Real DB password should not be in .env.example
            assert "your-supabase-jwt-secret" in content or "your-project-id" in content

