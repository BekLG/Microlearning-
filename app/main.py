import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.middleware.gzip import GZipMiddleware

from app.api import auth, documents
from app.core.config import get_settings
from app.core.exceptions import AIProviderUnavailableError, StorageError
from app.services.ai_service import AIService
from app.services.storage_service import StorageService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Verify OpenRouter is reachable before accepting traffic
    try:
        ai = AIService(settings)
        await ai.health_check()
        print("✓ OpenRouter is reachable")
    except AIProviderUnavailableError:
        print("⚠ Warning: OpenRouter not reachable with current credentials")
        print("  Document processing will fail until the AI provider is reachable.")

    # Verify Cloudinary credentials
    try:
        storage = StorageService(settings)
        storage.ensure_bucket()
        print("✓ Cloudinary is reachable")
    except StorageError:
        print("⚠ Warning: Cloudinary not reachable with current credentials")
        print("  Document uploads will fail until storage is configured correctly.")

    yield


app = FastAPI(
    title="AI Micro-Learning Backend",
    lifespan=lifespan,
    docs_url="/docs",  # Disable in production
    redoc_url=None,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    settings = get_settings()
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if settings.APP_ENV != "development":
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# CORS - configure allowed origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted host middleware - prevents host header attacks
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Catch database connection errors - don't expose internal details
    if "password authentication failed" in str(exc):
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable"}
        )
    
    if "connection refused" in str(exc).lower() or "could not connect" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable"}
        )
    
    # Catch storage errors
    if isinstance(exc, StorageError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Storage service temporarily unavailable"},
        )
    
    # Generic database errors
    if isinstance(exc, (DBAPIError, OperationalError)):
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable"}
        )
    
    # Fallback for any other unhandled exception - don't expose details
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(auth.router)
app.include_router(documents.router)
