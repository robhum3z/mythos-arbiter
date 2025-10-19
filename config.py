from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Configuration for the Mythos Arbiter service.
    Supports both local development and cloud deployment.
    """

    # Core URLs
    MODEL_URL: str = "https://mythos-model.onrender.com/ask"  # Cloud model endpoint
    LOCAL_MODEL_URL: Optional[str] = "http://127.0.0.1:8001/ask"  # Local dev fallback

    # Network + timeout tuning
    REQUEST_TIMEOUT_SECS: int = 20
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECS: float = 1.0

    # Database + logging (optional)
    DB_PATH: str = "arbiter.db"
    LOG_LEVEL: str = "INFO"

    # FastAPI metadata
    SERVICE_NAME: str = "Mythos Arbiter"
    SERVICE_VERSION: str = "0.2.1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
