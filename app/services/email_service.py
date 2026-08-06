"""
Transactional email sending via plain SMTP (stdlib only, no extra dependency).

Gated by env vars the same way ANTHROPIC_API_KEY gates AI features elsewhere
in this app: if SMTP isn't configured, is_email_configured() is False and
callers fall back to their own dev-mode behavior instead of failing.

    SMTP_HOST       - e.g. smtp.gmail.com, smtp.sendgrid.net
    SMTP_PORT       - defaults to 587 (STARTTLS)
    SMTP_USERNAME   - SMTP auth username
    SMTP_PASSWORD   - SMTP auth password (an app password for Gmail, an API key for SendGrid, etc.)
    SMTP_FROM_EMAIL - "From" address; defaults to SMTP_USERNAME
    FRONTEND_URL    - base URL used to build the reset link; defaults to http://localhost:5173
"""
import os
import smtplib
from email.message import EmailMessage


def is_email_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD"))


def _send(to_email: str, subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    body = (
        "We received a request to reset your ResumeIQ password.\n\n"
        f"Reset your password: {reset_link}\n\n"
        "This link expires in 5 minutes. If you didn't request this, you can safely ignore this email."
    )
    _send(to_email, "Reset your ResumeIQ password", body)
