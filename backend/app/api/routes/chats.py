from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Set
import logging
import json

from app.api.deps import get_current_user, verify_supabase_token
from app.db.database import get_db, SessionLocal
from app.models import User, Chat, Message
from app.schemas.chat import (
    ChatResponse, MessageResponse, MessageCreate, ChatListResponse, MessageListResponse
)
from app.services.chat_service import chat_service

logger = logging.getLogger("findit.api.chats")

router = APIRouter()

# ─── WebSocket Connection Manager ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        # Maps chat_id -> dict of (websocket -> user_id)
        self.active_connections: Dict[int, Dict[WebSocket, int]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        self.active_connections[chat_id][websocket] = user_id
        logger.info(f"WebSocket connected: User {user_id} to Chat {chat_id}")

    def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].pop(websocket, None)
            if not self.active_connections[chat_id]:
                self.active_connections.pop(chat_id, None)
        logger.info(f"WebSocket disconnected from Chat {chat_id}")

    async def broadcast_to_chat(self, chat_id: int, data: dict):
        if chat_id in self.active_connections:
            for connection in list(self.active_connections[chat_id].keys()):
                try:
                    await connection.send_json(data)
                except Exception as exc:
                    logger.warning(f"Error broadcasting to WebSocket: {exc}")

manager = ConnectionManager()

def helper_format_user_min(user: User) -> dict:
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url
    }

def helper_format_message(msg: Message, sender: Optional[User] = None) -> dict:
    return {
        "id": msg.id,
        "_id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "text": msg.text,
        "message": msg.text,
        "is_read": msg.is_read,
        "created_at": msg.created_at,
        "createdAt": msg.created_at,
        "sender": helper_format_user_min(sender) if sender else None
    }

def helper_format_chat(chat: Chat, current_user_id: int, db: Session) -> dict:
    other_id = chat.user2_id if current_user_id == chat.user1_id else chat.user1_id
    other_user = db.query(User).filter(User.id == other_id).first()
    
    last_msg = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .first()
    )

    return {
        "id": chat.id,
        "_id": chat.id,
        "match_id": chat.match_id,
        "user1_id": chat.user1_id,
        "user2_id": chat.user2_id,
        "created_at": chat.created_at,
        "createdAt": chat.created_at,
        "updated_at": chat.updated_at,
        "updatedAt": chat.updated_at,
        "other_user": helper_format_user_min(other_user),
        "last_message": helper_format_message(last_msg) if last_msg else None
    }

# ─── 1. List User Chats ────────────────────────────────────────────────────────
@router.get("", response_model=ChatListResponse)
@router.get("/", response_model=ChatListResponse)
def list_user_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active chats involving the authenticated user.
    """
    chats = chat_service.get_user_chats(db, current_user.id)
    formatted = [helper_format_chat(c, current_user.id, db) for c in chats]
    return ChatListResponse(chats=formatted, total=len(formatted))

# ─── 1b. Get or Create Chat for Match ──────────────────────────────────────────
@router.post("/match/{match_id}", response_model=ChatResponse)
def get_or_create_match_chat(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get or initialize a chat for a confirmed match record.
    """
    chat = chat_service.get_or_create_chat(db, match_id=match_id, user_id=current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Match not found or access denied"
        )
    return helper_format_chat(chat, current_user.id, db)

# ─── 2. Get Single Chat Detail ────────────────────────────────────────────────
@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat_by_id(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get chat metadata by ID. Requires membership in the chat.
    """
    chat = chat_service.get_chat_by_id(db, chat_id=chat_id, user_id=current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or access denied"
        )
    return helper_format_chat(chat, current_user.id, db)

# ─── 3. Get Chat Messages ──────────────────────────────────────────────────────
@router.get("/{chat_id}/messages", response_model=MessageListResponse)
def get_chat_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated chat messages for a chat room.
    """
    skip = (page - 1) * limit
    messages, total = chat_service.get_chat_messages(
        db, chat_id=chat_id, user_id=current_user.id, skip=skip, limit=limit
    )
    formatted = [helper_format_message(m) for m in messages]
    return MessageListResponse(messages=formatted, total=total)

# ─── 4. Send Message (REST) ───────────────────────────────────────────────────
@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    chat_id: int,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a text message in a chat room.
    Saves message and broadcasts to WebSocket room subscribers.
    """
    msg = chat_service.create_message(
        db, chat_id=chat_id, sender_id=current_user.id, text=message_in.text
    )
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat not found or access denied"
        )
    
    formatted = helper_format_message(msg, sender=current_user)

    # Broadcast to WebSocket room
    await manager.broadcast_to_chat(chat_id, formatted)

    return formatted

# ─── 5. WebSocket Chat Endpoint ────────────────────────────────────────────────
@router.websocket("/ws/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: Optional[str] = Query(None)
):
    """
    Real-time WebSocket endpoint for chat participants.
    Authenticates token, verifies chat membership, saves and broadcasts messages.
    """
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    db = SessionLocal()
    try:
        payload = verify_supabase_token(token)
        supabase_id = payload.get("sub")
        user = db.query(User).filter(User.supabase_id == supabase_id).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return

        chat = chat_service.get_chat_by_id(db, chat_id=chat_id, user_id=user.id)
        if not chat:
            await websocket.close(code=4003, reason="Chat access forbidden")
            return

        await manager.connect(websocket, chat_id=chat_id, user_id=user.id)

        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                text = data.get("text") or data.get("message")
                if text:
                    msg = chat_service.create_message(
                        db, chat_id=chat_id, sender_id=user.id, text=text
                    )
                    if msg:
                        formatted = helper_format_message(msg, sender=user)
                        await manager.broadcast_to_chat(chat_id, formatted)
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id=chat_id)
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        try:
            await websocket.close(code=4000, reason=str(exc))
        except Exception:
            pass
    finally:
        db.close()
