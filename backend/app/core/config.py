from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "MakeupArt V8"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    DATABASE_URL: str
    CORS_ORIGINS: str = ""
    MEDIA_ROOT: str = "./media"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    MAX_IMAGE_PIXELS: int = 40_000_000
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 1800
    LOG_LEVEL: str = "INFO"
    MEDIA_RETENTION_DAYS: int = 30
    REFRESH_SESSION_RETENTION_DAYS: int = 7
    SUBSCRIPTION_TRIAL_DAYS: int = 30
    PLATFORM_ADMIN_EMAILS: str = ""
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    LOGIN_LOCKOUT_MINUTES: int = 15

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def platform_admin_emails(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.PLATFORM_ADMIN_EMAILS.split(",")
            if email.strip()
        }

    @property
    def media_root_path(self) -> Path:
        return Path(self.MEDIA_ROOT).expanduser().resolve()

    def validate_runtime(self) -> None:
        if self.ENVIRONMENT.lower() == "production":
            if len(self.SECRET_KEY) < 32:
                raise RuntimeError("SECRET_KEY must be at least 32 characters in production")
            if "replace-with" in self.SECRET_KEY.lower() or self.SECRET_KEY.lower() in {"change-me", "changeme"}:
                raise RuntimeError("SECRET_KEY still contains a development placeholder")
            if self.cors_origins_list == ["*"]:
                raise RuntimeError("CORS_ORIGINS must be explicit in production")
            if any("example.com" in origin.lower() for origin in self.cors_origins_list):
                raise RuntimeError("CORS_ORIGINS still contains an example domain")
            if self.MAX_UPLOAD_BYTES <= 0 or self.MAX_IMAGE_PIXELS <= 0:
                raise RuntimeError("Production upload limits must be positive")
            if self.SUBSCRIPTION_TRIAL_DAYS < 0:
                raise RuntimeError("SUBSCRIPTION_TRIAL_DAYS cannot be negative")


@lru_cache
def get_settings() -> Settings:
    instance = Settings()
    instance.validate_runtime()
    return instance


settings = get_settings()
