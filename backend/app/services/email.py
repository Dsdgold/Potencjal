"""Email service – sends activation and notification emails via SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user)


def send_activation_email(to_email: str, full_name: str, token: str) -> bool:
    """Send account activation email with a link containing the token."""
    activation_url = f"{settings.app_url}/#activate/{token}"

    subject = "Potencjal – Aktywuj swoje konto"
    html = f"""\
<!DOCTYPE html>
<html lang="pl">
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#0a1628;font-family:system-ui,-apple-system,sans-serif">
  <div style="max-width:520px;margin:40px auto;background:#152238;border:1px solid #1e3354;border-radius:14px;padding:32px;color:#e5e7eb">
    <div style="text-align:center;margin-bottom:24px">
      <span style="font-weight:800;font-size:20px;color:#e5e7eb">
        <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#145efc;margin-right:8px;box-shadow:0 0 8px #145efc"></span>
        Potencjal
      </span>
    </div>
    <h1 style="font-size:22px;font-weight:800;color:#e5e7eb;margin:0 0 8px;text-align:center">Witaj, {full_name}!</h1>
    <p style="color:#bfbab5;font-size:14px;line-height:1.6;text-align:center;margin:0 0 24px">
      Dziekujemy za rejestracje w platformie Potencjal. Kliknij ponizszy przycisk, aby aktywowac swoje konto i rozpoczac ocene potencjalu klientów B2B.
    </p>
    <div style="text-align:center;margin-bottom:24px">
      <a href="{activation_url}"
         style="display:inline-block;background:linear-gradient(180deg,#145efc,#0d4fd4);color:#ffffff;
                font-size:14px;font-weight:700;padding:12px 32px;border-radius:10px;
                text-decoration:none;box-shadow:0 1px 3px rgba(0,0,0,.3)">
        Aktywuj konto
      </a>
    </div>
    <p style="color:#73706d;font-size:12px;text-align:center;margin:0 0 8px">
      Lub skopiuj ten link do przegladarki:
    </p>
    <p style="color:#145efc;font-size:12px;text-align:center;word-break:break-all;margin:0 0 24px">
      {activation_url}
    </p>
    <hr style="border:none;border-top:1px solid #1e3354;margin:16px 0"/>
    <p style="color:#73706d;font-size:11px;text-align:center;margin:0">
      Jesli nie rejestrowales/as sie w Potencjal, zignoruj ten email.
    </p>
  </div>
</body>
</html>"""

    text = f"""Witaj, {full_name}!

Dziekujemy za rejestracje w Potencjal.

Aktywuj konto klikajac w link:
{activation_url}

Jesli nie rejestrowales/as sie, zignoruj ten email.
"""

    return _send_email(to_email, subject, html, text)


def _send_email(to: str, subject: str, html: str, text: str) -> bool:
    if not _smtp_configured():
        logger.warning("SMTP not configured – email to %s not sent (subject: %s)", to, subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if settings.smtp_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)

        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, to, msg.as_string())
        server.quit()
        logger.info("Email sent to %s (subject: %s)", to, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False
