"""Configuration settings for the career job extraction engine."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Adaptive Career Job Extraction Engine"
    DEBUG: bool = False

    # Discovery bounds
    MAX_DISCOVERY_DEPTH: int = 3
    MAX_VISITED_URLS: int = 20
    MAX_CANDIDATE_URLS: int = 10

    # ATS Detection Threshold
    CONFIDENCE_THRESHOLD: float = 0.6

    # HTTP limits and timeouts
    HTTP_TIMEOUT_SECONDS: float = 15.0
    MAX_REDIRECTS: int = 10

    # Detail enrichment concurrency
    DEFAULT_CONCURRENCY: int = 5

    # Playwright settings
    PLAYWRIGHT_TIMEOUT_MS: int = 10000
    PLAYWRIGHT_HEADLESS: bool = True

    # Default User Agent
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


settings = Settings()
