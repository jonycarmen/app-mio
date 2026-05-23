"""SMTP email service for sending verification codes."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.security.logging import security_logger


def is_email_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def send_verification_code(to_email: str, code: str) -> bool:
    """Send a 6-digit verification code via SMTP. Returns True on success."""
    if not is_email_configured():
        security_logger.error("EMAIL_SEND_FAIL | SMTP not configured")
        return False

    from_addr = settings.smtp_from or settings.smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Código de recuperación de contraseña"
    msg["From"] = from_addr
    msg["To"] = to_email

    text_body = (
        f"Tu código de verificación es: {code}\n"
        "Expira en 15 minutos.\n\n"
        "Si no solicitaste esto, ignora este mensaje."
    )
    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:2rem;">
  <div style="max-width:420px;margin:auto;background:#1e293b;border-radius:12px;padding:2rem;">
    <h2 style="margin:0 0 .5rem;color:#6366f1;">People Manager</h2>
    <p style="color:#94a3b8;margin:0 0 1.5rem;">Recuperación de contraseña</p>
    <p>Tu código de verificación es:</p>
    <div style="font-size:2.2rem;letter-spacing:10px;font-family:monospace;font-weight:700;
                color:#f8fafc;background:#0f172a;border-radius:8px;padding:1rem 1.5rem;
                text-align:center;margin:1rem 0;">{code}</div>
    <p style="color:#94a3b8;font-size:.875rem;">
      Este código expira en <strong style="color:#e2e8f0;">15 minutos</strong>.<br>
      Si no solicitaste esto, ignora este mensaje.
    </p>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(from_addr, to_email, msg.as_string())
        security_logger.info("EMAIL_SENT | to=%s", to_email)
        return True
    except Exception as exc:
        security_logger.error("EMAIL_SEND_FAIL | to=%s | error=%s", to_email, exc)
        return False
