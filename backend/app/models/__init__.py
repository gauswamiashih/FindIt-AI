from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional
import enum
from app.db.database import Base


class Role(str, enum.Enum):
    user = "user"
    admin = "admin"

class ItemType(str, enum.Enum):
    lost = "lost"
    found = "found"

class ItemCategory(str, enum.Enum):
    wallet = "wallet"
    phone = "phone"
    bag = "bag"
    keys = "keys"
    documents = "documents"
    electronics = "electronics"
    other = "other"


class ItemStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"

class AIProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class MatchStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"

class NotificationType(str, enum.Enum):
    match_found = "match_found"
    message = "message"
    system = "system"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    supabase_id = Column(String, unique=True, index=True, nullable=True) # ID from Supabase Auth
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True) # Nullable for OAuth users
    role = Column(Enum(Role), default=Role.user)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    stats = Column(JSON, default=dict) # To store e.g., {"lostItemsReported": 0, "foundItemsReported": 0, "successfulMatches": 0}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    items = relationship("Item", back_populates="reporter")
    notifications = relationship("Notification", back_populates="user")
    
from sqlalchemy import Index

class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_lat_lng", "location_lat", "location_lng"),
    )

    id = Column(Integer, primary_key=True, index=True)
    reported_by = Column(Integer, ForeignKey("users.id"))
    item_type = Column(Enum(ItemType), nullable=False, index=True) # 'lost' or 'found'
    
    title = Column(String, nullable=False)
    category = Column(String, index=True)
    brand = Column(String, index=True)
    color = Column(String, index=True)
    description = Column(Text)
    
    item_date = Column(DateTime(timezone=True))
    item_time = Column(String)
    
    # Location data
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    location_address = Column(String, nullable=True)
    location_city = Column(String, nullable=True)
    location_state = Column(String, nullable=True)
    location_country = Column(String, nullable=True)
    
    images = Column(JSON, default=list) # e.g. [{"url": "...", "publicId": "..."}]
    reward = Column(JSON, default=dict) # e.g. {"offered": True, "amount": 50, "currency": "USD"}
    
    status = Column(Enum(ItemStatus), default=ItemStatus.active, index=True)
    ai_processing_status = Column(Enum(AIProcessingStatus), default=AIProcessingStatus.pending, index=True)
    views = Column(Integer, default=0)

    qr_code = Column(JSON, nullable=True) # e.g. {"url": "...", "dataUrl": "..."}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    reporter = relationship("User", back_populates="items")
    # Matches where this item is the lost item
    lost_matches = relationship("Match", foreign_keys="[Match.lost_item_id]", back_populates="lost_item")
    # Matches where this item is the found item
    found_matches = relationship("Match", foreign_keys="[Match.found_item_id]", back_populates="found_item")

    @property
    def _id(self) -> int:
        return self.id

    @property
    def user_id(self) -> int:
        return self.reported_by

    @property
    def type(self) -> str:
        return self.item_type.value if self.item_type else "lost"

    @property
    def image_url(self) -> Optional[str]:
        if self.images and len(self.images) > 0 and isinstance(self.images[0], dict):
            return self.images[0].get("url")
        return None

    @property
    def location(self) -> dict:
        return {
            "type": "Point",
            "coordinates": [self.location_lng or 0, self.location_lat or 0],
            "address": self.location_address,
            "city": self.location_city,
            "state": self.location_state,
            "country": self.location_country,
        }

    @property
    def createdAt(self):
        return self.created_at

    @property
    def updatedAt(self):
        return self.updated_at



from sqlalchemy import UniqueConstraint

class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("lost_item_id", "found_item_id", name="uq_match_lost_found"),
    )

    id = Column(Integer, primary_key=True, index=True)
    lost_item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    found_item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    
    score = Column(Float, nullable=False)
    image_score = Column(Float, nullable=True)
    text_score = Column(Float, nullable=True)
    status = Column(Enum(MatchStatus), default=MatchStatus.pending, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lost_item = relationship("Item", foreign_keys=[lost_item_id], back_populates="lost_matches")
    found_item = relationship("Item", foreign_keys=[found_item_id], back_populates="found_matches")
    chat = relationship("Chat", back_populates="match", uselist=False)

    @property
    def _id(self) -> int:
        return self.id

    @property
    def combined_score(self) -> float:
        return self.score

    @property
    def createdAt(self):
        return self.created_at

    @property
    def updatedAt(self):
        return self.updated_at


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True, nullable=False)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    match = relationship("Match", back_populates="chat")
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    related_id = Column(Integer, nullable=True) # e.g. match_id or chat_id depending on type
    related_item_id = Column(Integer, nullable=True)
    related_match_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")

    @property
    def _id(self) -> int:
        return self.id

    @property
    def createdAt(self):
        return self.created_at

