"""Frontend configuration settings."""
import os

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# OpenAI API Key (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API timeout settings (in seconds)
API_TIMEOUT = 180.0
API_TIMEOUT_SHORT = 10.0

# File upload settings
ALLOWED_DOC_TYPES = ["pdf", "png", "jpg", "jpeg", "webp", "md"]
ALLOWED_OPENAI_TYPES = ["pdf", "txt", "md", "docx"]

# Display settings
MAX_FILENAME_DISPLAY = 20
MAX_ANSWER_PREVIEW = 500
MAX_CONTENT_PREVIEW = 3000
DEFAULT_PREVIEW_CHARS = 1500

# Confidence thresholds
CONFIDENCE_HIGH = 0.7
CONFIDENCE_MEDIUM = 0.4
