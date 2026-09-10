from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ItemTypeEnum(str, Enum):
    lost = "lost"
    found = "found"

class ItemStatusEnum(str, Enum):
    active = "active"
    resolved = "resolved"

class UserMinResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class ItemBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=2, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=50)
    description: str = Field(..., min_length=5, max_length=5000)
    
    item_type: ItemTypeEnum = Field(..., description="Item type: lost or found")
    
    item_date: Optional[datetime] = None
    item_time: Optional[str] = None

    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    location_address: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None

    images: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    reward: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: ItemStatusEnum = ItemStatusEnum.active

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, min_length=5, max_length=5000)
    
    item_type: Optional[ItemTypeEnum] = None
    item_date: Optional[datetime] = None
    item_time: Optional[str] = None

    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    location_address: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None

    images: Optional[List[Dict[str, Any]]] = None
    reward: Optional[Dict[str, Any]] = None
    status: Optional[ItemStatusEnum] = None

class ItemResponse(BaseModel):
    id: int
    _id: int
    reported_by: int
    user_id: int
    item_type: ItemTypeEnum
    type: str
    
    title: str
    category: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    description: str
    
    item_date: Optional[datetime] = None
    item_time: Optional[str] = None
    
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_address: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    
    images: List[Dict[str, Any]] = Field(default_factory=list)
    image_url: Optional[str] = None
    reward: Dict[str, Any] = Field(default_factory=dict)
    status: ItemStatusEnum
    ai_processing_status: Optional[str] = "pending"
    distance_km: Optional[float] = None
    views: int = 0
    qr_code: Optional[Dict[str, Any]] = None
    
    created_at: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    
    reporter: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True

class PaginatedItemResponse(BaseModel):
    items: List[ItemResponse]
    page: int
    limit: int
    total: int
    pages: int
    hasNext: bool
    hasPrev: bool
