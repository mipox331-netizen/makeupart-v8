import logging
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

logger = logging.getLogger("makeupart.api")

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
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception(
            "Unhandled request error",
            extra={"request_id": request_id, "path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
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


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/health/live", tags=["health"])
def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Readiness check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(exc)},
        )
    return {"status": "ready"}
