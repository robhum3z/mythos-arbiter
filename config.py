from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Core Configuration
    # ------------------------------------------------------------------
    MODEL_URL: str = "https://mythos-model.onrender.com/ask"
    DB_URL: str = "sqlite:///arbiter.db"

    # ------------------------------------------------------------------
    # Arbiter Controls
    # ------------------------------------------------------------------
    ARBITER_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------
    # Scoring and Adaptation Constants
    # ------------------------------------------------------------------
    EMA_ALPHA: float = 0.15  # smoothing factor for exponential moving average
    RETRY_BACKOFF_SECS: float = 1.2
    MAX_RETRIES: int = 2
    REQUEST_TIMEOUT_SECS: float = 12.0

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
