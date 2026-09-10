from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models import User, Role
import logging

logger = logging.getLogger("findit.auth")

security = HTTPBearer(auto_error=False)

def verify_supabase_token(token: str) -> dict:
    """
    Verify the JWT token issued by Supabase Auth.
    """
    if not settings.JWT_SECRET:
        logger.warning("JWT_SECRET is not set; token verification will fail unless configured.")
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM], 
            audience="authenticated"
        )
        return payload
    except ExpiredSignatureError as e:
        logger.warning(f"JWT expired: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    payload = verify_supabase_token(token)
    
    supabase_id: str = payload.get("sub")
    email: str = payload.get("email")
    
    if not supabase_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub or email",
        )
    
    # Try to find existing user by supabase_id
    user = db.query(User).filter(User.supabase_id == supabase_id).first()
    
    if not user:
        # Fallback: check if user exists by email
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Update existing user with supabase_id
            user.supabase_id = supabase_id
            db.commit()
            db.refresh(user)
        else:
            # Create a new user based on Supabase identity
            user_metadata = payload.get("user_metadata", {})
            name = (
                user_metadata.get("full_name") 
                or user_metadata.get("name") 
                or email.split("@")[0]
            )
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

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional user dependency. Returns User model if valid Bearer token provided,
    otherwise returns None without raising 401.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials=credentials, db=db)
    except Exception:
        return None


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

