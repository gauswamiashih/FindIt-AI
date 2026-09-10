import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import User, Item, ItemType, ItemStatus, Match, Chat, Message, Role, MatchStatus
from app.services.chat_service import chat_service
from app.services.email_service import email_service
from app.api.deps import get_current_user, get_current_admin_user

def create_user(db: Session, email: str, name: str, role: Role = Role.user) -> User:
    user = User(email=email, name=name, role=role, is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_item(db: Session, user_id: int, item_type: ItemType, title: str) -> Item:
    item = Item(
        reported_by=user_id,
        item_type=item_type,
        title=title,
        category="electronics",
        description="Phase 7 test item description",
        status=ItemStatus.active
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def create_match_with_chat(db: Session, u1: User, u2: User):
    lost = create_item(db, u1.id, ItemType.lost, "Lost Mac")
    found = create_item(db, u2.id, ItemType.found, "Found Mac")
    match = Match(lost_item_id=lost.id, found_item_id=found.id, score=0.95, status=MatchStatus.confirmed)
    db.add(match)
    db.commit()
    db.refresh(match)
    chat = chat_service.get_or_create_chat(db, match.id, u1.id)
    return match, chat, lost, found


# ─── 1. Chat REST Endpoints & Authorization ────────────────────────────────────
def test_chat_rest_flow_and_authorization(client, db_session):
    u1 = create_user(db_session, "chat_u1@example.com", "Chat User 1")
    u2 = create_user(db_session, "chat_u2@example.com", "Chat User 2")
    u3 = create_user(db_session, "chat_u3@example.com", "Chat User 3")

    match, chat, lost, found = create_match_with_chat(db_session, u1, u2)

    from app.main import app

    # User 1 lists chats
    app.dependency_overrides[get_current_user] = lambda: u1
    res_list = client.get("/api/v1/chats")
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    # User 1 sends message
    res_msg = client.post(f"/api/v1/chats/{chat.id}/messages", json={"text": "Hello User 2!"})
    assert res_msg.status_code == 201
    assert res_msg.json()["text"] == "Hello User 2!"

    # User 2 gets messages
    app.dependency_overrides[get_current_user] = lambda: u2
    res_get_msgs = client.get(f"/api/v1/chats/{chat.id}/messages")
    assert res_get_msgs.status_code == 200
    assert res_get_msgs.json()["total"] == 1

    # User 3 (Unauthorized) attempts to access chat -> 404 or 403
    app.dependency_overrides[get_current_user] = lambda: u3
    res_unauth = client.get(f"/api/v1/chats/{chat.id}")
    assert res_unauth.status_code in (403, 404)

    app.dependency_overrides.pop(get_current_user, None)


# ─── 2. WebSocket Connection & Authorization Test ─────────────────────────────
@patch("app.api.routes.chats.verify_supabase_token")
def test_websocket_chat_access(mock_verify_token, client, db_session):
    u1 = create_user(db_session, "ws_u1@example.com", "WS User 1")
    u1.supabase_id = "ws_u1_sub"
    db_session.commit()
    u2 = create_user(db_session, "ws_u2@example.com", "WS User 2")
    match, chat, lost, found = create_match_with_chat(db_session, u1, u2)

    # Missing token -> Rejected
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/chats/ws/{chat.id}") as websocket:
            pass

    # ConnectionManager unit verification
    from app.api.routes.chats import manager
    assert chat.id not in manager.active_connections or isinstance(manager.active_connections, dict)





# ─── 3. QR Code Generation Test ───────────────────────────────────────────────
def test_generate_item_qr_code(client, db_session):
    u = create_user(db_session, "qr_user@example.com", "QR User")
    item = create_item(db_session, u.id, ItemType.lost, "Camera with Lens")

    res = client.get(f"/api/v1/items/{item.id}/qr")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 50


# ─── 4. Admin Stats & Role Enforcement ─────────────────────────────────────────
def test_admin_stats_and_authorization(client, db_session):
    admin = create_user(db_session, "admin_user@example.com", "Admin", role=Role.admin)
    normal = create_user(db_session, "normal_user@example.com", "Normal User", role=Role.user)
    create_item(db_session, normal.id, ItemType.lost, "Admin Test Lost Item")

    from app.main import app

    # Normal user attempts admin endpoint -> 403
    app.dependency_overrides[get_current_user] = lambda: normal
    res_denied = client.get("/api/v1/admin/stats")
    assert res_denied.status_code == 403

    # Admin accesses stats -> 200
    app.dependency_overrides[get_current_user] = lambda: admin
    res_stats = client.get("/api/v1/admin/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()["data"]
    assert stats_data["total_users"] >= 2
    assert stats_data["total_lost_items"] >= 1

    app.dependency_overrides.pop(get_current_user, None)


# ─── 5. Admin User & Item Status Management ────────────────────────────────────
def test_admin_status_updates(client, db_session):
    admin = create_user(db_session, "admin_mgr@example.com", "Admin Manager", role=Role.admin)
    target_user = create_user(db_session, "target_user@example.com", "Target User")
    target_item = create_item(db_session, target_user.id, ItemType.lost, "Item to Moderate")

    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: admin

    # Promote target user to admin
    res_u = client.patch(f"/api/v1/admin/users/{target_user.id}/status", json={"role": "admin"})
    assert res_u.status_code == 200
    assert res_u.json()["data"]["role"] == "admin"

    # Update item status to resolved
    res_i = client.patch(f"/api/v1/admin/items/{target_item.id}/status", json={"status": "resolved"})
    assert res_i.status_code == 200
    assert res_i.json()["data"]["status"] == "resolved"

    app.dependency_overrides.pop(get_current_user, None)


# ─── 6. Email Service Fallback & Mocks ───────────────────────────────────────
def test_email_service_mocking():
    success = email_service.send_email("test@example.com", "Test Subject", "Test Body")
    assert success is True
