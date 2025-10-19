from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Core Config
    # ------------------------------------------------------------------
    MODEL_URL: str = Field(
        "https://mythos-model.onrender.com/ask",
        description="URL of the Mythos Model service",
    )
    DB_URL: str = Field(
        "sqlite:///arbiter.db",
        description="SQLite database path for Arbiter state",
    )
    ARBITER_API_KEY: str | None = Field(
        default=None,
        description="Optional API key for secure Arbiter access",
    )

    # ------------------------------------------------------------------
    # Networking & Timeouts
    # ------------------------------------------------------------------
    MAX_RETRIES: int = Field(default=2, description="Max retries for model calls")
    REQUEST_TIMEOUT_SECS: float = Field(default=20.0, description="Model call timeout")
    RETRY_BACKOFF_SECS: float = Field(default=2.0, description="Initial retry backoff")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instantiate global settings object
settings = Settings()
