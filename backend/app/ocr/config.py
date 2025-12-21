"""OCR Benchmark configuration."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class OCRSettings(BaseSettings):
    """OCR-specific settings."""

    # OpenRouter API (for GPT, Gemini, Qwen)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Mistral API (for Mistral OCR)
    mistral_api_key: str = ""

    # Model IDs
    gpt_model: str = "openai/gpt-4o"  # Using available model
    gemini_model: str = "google/gemini-2.0-flash-001"  # Using available model
    qwen_model: str = "qwen/qwen-2-vl-72b-instruct"  # Using available model
    mistral_ocr_model: str = "mistral-ocr-latest"

    # Evaluation
    eval_model: str = "openai/gpt-4o"
    eval_temperature: float = 0.1

    # Processing
    max_file_size_mb: int = 50
    default_language: str = "en"

    # Traditional OCR settings
    paddleocr_lang: str = "en"
    easyocr_langs: str = "en"
    surya_langs: str = "en"

    # Feature flags
    chandra_enabled: bool = False
    traditional_ocr_enabled: bool = True

    class Config:
        env_prefix = ""
        extra = "ignore"

    @property
    def easyocr_lang_list(self) -> list[str]:
        """Parse EasyOCR languages."""
        return [l.strip() for l in self.easyocr_langs.split(",")]


@lru_cache
def get_ocr_settings() -> OCRSettings:
    """Get cached OCR settings."""
    return OCRSettings()
