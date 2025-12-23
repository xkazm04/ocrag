"""Surya OCR service."""
from app.ocr.services.base import BaseOCRService, TimedExecution
from app.ocr.schemas import OCRResult, OCRCategory
from app.ocr.config import get_ocr_settings

# Optional import - may not be installed (API changed in v0.17+)
try:
    from surya.recognition import RecognitionPredictor, FoundationPredictor
    from surya.detection import DetectionPredictor
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
        self._det_predictor = None
        self._rec_predictor = None
        self._foundation_predictor = None

    def is_available(self) -> bool:
        """Check if Surya OCR is installed."""
        return SURYA_AVAILABLE

    def _load_models(self):
        """Lazy load Surya predictors."""
        if self._det_predictor is None and SURYA_AVAILABLE:
            self._det_predictor = DetectionPredictor()
            self._foundation_predictor = FoundationPredictor()
            self._rec_predictor = RecognitionPredictor(self._foundation_predictor)
        return self._det_predictor, self._rec_predictor

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
        # Convert bytes to PIL images (handles PDFs)
        images = self.bytes_to_pil_images(image)
        det_predictor, rec_predictor = self._load_models()

        all_lines = []
        for img in images:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # New API: pass det_predictor as keyword arg (not the detection results)
            # task_names are now task types, not language codes
            rec_results = rec_predictor([img], det_predictor=det_predictor)

            # Extract text from results
            if rec_results and rec_results[0]:
                for text_line in rec_results[0].text_lines:
                    all_lines.append(text_line.text)

        return "\n".join(all_lines)
