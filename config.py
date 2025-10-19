from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Mythos Model microservice (Phase 1)
    MODEL_URL: str = Field(default="https://mythos-model.onrender.com/ask")

    # Local DB for Arbiter metrics
    DB_URL: str = Field(default="sqlite:///arbiter.db")

    # Optional API key (set if you want to restrict calls)
    ARBITER_API_KEY: str = Field(default="", description="Optional API key for /ask endpoint")

    # Logging and scoring behaviour
    LOG_LEVEL: str = Field(default="INFO")
    EMA_ALPHA: float = Field(default=0.15)
    RETRY_BACKOFF_SECS: float = Field(default=1.2)
    MAX_RETRIES: int = Field(default=2)
    REQUEST_TIMEOUT_SECS: float = Field(default=12.0)

    # Optional link to Mythos Nest (Phase 2)
    NEST_URL: str = Field(default="https://mythos-nest.onrender.com")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
