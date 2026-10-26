from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-only-secret-change-me-before-going-live"


class Settings(BaseSettings):
    """App settings, read from environment variables prefixed with SMARTCART_.

    Example: SMARTCART_DATABASE_URL=postgresql+psycopg://user:pass@host/db
    """

    model_config = SettingsConfigDict(env_prefix="SMARTCART_", env_file=".env", extra="ignore")

    app_name: str = "SmartCart"
    database_url: str = "sqlite:///./smartcart.db"

    # Dev mode returns the login OTP in the API response instead of sending an SMS.
    dev_mode: bool = True

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30

    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5

    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Seed the database with demo stores/products on startup when it is empty.
    seed_on_startup: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
