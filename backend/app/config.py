"""
Application settings loaded from environment variables.

Uses pydantic-settings to validate and type-check all config values at startup.
Missing or invalid values will raise a clear error before the server starts.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """GitCompass backend configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "GitCompass"
    DEBUG: bool = False


settings = Settings()
