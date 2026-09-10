from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from app.schemas.item import ItemResponse

class MatchStatusEnum(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"

class MatchStatusUpdate(BaseModel):
    status: MatchStatusEnum

class MatchResponse(BaseModel):
    id: int
    _id: int
    lost_item_id: int
    found_item_id: int
    score: float
    similarity_score: float
    combined_score: float
    image_score: Optional[float] = None
    text_score: Optional[float] = None
    status: MatchStatusEnum
    created_at: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    lost_item: Optional[ItemResponse] = None
    found_item: Optional[ItemResponse] = None

    model_config = ConfigDict(from_attributes=True)

class MatchAnalyzeResponse(BaseModel):
    item_id: int
    total_candidates: int
    matches_created: int
    matches: List[MatchResponse]

class MatchListResponse(BaseModel):
    matches: List[MatchResponse]
    total: int
