import logging
import os
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.services import google_drive_media
from app.services.google_drive_media import GoogleDriveMediaError

logger = logging.getLogger("makeupart.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _request_id_from_header(value: str | None) -> str:
    candidate = (value or "").strip()
    if _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="8.0.0",
    docs_url="/docs" if settings.ENVIRONMENT.lower() != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT.lower() != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_origins_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    request_id = _request_id_from_header(request.headers.get("X-Request-ID"))
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception(
            "Unhandled request error request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
        return response
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            if settings.ENVIRONMENT.lower() == "production":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            logger.info(
                "%s %s -> %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                extra={"request_id": request_id},
            )


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "health": "/health",
        "readiness": "/health/ready",
        "media_readiness": "/health/media-ready",
        "api": settings.API_V1_STR,
    }


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/health/live", tags=["health"])
def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/media-ready", tags=["health"])
def media_readiness_check() -> dict[str, str]:
    """Verify that private durable storage is safe for customer photos."""
    drive_configured = any(
        value.strip()
        for value in (
            settings.GOOGLE_DRIVE_CLIENT_ID,
            settings.GOOGLE_DRIVE_CLIENT_SECRET,
            settings.GOOGLE_DRIVE_REFRESH_TOKEN,
        )
    )
    media_required = (
        settings.ENVIRONMENT.lower() == "production"
        or settings.REQUIRE_DURABLE_MEDIA
        or drive_configured
        or google_drive_media.uses_modal_volume()
    )
    if not media_required:
        return {"status": "ready", "storage": "local_only"}

    try:
        google_drive_media.verify_connection()
    except GoogleDriveMediaError:
        # This failure is visible through the dedicated media probe. It must
        # not cause Render to restart the API process used for login and clients.
        logger.exception("Private media storage readiness check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "media_storage_unavailable"},
        )

    return {"status": "ready", "storage": settings.MEDIA_STORAGE_BACKEND.lower()}


@app.get("/health/ready", tags=["health"])
def readiness_check() -> dict[str, str]:
    """Check the database/API dependencies required for ordinary requests.

    Durable media storage is checked separately by /health/media-ready.
    Photo persistence fails closed when the configured private media backend is unavailable.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "database_unavailable"},
        )

    return {
        "status": "ready",
        # Render sets this to the exact source commit running in production.
        "deployment_commit": os.getenv("RENDER_GIT_COMMIT", ""),
    }
