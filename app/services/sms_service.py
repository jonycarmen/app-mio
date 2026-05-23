"""Twilio SMS service for sending verification codes (optional)."""
from app.config import settings
from app.security.logging import security_logger


def is_sms_configured() -> bool:
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    )


def send_verification_sms(to_phone: str, code: str) -> bool:
    """Send a 6-digit verification code via Twilio SMS. Returns True on success."""
    if not is_sms_configured():
        security_logger.error("SMS_SEND_FAIL | Twilio not configured")
        return False

    try:
        from twilio.rest import Client  # imported lazily so twilio is truly optional

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=f"People Manager: tu código de recuperación es {code}. Expira en 15 min.",
            from_=settings.twilio_from_number,
            to=to_phone,
        )
        security_logger.info("SMS_SENT | to=%s", to_phone)
        return True
    except Exception as exc:
        security_logger.error("SMS_SEND_FAIL | to=%s | error=%s", to_phone, exc)
        return False
