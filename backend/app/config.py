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
    AICODEWITH_BASE_URL: str = "https://api.aicodewith.com/v1"  # OpenAI 兼容端点，占位
    # Anthropic 格式端点(供 Claude Code /v1/messages 透传)。以 aicodewith 文档为准。
    AICODEWITH_ANTHROPIC_BASE_URL: str = "https://api.aicodewith.com"
    AICODEWITH_TIMEOUT_SECONDS: float = 60.0

    # 上游 key 未配置时回落到 mock（本地开发/演示用）。生产环境应配好 key，
    # 或显式设为 False 让缺 key 直接 fail-fast，避免静默返回假数据。
    MOCK_WHEN_NO_UPSTREAM_KEY: bool = True

    # ── 邮箱验证(SMTP)──
    # 未配置(SMTP_HOST 为空)时,注册走开发模式:验证码直接在接口返回、不发邮件。
    # 配好后即真实发信。Gmail 示例:HOST=smtp.gmail.com PORT=587 USER=你的gmail PASSWORD=应用专用密码
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""           # 发件人地址,留空则用 SMTP_USER
    EMAIL_CODE_TTL_MIN: int = 10  # 验证码有效期(分钟)

    # ── 会员制 / 用户登录态 ──
    # 管理员邮箱(逗号分隔)。这些账号登录后可访问分组管理等运营功能。
    ADMIN_EMAILS: str = "liuchulong163@gmail.com"
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
