"""OCR Services."""
from app.ocr.services.base import BaseOCRService
from app.ocr.services.openrouter import OpenRouterOCR
from app.ocr.services.mistral import MistralOCR
from app.ocr.services.qwen import QwenOCR
from app.ocr.services.paddle import PaddleOCR
from app.ocr.services.easy import EasyOCRService
from app.ocr.services.surya import SuryaOCR
from app.ocr.services.evaluator import OCREvaluator
from app.ocr.services.comparative_evaluator import ComparativeEvaluator

__all__ = [
    "BaseOCRService",
    "OpenRouterOCR",
    "MistralOCR",
    "QwenOCR",
    "PaddleOCR",
    "EasyOCRService",
    "SuryaOCR",
    "OCREvaluator",
    "ComparativeEvaluator",
]
