from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class NotificationTypeEnum(str, Enum):
    match_found = "match_found"
    message = "message"
    system = "system"

class NotificationResponse(BaseModel):
    id: int
    _id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool = False
    related_id: Optional[int] = None
    related_item_id: Optional[int] = None
    related_match_id: Optional[int] = None
    created_at: Optional[datetime] = None
    createdAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int

class UnreadCountResponse(BaseModel):
    unread_count: int
