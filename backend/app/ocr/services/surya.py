"""Surya OCR service."""
from app.ocr.services.base import BaseOCRService, TimedExecution
from app.ocr.schemas import OCRResult, OCRCategory
from app.ocr.config import get_ocr_settings

# Optional import - may not be installed
try:
    from surya.ocr import run_ocr
    from surya.model.detection.model import load_model as load_det_model
    from surya.model.recognition.model import load_model as load_rec_model
    SURYA_AVAILABLE = True
except ImportError:
    SURYA_AVAILABLE = False


class SuryaOCR(BaseOCRService):
    """OCR using Surya OCR."""

    engine_id = "surya"
    engine_name = "Surya OCR"
    category = OCRCategory.TRADITIONAL

    def __init__(self):
        settings = get_ocr_settings()
        self.langs = settings.surya_langs.split(",")
        self._det_model = None
        self._rec_model = None

    def is_available(self) -> bool:
        """Check if Surya OCR is installed."""
        return SURYA_AVAILABLE

    def _load_models(self):
        """Lazy load Surya models."""
        if self._det_model is None and SURYA_AVAILABLE:
            self._det_model = load_det_model()
            self._rec_model = load_rec_model()
        return self._det_model, self._rec_model

    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image using Surya OCR."""
        if not self.is_available():
            return self._create_result(
                success=False,
                error="Surya OCR not installed. Run: pip install surya-ocr"
            )

        with TimedExecution() as timer:
            try:
                text = await self._run_ocr(image, languages)
            except Exception as e:
                return self._create_result(
                    success=False,
                    error=str(e),
                    processing_time_ms=timer.elapsed_ms
                )

        return self._create_result(
            text=text,
            cost_usd=0.0,
            processing_time_ms=timer.elapsed_ms
        )

    async def _run_ocr(self, image: bytes, languages: list[str] = None) -> str:
        """Run Surya OCR on image."""
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(image))
        det_model, rec_model = self._load_models()
        langs = languages or self.langs

        results = run_ocr(
            [img],
            [langs],
            det_model,
            rec_model
        )

        # Extract text from results
        lines = []
        if results and results[0]:
            for text_line in results[0].text_lines:
                lines.append(text_line.text)

        return "\n".join(lines)
