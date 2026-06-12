"""
Application settings loaded from environment variables.

WHY: Centralizes all configuration in one place. Uses pydantic-settings
to automatically read from .env files and validate types at startup.
A junior dev never has to hunt for where DATABASE_URL is defined.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Face Detection Stream"
    DEBUG: bool = False

    # --- Database ---
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/facedetect"

    # Sync URL needed for Alembic migrations (asyncpg doesn't work with Alembic)
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@db:5432/facedetect"

    # --- Detection ---
    # Minimum confidence threshold for face detection (0.0 - 1.0)
    DETECTION_CONFIDENCE: float = 0.5

    # --- Stream ---
    # Max viewers that can watch the processed stream simultaneously
    MAX_VIEWERS: int = 10

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance. Created once, reused everywhere.
    WHY lru_cache: Avoids re-reading .env on every request.
    """
    return Settings()
