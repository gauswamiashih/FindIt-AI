from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.api.deps import get_current_user, verify_supabase_token
from app.core.config import settings
from app.db.database import get_db
from app.models import User
from app.schemas.auth import UserResponse, UserRegister, UserLogin, TokenResponse

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    Validates the Bearer JWT token issued by Supabase Auth and returns
    the synchronized application user record from PostgreSQL.
    """
    return current_user

@router.post("/register", response_model=UserResponse)
async def register(
    data: UserRegister, 
    db: Session = Depends(get_db)
):
    """
    Register a new user with Email/Password via Supabase Auth.
    If Supabase credentials are set, calls Supabase Auth API to sign up,
    then synchronizes the created user to PostgreSQL.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        # Development fallback when live Supabase URL is not configured
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        user = User(
            email=data.email,
            name=data.name,
            is_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/signup",
            headers={"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={
                "email": data.email,
                "password": data.password,
                "data": {"full_name": data.name}
            }
        )
        
    if response.status_code >= 400:
        err_msg = response.json().get("msg") or response.json().get("error_description") or "Registration failed"
        raise HTTPException(status_code=response.status_code, detail=err_msg)

    resp_data = response.json()
    supabase_user = resp_data.get("user") or resp_data
    supabase_id = supabase_user.get("id")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        user = User(
            supabase_id=supabase_id,
            email=data.email,
            name=data.name,
            is_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif supabase_id and not user.supabase_id:
        user.supabase_id = supabase_id
        db.commit()
        db.refresh(user)

    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin, 
    db: Session = Depends(get_db)
):
    """
    Authenticate an existing Email/Password user via Supabase Auth.
    Returns access token, refresh token, and synced User profile.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Supabase credentials not configured in backend .env"
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password",
            headers={"apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={
                "email": data.email,
                "password": data.password,
            }
        )

    if response.status_code >= 400:
        err = response.json()
        detail = err.get("error_description") or err.get("msg") or "Invalid login credentials"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    token_data = response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    payload = verify_supabase_token(access_token)
    supabase_id = payload.get("sub")
    email = payload.get("email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user_metadata = payload.get("user_metadata", {})
        name = user_metadata.get("full_name") or email.split("@")[0]
        user = User(
            supabase_id=supabase_id,
            email=email,
            name=name,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )

@router.post("/logout")
def logout():
    """
    Logout endpoint.
    Session invalidation is managed by Supabase Auth on the client side.
    """
    return {"message": "Successfully logged out"}
