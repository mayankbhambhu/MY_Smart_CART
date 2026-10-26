import logging

logger = logging.getLogger("smartcart.notifications")


def send_otp_sms(phone: str, code: str) -> None:
    """Hook for a real SMS gateway (MSG91, Twilio, Gupshup, ...). For now the code is only logged."""
    logger.info("OTP for %s: %s", phone, code)
