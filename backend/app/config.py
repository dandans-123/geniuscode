from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./modelmux.db"
    ADMIN_API_KEY: str = "admin-secret-key-change-me"
    DEFAULT_RATE_LIMIT_RPM: int = 60
    DEFAULT_RATE_LIMIT_TPM: int = 100000

    class Config:
        env_file = ".env"


settings = Settings()
