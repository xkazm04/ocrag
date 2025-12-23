"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    gemini_api_key: str = ""

    # Database (optional - can run without DBs for OCR benchmark)
    postgres_url: str | None = None
    weaviate_url: str | None = "http://localhost:8080"

    # Document processing
    small_doc_threshold_tokens: int = 50000  # ~35-40 pages
    chunk_size_tokens: int = 8000
    chunk_overlap_tokens: int = 500

    # Gemini settings
    gemini_model: str = "gemini-2.0-flash"
    default_thinking_level: str = "medium"

    # Storage
    storage_path: str = "/app/storage"

    # Environment
    environment: str = "development"

    class Config:
        env_file = "../.env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
