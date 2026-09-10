from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User, Role
import logging

logger = logging.getLogger("findit.auth")

security = HTTPBearer()

def verify_supabase_token(token: str) -> dict:
    """
    Verify the JWT token issued by Supabase Auth.
    """
    try:
        # Supabase uses HS256 by default to sign JWTs with the project's JWT secret
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=["HS256"], 
            audience="authenticated"
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Validates the Supabase JWT, creates the user in the local DB if they don't exist,
    and returns the local User model instance.
    """
    token = credentials.credentials
    payload = verify_supabase_token(token)
    
    supabase_id: str = payload.get("sub")
    email: str = payload.get("email")
    
    if supabase_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing required fields (sub, email)",
        )
    
    # Try to find existing user by supabase_id
    user = db.query(User).filter(User.supabase_id == supabase_id).first()
    
    if not user:
        # Fallback: check if user exists by email (e.g., if they were created before we added supabase_id)
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Update existing user with supabase_id
            user.supabase_id = supabase_id
            db.commit()
            db.refresh(user)
        else:
            # Create a new user based on Supabase identity
            # The 'user_metadata' claim often contains the user's name if they used Google OAuth
            user_metadata = payload.get("user_metadata", {})
            name = user_metadata.get("full_name") or user_metadata.get("name") or email.split("@")[0]
            avatar_url = user_metadata.get("avatar_url") or user_metadata.get("picture")
            
            user = User(
                supabase_id=supabase_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
                is_verified=True, # OAuth emails from Google are verified
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current authenticated user and assert they have the admin role.
    """
    if current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
