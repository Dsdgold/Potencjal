"""Email service — Resend integration.

Will be fully implemented in Phase 4.
For now, provides a send_email stub that logs instead of sending.
"""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email via Resend API."""
    if not settings.resend_api_key:
        logger.info("Email skipped (no RESEND_API_KEY): to=%s subject=%s", to, subject)
        return False

    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.email_from,
            "to": to,
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent: to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        logger.error("Email failed: to=%s error=%s", to, exc)
        return False
