"""Base OCR service interface."""
import base64
import time
from abc import ABC, abstractmethod
from typing import Optional, List
from PIL import Image
import io

from app.ocr.schemas import OCRResult, OCRCategory


class BaseOCRService(ABC):
    """Abstract base class for OCR services."""

    engine_id: str = "base"
    engine_name: str = "Base OCR"
    category: OCRCategory = OCRCategory.TRADITIONAL

    @abstractmethod
    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image and extract text."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available."""
        pass

    def _create_result(
        self,
        text: str = "",
        success: bool = True,
        error: Optional[str] = None,
        processing_time_ms: float = 0,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> OCRResult:
        """Create standardized OCR result."""
        return OCRResult(
            engine=self.engine_id,
            category=self.category,
            text=text,
            success=success,
            error=error,
            processing_time_ms=processing_time_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            confidence=confidence
        )

    @staticmethod
    def image_to_base64(image_bytes: bytes) -> str:
        """Convert image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode("utf-8")

    @staticmethod
    def get_image_mime_type(image_bytes: bytes) -> str:
        """Detect image MIME type from bytes."""
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_bytes[:2] == b'\xff\xd8':
            return "image/jpeg"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            return "image/webp"
        elif image_bytes[:4] == b'%PDF':
            return "application/pdf"
        return "image/png"

    @staticmethod
    def resize_if_needed(
        image_bytes: bytes,
        max_size: int = 4096
    ) -> bytes:
        """Resize image if larger than max_size."""
        img = Image.open(io.BytesIO(image_bytes))
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        return image_bytes

    @staticmethod
    def bytes_to_pil_images(file_bytes: bytes) -> List[Image.Image]:
        """Convert file bytes to PIL Image(s). Handles both images and PDFs."""
        mime_type = BaseOCRService.get_image_mime_type(file_bytes)

        if mime_type == "application/pdf":
            # Convert PDF to images using PyMuPDF
            try:
                import fitz  # PyMuPDF
                images = []
                pdf = fitz.open(stream=file_bytes, filetype="pdf")
                for page_num in range(len(pdf)):
                    page = pdf[page_num]
                    # Render at 2x for better OCR quality
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes))
                    images.append(img)
                pdf.close()
                return images
            except ImportError:
                raise RuntimeError("PyMuPDF (fitz) required for PDF processing")
        else:
            # Regular image
            img = Image.open(io.BytesIO(file_bytes))
            return [img]

    @staticmethod
    def bytes_to_single_image(file_bytes: bytes) -> Image.Image:
        """Convert file bytes to a single PIL Image. For PDFs, returns first page."""
        images = BaseOCRService.bytes_to_pil_images(file_bytes)
        return images[0] if images else None


class TimedExecution:
    """Context manager for timing execution."""

    def __init__(self):
        self.start_time = 0
        self.elapsed_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
