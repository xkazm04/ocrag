"""EasyOCR service."""
from app.ocr.services.base import BaseOCRService, TimedExecution
from app.ocr.schemas import OCRResult, OCRCategory
from app.ocr.config import get_ocr_settings

# Optional import - may not be installed
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


class EasyOCRService(BaseOCRService):
    """OCR using EasyOCR."""

    engine_id = "easy"
    engine_name = "EasyOCR"
    category = OCRCategory.TRADITIONAL

    def __init__(self):
        settings = get_ocr_settings()
        self.langs = settings.easyocr_lang_list
        self._reader = None

    def is_available(self) -> bool:
        """Check if EasyOCR is installed."""
        return EASYOCR_AVAILABLE

    def _get_reader(self, languages: list[str] = None):
        """Lazy load EasyOCR reader."""
        langs = languages or self.langs
        if self._reader is None and EASYOCR_AVAILABLE:
            self._reader = easyocr.Reader(langs, gpu=False)
        return self._reader

    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image using EasyOCR."""
        if not self.is_available():
            return self._create_result(
                success=False,
                error="EasyOCR not installed. Run: pip install easyocr"
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
        """Run EasyOCR on image."""
        import io
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image))
        img_array = np.array(img)

        reader = self._get_reader(languages)
        results = reader.readtext(img_array)

        # Extract text preserving order
        lines = []
        for detection in results:
            text = detection[1]
            lines.append(text)

        return "\n".join(lines)
