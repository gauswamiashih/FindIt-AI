"""
Email Service Abstraction
Provides SMTP sending capability using environment variable credentials.
Safely logs execution without exposing passwords or failing if credentials are absent.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("findit.services.email")

class EmailService:
    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "") or ""
        self.smtp_port = int(getattr(settings, "SMTP_PORT", 587) or 587)
        self.smtp_username = getattr(settings, "SMTP_USERNAME", "") or ""
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "") or ""
        self.email_from = getattr(settings, "EMAIL_FROM", "noreply@findit.app") or "noreply@findit.app"

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """
        Send an email via SMTP if credentials are configured.
        Falls back safely to logging in development/test environments.
        """
        if not self.smtp_host or not self.smtp_username:
            logger.info(f"[Email Mock/Fallback] To: {to_email} | Subject: '{subject}' | Content: {body[:60]}...")
            return True

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_from
            msg["To"] = to_email
            msg["Subject"] = subject

            mime_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, mime_type))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email successfully delivered to {to_email}")
            return True

        except Exception as exc:
            logger.error(f"Failed to send email to {to_email}: {exc}")
            return False

email_service = EmailService()
