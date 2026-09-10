"""
Chat Service
Handles creation, membership authorization, message persistence, and notifications for real-time chats.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.models import Chat, Message, Match, Item, User, NotificationType
from app.services.notification_service import notification_service

logger = logging.getLogger("findit.services.chat")

class ChatService:
    def get_or_create_chat(self, db: Session, match_id: int, user_id: int) -> Optional[Chat]:
        """
        Get existing chat or create a new chat for a confirmed match.
        Requires user_id to be an owner of an item involved in the match.
        """
        match = (
            db.query(Match)
            .options(joinedload(Match.lost_item), joinedload(Match.found_item))
            .filter(Match.id == match_id)
            .first()
        )
        if not match or not match.lost_item or not match.found_item:
            return None

        u1 = match.lost_item.reported_by
        u2 = match.found_item.reported_by

        if user_id != u1 and user_id != u2:
            logger.warning(f"User {user_id} unauthorized to open chat for match {match_id}")
            return None

        chat = db.query(Chat).filter(Chat.match_id == match_id).first()
        if not chat:
            chat = Chat(match_id=match_id, user1_id=u1, user2_id=u2)
            db.add(chat)
            db.commit()
            db.refresh(chat)
            logger.info(f"Created chat {chat.id} for match {match_id}")

        return chat

    def get_user_chats(self, db: Session, user_id: int) -> List[Chat]:
        """Retrieve all chats involving the specified user."""
        return (
            db.query(Chat)
            .options(
                joinedload(Chat.messages),
                joinedload(Chat.match).joinedload(Match.lost_item),
                joinedload(Chat.match).joinedload(Match.found_item)
            )
            .filter(or_(Chat.user1_id == user_id, Chat.user2_id == user_id))
            .order_by(Chat.updated_at.desc())
            .all()
        )

    def get_chat_by_id(self, db: Session, chat_id: int, user_id: int) -> Optional[Chat]:
        """Retrieve single chat by ID ensuring membership authorization."""
        chat = (
            db.query(Chat)
            .options(
                joinedload(Chat.messages),
                joinedload(Chat.match).joinedload(Match.lost_item),
                joinedload(Chat.match).joinedload(Match.found_item)
            )
            .filter(Chat.id == chat_id)
            .first()
        )
        if not chat:
            return None
        if chat.user1_id != user_id and chat.user2_id != user_id:
            return None
        return chat

    def get_chat_messages(
        self,
        db: Session,
        chat_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Message], int]:
        """Retrieve paginated messages for a chat with user membership verification."""
        chat = self.get_chat_by_id(db, chat_id, user_id)
        if not chat:
            return [], 0

        query = db.query(Message).filter(Message.chat_id == chat_id)
        total = query.count()
        messages = (
            query.order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return messages, total

    def create_message(
        self,
        db: Session,
        chat_id: int,
        sender_id: int,
        text: str
    ) -> Optional[Message]:
        """Create and persist a message in a chat, updating chat timestamp and notifying recipient."""
        chat = self.get_chat_by_id(db, chat_id, sender_id)
        if not chat:
            return None

        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            is_read=False
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        # Notify other participant
        recipient_id = chat.user2_id if sender_id == chat.user1_id else chat.user1_id
        try:
            sender_user = db.query(User).filter(User.id == sender_id).first()
            sender_name = sender_user.name if sender_user else "Someone"
            notification_service.create_in_app_notification(
                db=db,
                user_id=recipient_id,
                title="New Message 💬",
                message=f"{sender_name}: '{text[:50]}...'",
                type=NotificationType.message,
                related_match_id=chat.match_id
            )
        except Exception as e:
            logger.warning(f"Failed to deliver chat notification: {e}")

        return message

chat_service = ChatService()
