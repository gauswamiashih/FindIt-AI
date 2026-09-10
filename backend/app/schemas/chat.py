from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class MessageCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

class UserMinInfo(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    id: int
    _id: int
    chat_id: int
    sender_id: int
    text: str
    message: str
    is_read: bool = False
    created_at: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    sender: Optional[UserMinInfo] = None

    model_config = ConfigDict(from_attributes=True)

class ChatResponse(BaseModel):
    id: int
    _id: int
    match_id: int
    user1_id: int
    user2_id: int
    created_at: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    other_user: Optional[UserMinInfo] = None
    last_message: Optional[MessageResponse] = None

    model_config = ConfigDict(from_attributes=True)

class ChatListResponse(BaseModel):
    chats: List[ChatResponse]
    total: int

class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
