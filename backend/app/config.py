from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./modelmux.db"
    ADMIN_API_KEY: str = "admin-secret-key-change-me"
    DEFAULT_RATE_LIMIT_RPM: int = 60
    DEFAULT_RATE_LIMIT_TPM: int = 100000

    # Upstream provider credentials. Real providers fail-fast if their key
    # is unset; the mock provider does not read these.
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_TIMEOUT_SECONDS: float = 60.0

    class Config:
        env_file = ".env"
        extra = "ignore"  # tolerate keys for providers wired in later tasks


settings = Settings()
