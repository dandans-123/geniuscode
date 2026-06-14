from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./geniuscode.db"
    ADMIN_API_KEY: str = "admin-secret-key-change-me"
    DEFAULT_RATE_LIMIT_RPM: int = 60
    DEFAULT_RATE_LIMIT_TPM: int = 100000

    # ── 上游：aicodewith（GeniusCode 的唯一供货上游，OpenAI 兼容中转）──
    # 所有模型都转发到这里。base_url / key 以 aicodewith 控制台文档为准。
    AICODEWITH_API_KEY: Optional[str] = None
    AICODEWITH_BASE_URL: str = "https://api.aicodewith.com/v1"  # 占位，接入时按实际改
    AICODEWITH_TIMEOUT_SECONDS: float = 60.0

    # 上游 key 未配置时回落到 mock（本地开发/演示用）。生产环境应配好 key，
    # 或显式设为 False 让缺 key 直接 fail-fast，避免静默返回假数据。
    MOCK_WHEN_NO_UPSTREAM_KEY: bool = True

    # ── 会员制 / 用户登录态 ──
    JWT_SECRET: str = "geniuscode-dev-jwt-secret-change-me"  # 生产务必改
    TOKEN_TTL_HOURS: int = 720          # 控制台登录态有效期（30 天）
    FREE_TRIAL_CREDIT_CNY: float = 20.0  # 注册即送体验额度（¥）
    # 浏览器前端跨域来源（GitHub Pages 线上 + 本地开发）
    CORS_ORIGINS: str = "https://dandans-123.github.io,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500"

    # Upstream provider credentials. Real providers fail-fast if their key
    # is unset; the mock provider does not read these.
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_TIMEOUT_SECONDS: float = 60.0

    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_TIMEOUT_SECONDS: float = 60.0

    class Config:
        env_file = ".env"
        extra = "ignore"  # tolerate keys for providers wired in later tasks


settings = Settings()
