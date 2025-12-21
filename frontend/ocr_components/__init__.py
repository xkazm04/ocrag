"""OCR Benchmark components."""
from frontend.ocr_components.styles import apply_ocr_styles
from frontend.ocr_components.uploader import render_uploader
from frontend.ocr_components.results import render_results
from frontend.ocr_components.evaluation import render_evaluation

__all__ = [
    "apply_ocr_styles",
    "render_uploader",
    "render_results",
    "render_evaluation",
]
