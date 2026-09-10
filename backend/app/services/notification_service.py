"""
Notification Service
Handles creation, querying, read-status updates, and email abstraction for user notifications.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Notification, NotificationType, Item, Match

logger = logging.getLogger("findit.services.notification")

class NotificationService:
    def create_in_app_notification(
        self,
        db: Session,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType = NotificationType.match_found,
        related_item_id: Optional[int] = None,
        related_match_id: Optional[int] = None
    ) -> Notification:
        """Create and persist an in-app notification record."""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            related_item_id=related_item_id,
            related_match_id=related_match_id,
            related_id=related_match_id or related_item_id,
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info(f"Notification created for user {user_id}: '{title}'")
        return notification

    def send_email_notification(
        self,
        user_email: str,
        title: str,
        message: str
    ) -> bool:
        """
        Email notification service abstraction.
        Preserves interface for external SMTP/SendGrid providers without hardcoding credentials.
        """
        logger.info(f"Email notification queued/sent to {user_email}: '{title}'")
        return True

    def notify_match(
        self,
        db: Session,
        match: Match,
        lost_item: Item,
        found_item: Item
    ):
        """
        Trigger notifications for a newly created match record.
        Notifies both the lost item reporter and found item reporter.
        """
        try:
            # 1. Notify Lost Item owner
            if lost_item and lost_item.reported_by:
                self.create_in_app_notification(
                    db=db,
                    user_id=lost_item.reported_by,
                    title="Potential Match Found! 🔍",
                    message="AI found a potential match for your lost item.",
                    type=NotificationType.match_found,
                    related_item_id=lost_item.id,
                    related_match_id=match.id
                )
                if lost_item.reporter and lost_item.reporter.email:
                    self.send_email_notification(
                        user_email=lost_item.reporter.email,
                        title="FindIt: Potential Match Found",
                        message=f"AI found a potential match for your item '{lost_item.title}'."
                    )

            # 2. Notify Found Item owner
            if found_item and found_item.reported_by and found_item.reported_by != lost_item.reported_by:
                self.create_in_app_notification(
                    db=db,
                    user_id=found_item.reported_by,
                    title="Potential Match Found! 🔍",
                    message="AI matched your found item with a reported lost item.",
                    type=NotificationType.match_found,
                    related_item_id=found_item.id,
                    related_match_id=match.id
                )
                if found_item.reporter and found_item.reporter.email:
                    self.send_email_notification(
                        user_email=found_item.reporter.email,
                        title="FindIt: Potential Match Found",
                        message=f"AI matched your found item '{found_item.title}' with a reported lost item."
                    )

        except Exception as exc:
            logger.error(f"Failed to deliver match notifications: {exc}")

    def get_user_notifications(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Notification], int]:
        """Retrieve paginated notifications for a specific user."""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        total = query.count()
        notifications = (
            query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return notifications, total

    def mark_as_read(
        self,
        db: Session,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """Mark a notification as read if it belongs to the user."""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if not notification:
            return None

        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification

    def get_unread_count(self, db: Session, user_id: int) -> int:
        """Get count of unread notifications for a specific user."""
        return (
            db.query(func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
            .scalar() or 0
        )

notification_service = NotificationService()
