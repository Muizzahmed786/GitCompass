"""
Application settings loaded from environment variables.

Uses pydantic-settings to validate and type-check all config values at startup.
Missing or invalid values will raise a clear error before the server starts.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """GitCompass backend configuration."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
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

    # ── Gemini Primary Provider ─────────────────────────────
    GEMINI_API_KEY: str | None = None
    GEMINI_FLASH_MODEL: str = "gemini-3.5-flash"
    GEMINI_FLASH_LITE_MODEL: str = "gemini-3.5-flash-lite"
    MAX_COMMITS_FOR_SHIFT_DETECTION: int = 500

    # ── Groq Secondary Provider ─────────────────────────────
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TIMEOUT: int = 30


settings = Settings()
