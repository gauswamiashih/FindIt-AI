"""
FindIt AI Service – Main Application Entry Point
FastAPI + CLIP-based image matching service
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.routes import match, health, embeddings, auth

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("findit.ai")


# ─── App Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Placeholder lifespan."""
    logger.info("🚀 Starting FindIt Service (AI Disabled for Free Tier)...")
    app.state.clip = None
    yield
    logger.info("🛑 Shutting down Service...")


# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="FindIt AI Service",
    description="AI-powered image matching service using CLIP embeddings for the FindIt platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
from app.middleware.rate_limit import RateLimitMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Internal Server Error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal server error occurred."}
    )

from app.api.routes import match, health, embeddings, auth, items, matches, notifications, chats, admin

# ─── API v1 Router ────────────────────────────────────────────────────────────
from fastapi import APIRouter
api_router = APIRouter(prefix="/api/v1")

# Include existing routes (migrating over time)
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(match.router, prefix="/match", tags=["Matching"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(items.router, prefix="/lost-items", tags=["Lost Items Legacy"])
api_router.include_router(items.router, prefix="/found-items", tags=["Found Items Legacy"])
api_router.include_router(matches.router, prefix="/matches", tags=["Matches"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(chats.router, prefix="/chats", tags=["Chats"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

app.include_router(api_router)



# Also include health on root for simple load balancer checks
app.include_router(health.router, tags=["Health"])

@app.get("/api/v1/test-500-trigger")
def trigger_test_500():
    raise Exception("Simulated Unhandled Server Error")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        workers=1,  # Single worker for GPU model
    )
