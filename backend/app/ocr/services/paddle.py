"""PaddleOCR service."""
from app.ocr.services.base import BaseOCRService, TimedExecution
from app.ocr.schemas import OCRResult, OCRCategory
from app.ocr.config import get_ocr_settings

# Optional import - may not be installed
try:
    from paddleocr import PaddleOCR as PaddleOCREngine
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


class PaddleOCR(BaseOCRService):
    """OCR using PaddleOCR."""

    engine_id = "paddle"
    engine_name = "PaddleOCR"
    category = OCRCategory.TRADITIONAL

    def __init__(self):
        settings = get_ocr_settings()
        self.lang = settings.paddleocr_lang
        self._engine = None

    def is_available(self) -> bool:
        """Check if PaddleOCR is installed."""
        return PADDLE_AVAILABLE

    def _get_engine(self):
        """Lazy load PaddleOCR engine."""
        if self._engine is None and PADDLE_AVAILABLE:
            self._engine = PaddleOCREngine(
                use_textline_orientation=True,
                lang=self.lang
            )
        return self._engine

    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image using PaddleOCR."""
        if not self.is_available():
            return self._create_result(
                success=False,
                error="PaddleOCR not installed. Run: pip install paddleocr paddlepaddle"
            )

        with TimedExecution() as timer:
            try:
                text = await self._run_ocr(image)
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

    async def _run_ocr(self, image: bytes) -> str:
        """Run PaddleOCR on image."""
        import numpy as np

        # Convert bytes to PIL images (handles PDFs)
        images = self.bytes_to_pil_images(image)
        engine = self._get_engine()

        all_lines = []
        for img in images:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)

            # Use predict() method (new PaddleOCR v3+ API)
            result = engine.predict(img_array)

            # New API returns OCRResult objects with rec_texts attribute
            if result and len(result) > 0:
                ocr_result = result[0]
                if hasattr(ocr_result, 'get') and 'rec_texts' in ocr_result:
                    texts = ocr_result['rec_texts']
                    all_lines.extend(texts)
                elif hasattr(ocr_result, 'rec_texts'):
                    all_lines.extend(ocr_result.rec_texts)

        return "\n".join(all_lines)
