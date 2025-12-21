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
                use_angle_cls=True,
                lang=self.lang,
                show_log=False
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
        import io
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image))
        img_array = np.array(img)

        engine = self._get_engine()
        result = engine.ocr(img_array, cls=True)

        # Extract text from results
        lines = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) > 1:
                    text = line[1][0] if isinstance(line[1], tuple) else line[1]
                    lines.append(text)

        return "\n".join(lines)
