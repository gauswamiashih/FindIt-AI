from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.models import User
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter()

class UserResponse(BaseModel):
    id: int
    supabase_id: Optional[str]
    name: str
    email: str
    role: str
    is_verified: bool
    avatar_url: Optional[str]
    bio: Optional[str]
    stats: Dict
    
    class Config:
        from_attributes = True

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    Since Supabase handles the actual login/registration, this endpoint
    simply validates the Supabase JWT and returns the synchronized local User object.
    It's also useful for the frontend to verify the token is still valid.
    """
    return current_user
