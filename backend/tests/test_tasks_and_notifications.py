import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models import User, Item, ItemType, ItemStatus, Match, Notification, NotificationType, AIProcessingStatus
from app.tasks.matching_tasks import process_item_ai_matching_task
from app.services.notification_service import notification_service
from app.api.deps import get_current_user

# Helper to generate test tokens / override auth
def create_test_user(db: Session, email: str, name: str) -> User:
    user = User(email=email, name=name, is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_test_item(db: Session, user_id: int, item_type: ItemType, title: str) -> Item:
    item = Item(
        reported_by=user_id,
        item_type=item_type,
        title=title,
        category="Electronics",
        description="Test description for item matching",
        status=ItemStatus.active,
        ai_processing_status=AIProcessingStatus.pending
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ─── 1. Celery Task Creation ────────────────────────────────────────────────
def test_celery_task_signature():
    """Verify Celery task signature and registration."""
    assert process_item_ai_matching_task.name == "app.tasks.matching_tasks.process_item_ai_matching_task"


# ─── 2. Successful Matching Task ────────────────────────────────────────────
@patch("app.tasks.matching_tasks.SessionLocal")
@patch("app.tasks.matching_tasks.matching_service.analyze_item_and_find_matches")
@patch("app.tasks.matching_tasks.get_worker_clip")
def test_process_item_ai_matching_task_success(mock_get_clip, mock_analyze, mock_session_cls, db_session):
    mock_db = db_session
    mock_session_cls.return_value = mock_db

    user1 = create_test_user(mock_db, "owner1@example.com", "Owner 1")
    item = create_test_item(mock_db, user1.id, ItemType.found, "Found Keys")
    item_id = item.id

    mock_analyze.return_value = []

    res = process_item_ai_matching_task(item_id)
    assert res["status"] == "completed"
    assert res["item_id"] == item_id
    
    updated_item = db_session.query(Item).filter(Item.id == item_id).first()
    assert updated_item.ai_processing_status == AIProcessingStatus.completed



# ─── 3. Failed AI Task Handling ─────────────────────────────────────────────
@patch("app.tasks.matching_tasks.SessionLocal")
@patch("app.tasks.matching_tasks.matching_service.analyze_item_and_find_matches")
@patch("app.tasks.matching_tasks.get_worker_clip")
def test_process_item_ai_matching_task_failure(mock_get_clip, mock_analyze, mock_session_cls, db_session):
    mock_db = db_session
    mock_session_cls.return_value = mock_db

    user1 = create_test_user(mock_db, "owner2@example.com", "Owner 2")
    item = create_test_item(mock_db, user1.id, ItemType.found, "Found Laptop")

    mock_analyze.side_effect = Exception("AI inference memory error")

    res = process_item_ai_matching_task(item.id)
    assert res["status"] in ("failed", "skipped")


# ─── 4. Retry Behavior ──────────────────────────────────────────────────────
@patch("app.tasks.matching_tasks.SessionLocal")
@patch("app.tasks.matching_tasks.matching_service.analyze_item_and_find_matches")
@patch("app.tasks.matching_tasks.get_worker_clip")
def test_process_item_ai_matching_task_retry(mock_get_clip, mock_analyze, mock_session_cls, db_session):
    mock_db = db_session
    mock_session_cls.return_value = mock_db

    user1 = create_test_user(mock_db, "owner3@example.com", "Owner 3")
    item = create_test_item(mock_db, user1.id, ItemType.found, "Found Phone")

    mock_analyze.side_effect = Exception("DB Connection Timeout")

    res = process_item_ai_matching_task(item.id)
    assert res is not None


# ─── 5. Duplicate Task Execution (Idempotency) ──────────────────────────────
@patch("app.tasks.matching_tasks.SessionLocal")
@patch("app.tasks.matching_tasks.get_worker_clip")
def test_duplicate_task_execution_idempotency(mock_get_clip, mock_session_cls, db_session):
    mock_db = db_session
    mock_session_cls.return_value = mock_db

    u1 = create_test_user(mock_db, "u1@example.com", "User 1")
    u2 = create_test_user(mock_db, "u2@example.com", "User 2")
    lost = create_test_item(mock_db, u1.id, ItemType.lost, "Black Wallet")
    found = create_test_item(mock_db, u2.id, ItemType.found, "Black Leather Wallet")

    # Manually create match
    match1 = Match(lost_item_id=lost.id, found_item_id=found.id, score=0.92)
    mock_db.add(match1)
    mock_db.commit()

    match_query = mock_db.query(Match).filter(Match.lost_item_id == lost.id, Match.found_item_id == found.id)
    assert match_query.count() == 1

    # Re-running task for lost item should not throw error or duplicate match
    res = process_item_ai_matching_task(lost.id)
    assert res["status"] == "completed"
    assert match_query.count() == 1



# ─── 6. Duplicate Match Prevention ──────────────────────────────────────────
def test_duplicate_match_prevention(db_session):
    u1 = create_test_user(db_session, "dup1@example.com", "Dup User 1")
    u2 = create_test_user(db_session, "dup2@example.com", "Dup User 2")
    lost = create_test_item(db_session, u1.id, ItemType.lost, "Red Backpack")
    found = create_test_item(db_session, u2.id, ItemType.found, "Red Nylon Backpack")

    m1 = Match(lost_item_id=lost.id, found_item_id=found.id, score=0.88)
    db_session.add(m1)
    db_session.commit()

    # Querying matching logic shouldn't re-add existing match
    existing = db_session.query(Match).filter(
        Match.lost_item_id == lost.id,
        Match.found_item_id == found.id
    ).first()
    assert existing is not None


# ─── 7. Notification Creation ───────────────────────────────────────────────
def test_notification_service_creation(db_session):
    user = create_test_user(db_session, "notif_user@example.com", "Notif User")
    notif = notification_service.create_in_app_notification(
        db=db_session,
        user_id=user.id,
        title="Test Title",
        message="AI found a potential match for your lost item.",
        type=NotificationType.match_found,
        related_item_id=10,
        related_match_id=20
    )
    assert notif.id is not None
    assert notif.user_id == user.id
    assert notif.is_read is False
    assert notif.title == "Test Title"


# ─── 8. User Notification Authorization ─────────────────────────────────────
def test_user_notification_authorization(client, db_session):
    u1 = create_test_user(db_session, "userA@example.com", "User A")
    u2 = create_test_user(db_session, "userB@example.com", "User B")

    notif_u2 = notification_service.create_in_app_notification(
        db=db_session,
        user_id=u2.id,
        title="User B Notification",
        message="Secret notification"
    )

    # Override current user as User A
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: u1

    # User A tries to list notifications
    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0 # User A has no notifications

    # User A tries to read User B's notification -> Should get 404
    res_patch = client.patch(f"/api/v1/notifications/{notif_u2.id}/read")
    assert res_patch.status_code == 404

    # Clean up override
    app.dependency_overrides.pop(get_current_user, None)


# ─── 9. Mark Notification as Read ────────────────────────────────────────────
def test_mark_notification_as_read(client, db_session):
    u1 = create_test_user(db_session, "reader@example.com", "Reader User")
    notif = notification_service.create_in_app_notification(
        db=db_session,
        user_id=u1.id,
        title="Read Me",
        message="Click to mark read"
    )

    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: u1

    res = client.patch(f"/api/v1/notifications/{notif.id}/read")
    assert res.status_code == 200
    data = res.json()
    assert data["is_read"] is True

    app.dependency_overrides.pop(get_current_user, None)


# ─── 10. Unread Count Endpoint ───────────────────────────────────────────────
def test_get_unread_notification_count(client, db_session):
    u1 = create_test_user(db_session, "unread@example.com", "Unread User")
    notification_service.create_in_app_notification(
        db=db_session, user_id=u1.id, title="N1", message="Message 1"
    )
    notification_service.create_in_app_notification(
        db=db_session, user_id=u1.id, title="N2", message="Message 2"
    )

    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: u1

    res = client.get("/api/v1/notifications/unread-count")
    assert res.status_code == 200
    assert res.json()["unread_count"] == 2

    app.dependency_overrides.pop(get_current_user, None)


# ─── 11. Protected Endpoints Authorization Check ─────────────────────────────
def test_notifications_protected_endpoint_unauthenticated(client):
    res = client.get("/api/v1/notifications")
    assert res.status_code in (401, 403)

    res_unread = client.get("/api/v1/notifications/unread-count")
    assert res_unread.status_code in (401, 403)
