from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-only-secret-change-me-in-production"


class Settings(BaseSettings):
    """App configuration. Every field can be overridden with an env var of the same name
    (case-insensitive) or a `.env` file in the backend folder."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Smart Cart"
    environment: str = "development"  # development | test | production
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
    # Returns the OTP in the API response so you can log in without an SMS provider.
    # Must be False in production.
    otp_dev_mode: bool = True

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

    # Path to the built frontend (frontend/dist). When it exists the API also serves the web app.
    frontend_dist: str = "../frontend/dist"

    def validate_for_production(self) -> None:
        if self.environment != "production":
            return
        if self.secret_key == DEFAULT_SECRET:
            raise RuntimeError("Set SECRET_KEY before running in production.")
        if self.otp_dev_mode:
            raise RuntimeError("Set OTP_DEV_MODE=false before running in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
