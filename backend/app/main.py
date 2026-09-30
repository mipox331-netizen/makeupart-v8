from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

if settings.ENVIRONMENT.lower() == "production" and settings.cors_origins_list == ["*"]:
    raise RuntimeError("CORS_ORIGINS must be explicit when ENVIRONMENT=production")

app = FastAPI(title=settings.PROJECT_NAME, version="8.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_origins_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}
