"""Minimal SMTP email sending for transactional mail (currently: password
reset links only).

Works with any standard SMTP provider - Gmail (with an App Password),
Resend, SendGrid, Mailgun, etc. - since they all speak SMTP. Configure via
environment variables:

    SMTP_HOST=smtp.resend.com
    SMTP_PORT=587
    SMTP_USER=resend
    SMTP_PASSWORD=your_smtp_api_key_or_app_password
    SMTP_FROM=Rotryai <noreply@yourdomain.com>
    FRONTEND_URL=https://rotryai.vercel.app

Sending runs in a worker thread (via asyncio.to_thread) so it doesn't
block the event loop, since Python's smtplib is synchronous.
"""

import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("notrieai")


class EmailNotConfigured(Exception):
    """Raised when SMTP env vars are missing, so callers can turn this
    into a clean user-facing error instead of a raw exception."""


def _smtp_settings() -> dict:
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM")
    if not all([host, port, user, password, sender]):
        raise EmailNotConfigured(
            "Email is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD and SMTP_FROM as environment variables."
        )
    return {"host": host, "port": int(port), "user": user, "password": password, "sender": sender}


def _send_sync(to_email: str, subject: str, body_text: str) -> None:
    settings = _smtp_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings["sender"]
    msg["To"] = to_email
    msg.set_content(body_text)

    with smtplib.SMTP(settings["host"], settings["port"], timeout=10) as smtp:
        smtp.starttls()
        smtp.login(settings["user"], settings["password"])
        smtp.send_message(msg)


async def send_password_reset_email(to_email: str, reset_link: str) -> None:
    subject = "Reset your Rotryai password"
    body = (
        "We received a request to reset your Rotryai password.\n\n"
        f"Reset it here (this link expires in 30 minutes):\n{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email - "
        "your password will stay the same."
    )
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, body)
    except EmailNotConfigured:
        raise
    except Exception as exc:
        logger.exception("Failed to send password reset email")
        raise RuntimeError("Could not send the reset email right now.") from exc
