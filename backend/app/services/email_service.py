"""邮箱验证码:签发 / 校验 + SMTP 发信(标准库 smtplib)。

未配置 SMTP 时为开发模式:`issue_code` 返回 (code, dev_mode=True),由上层直接回传给前端,
不实际发邮件——便于本地/未接邮箱时测试。配好 SMTP 后真实发信、不回传验证码。
"""
from __future__ import annotations

import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_code import EmailCode

RESEND_INTERVAL_SEC = 60


def is_email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _send_email(to: str, code: str) -> None:
    sender = settings.SMTP_FROM or settings.SMTP_USER
    body = (
        f"您正在注册 GeniusCode,验证码为:\n\n    {code}\n\n"
        f"{settings.EMAIL_CODE_TTL_MIN} 分钟内有效。若非本人操作,请忽略本邮件。"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "GeniusCode 注册验证码"
    msg["From"] = formataddr(("GeniusCode", sender))
    msg["To"] = to
    ctx = ssl.create_default_context()
    if int(settings.SMTP_PORT) == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, 465, context=ctx, timeout=20) as s:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.sendmail(sender, [to], msg.as_string())
    else:
        with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT), timeout=20) as s:
            s.starttls(context=ctx)
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.sendmail(sender, [to], msg.as_string())


def issue_code(db: Session, email: str) -> tuple[str, bool]:
    """签发验证码并(在已配置 SMTP 时)发送。返回 (code, dev_mode)。

    dev_mode=True 表示未配 SMTP、未真实发信,code 应回传前端用于自助测试。
    """
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 已注册邮箱不再发码,引导去登录
    from app.models.user import User
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="该邮箱已注册,请直接登录")

    now = datetime.utcnow()
    latest = (
        db.query(EmailCode)
        .filter(EmailCode.email == email)
        .order_by(EmailCode.created_at.desc())
        .first()
    )
    if latest and (now - latest.created_at).total_seconds() < RESEND_INTERVAL_SEC:
        raise HTTPException(status_code=429, detail="验证码发送过于频繁,请稍后再试")

    code = f"{secrets.randbelow(1000000):06d}"
    db.query(EmailCode).filter(EmailCode.email == email).delete()
    db.add(EmailCode(email=email, code=code, expires_at=now + timedelta(minutes=settings.EMAIL_CODE_TTL_MIN)))
    db.commit()

    if is_email_configured():
        try:
            _send_email(email, code)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"邮件发送失败,请稍后再试({type(e).__name__})")
        return code, False
    # 开发模式:未配 SMTP,不发信,回传 code
    return code, True


def verify_code(db: Session, email: str, code: str) -> None:
    email = (email or "").strip().lower()
    rec = (
        db.query(EmailCode)
        .filter(EmailCode.email == email)
        .order_by(EmailCode.created_at.desc())
        .first()
    )
    if not rec or not code or rec.code != code.strip():
        raise HTTPException(status_code=400, detail="验证码错误")
    if rec.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="验证码已过期,请重新获取")
    # 一次性:用后即删
    db.query(EmailCode).filter(EmailCode.email == email).delete()
    db.commit()
