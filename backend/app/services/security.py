"""密码哈希与登录 token —— 纯标准库实现，零外部依赖。

- 密码：PBKDF2-HMAC-SHA256（盐 + 20 万次迭代），格式
  `pbkdf2_sha256$<iters>$<salt_b64>$<hash_b64>`。
- token：HMAC-SHA256 签名的 `<payload_b64url>.<sig_b64url>`（结构类 JWT），
  payload 含 `sub`(user_id) 与 `exp`(过期秒级时间戳)，密钥取自 settings.JWT_SECRET。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from app.config import settings

_ITERS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERS)
    return f"pbkdf2_sha256${_ITERS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(user_id: int, ttl_hours: Optional[int] = None) -> str:
    ttl = ttl_hours if ttl_hours is not None else settings.TOKEN_TTL_HOURS
    payload = {"sub": int(user_id), "exp": int(time.time()) + ttl * 3600}
    body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64u(hmac.new(settings.JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_token(token: str) -> Optional[int]:
    """返回 user_id；签名无效 / 过期 / 格式错误 → None。"""
    try:
        body, sig = token.split(".")
        expected = _b64u(hmac.new(settings.JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64u_dec(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return int(payload["sub"])
    except Exception:
        return None
