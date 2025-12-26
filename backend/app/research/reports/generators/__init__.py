"""Report format generators."""

from .html_generator import HTMLGenerator, create_html_generator
from .pdf_generator import PDFGenerator, create_pdf_generator, is_pdf_available
from .style_guides import (
    TEMPLATE_STYLE_GUIDES,
    get_style_guide,
    format_style_guide_for_prompt,
    BASE_CSS
)


__all__ = [
    "HTMLGenerator",
    "create_html_generator",
    "PDFGenerator",
    "create_pdf_generator",
    "is_pdf_available",
    "TEMPLATE_STYLE_GUIDES",
    "get_style_guide",
    "format_style_guide_for_prompt",
    "BASE_CSS",
]
