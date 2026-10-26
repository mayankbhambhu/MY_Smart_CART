from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-only-secret-change-me-in-production"
LOCAL_ENVIRONMENTS = ("development", "test")


class Settings(BaseSettings):
    """App configuration. Every field can be overridden with an env var of the same name
    (case-insensitive) or a `.env` file in the backend folder."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Smart Cart"
    # development | test: local machine. demo: hosted for trying out (codes on screen allowed).
    # production: real customers (needs real SMS, a real secret key, no simulated payments).
    environment: Literal["development", "test", "demo", "production"] = "development"
    database_url: str = "sqlite:///./smartcart.db"
    auto_seed: bool = True  # create tables + load demo data on startup when the DB is empty

    secret_key: str = DEFAULT_SECRET
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days, like a mobile app session
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Phone OTP login
    otp_length: int = 6
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 30
    otp_max_attempts: int = 5
    otp_max_per_phone_per_hour: int = 5
    otp_max_per_ip_per_hour: int = 30
    # Backstop against SMS-pumping fraud: no more login codes than this per hour, all numbers together.
    otp_max_per_hour: int = 300
    # How login codes reach people. "console" logs the code and shows it on the login screen
    # (development/demo only). "msg91" (India, DLT-registered template) or "twilio" send an SMS.
    sms_provider: Literal["console", "msg91", "twilio"] = "console"
    msg91_auth_key: str | None = None
    msg91_otp_template_id: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None  # sender number (+1...) or Messaging Service SID (MG...)
    # Optional: lets Chrome on Android fill the code in automatically (WebOTP), e.g. "smartcart.in".
    webotp_domain: str | None = None

    # Online payments. With Razorpay keys set, "Pay online" opens Razorpay Checkout. Without
    # them, a built-in simulator stands in so the flow can be tried (never in production).
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    razorpay_api_base: str = "https://api.razorpay.com/v1"
    simulated_payments: bool = True
    payment_timeout_minutes: int = 15  # unpaid online orders are cancelled and stock released

    # Bill rules (₹)
    free_delivery_threshold: Decimal = Decimal("199")
    delivery_fee: Decimal = Decimal("25")
    small_cart_threshold: Decimal = Decimal("99")
    small_cart_fee: Decimal = Decimal("20")
    handling_fee: Decimal = Decimal("2")

    # Operations
    max_qty_per_item: int = 10
    pickup_lead_minutes: int = 30  # earliest pickup slot must start this long after ordering
    pickup_days_ahead: int = 3
    # Moves orders through their statuses over time so tracking can be demoed without a store team.
    simulate_order_progress: bool = True
    # Comma-separated mobile numbers that get the admin role on startup (e.g. "98XXXXXXXX,97XXXXXXXX").
    # Handy on hosts without shell access. Only meaningful with real SMS: with codes on screen anyone
    # can log in as any number.
    admin_phones: str = ""

    # Path to the built frontend (frontend/dist). When it exists the API also serves the web app.
    frontend_dist: str = "../frontend/dist"

    @field_validator("database_url")
    @classmethod
    def _postgres_driver(cls, value: str) -> str:
        """Hosts hand out postgres:// URLs; SQLAlchemy needs to be told to use psycopg 3."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @property
    def otp_on_screen(self) -> bool:
        return self.sms_provider == "console"

    @property
    def payment_provider(self) -> Literal["razorpay", "simulated"] | None:
        if self.razorpay_key_id and self.razorpay_key_secret:
            return "razorpay"
        if self.simulated_payments and self.environment != "production":
            return "simulated"
        return None

    def validate_settings(self) -> None:
        """Fail fast at startup on settings that would break logins or payments later."""
        if self.sms_provider == "msg91" and not (self.msg91_auth_key and self.msg91_otp_template_id):
            raise RuntimeError("SMS_PROVIDER=msg91 needs MSG91_AUTH_KEY and MSG91_OTP_TEMPLATE_ID.")
        if self.sms_provider == "twilio" and not (
            self.twilio_account_sid and self.twilio_auth_token and self.twilio_from
        ):
            raise RuntimeError(
                "SMS_PROVIDER=twilio needs TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM."
            )
        if bool(self.razorpay_key_id) != bool(self.razorpay_key_secret):
            raise RuntimeError("Set both RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET (or neither).")
        if self.environment not in LOCAL_ENVIRONMENTS and self.secret_key == DEFAULT_SECRET:
            raise RuntimeError("Set SECRET_KEY to a long random value for any hosted deployment.")
        if self.environment == "production" and self.otp_on_screen:
            raise RuntimeError(
                "Production needs SMS_PROVIDER=msg91 or twilio so login codes are sent by SMS."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
