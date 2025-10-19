from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Core configuration
    MODEL_URL: str = Field(
        "https://mythos-model.onrender.com/ask",
        description="URL of the Mythos Model endpoint"
    )
    DB_URL: str = Field(
        "sqlite:///arbiter.db",
        description="SQLite DB file (auto-created if missing)"
    )
    ARBITER_API_KEY: str | None = Field(
        default=None,
        description="Optional API key for access control"
    )

    # Runtime behaviour
    MAX_RETRIES: int = Field(default=2)
    REQUEST_TIMEOUT_SECS: float = Field(default=20.0)
    RETRY_BACKOFF_SECS: float = Field(default=2.0)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


try:
    settings = Settings()
except Exception as e:
    # If something’s badly wrong, print it but keep running
    print(f"⚠️ Config load warning: {e}")
    settings = Settings(_env_file=None)
