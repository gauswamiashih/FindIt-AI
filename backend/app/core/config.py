"""AI Service Configuration"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: Literal["development", "production", "test"] = "development"

    # CLIP Model
    CLIP_MODEL: str = "ViT-B-32"

    # Matching
    SIMILARITY_THRESHOLD: float = 0.85

    # Server callback (Deprecating slowly)
    SERVER_URL: str = "http://localhost:5000"
    SERVER_API_KEY: str = ""

    # Deployment / CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = ""
    DIRECT_DATABASE_URL: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Redis
    REDIS_URL: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
