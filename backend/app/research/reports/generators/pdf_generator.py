"""PDF report generator using WeasyPrint."""

import io
from typing import Optional

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # OSError can occur when WeasyPrint's required system libraries (GTK/GObject) are missing
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    FontConfiguration = None


class PDFGenerator:
    """
    Generates PDF reports from HTML using WeasyPrint.

    Converts styled HTML to high-quality PDF documents suitable
    for professional distribution.
    """

    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint is not installed. Install with: pip install weasyprint>=60.0"
            )
        self.font_config = FontConfiguration()

    def generate(
        self,
        html_content: str,
        additional_css: Optional[str] = None
    ) -> bytes:
        """
        Generate PDF from HTML content.

        Args:
            html_content: Complete HTML document string
            additional_css: Optional extra CSS for PDF-specific styling

        Returns:
            PDF file as bytes
        """
        # Create HTML document
        html_doc = HTML(string=html_content)

        # Prepare stylesheets
        stylesheets = []

        # Add PDF-specific styles
        pdf_css = self._get_pdf_styles()
        stylesheets.append(CSS(string=pdf_css, font_config=self.font_config))

        # Add any additional custom CSS
        if additional_css:
            stylesheets.append(CSS(string=additional_css, font_config=self.font_config))

        # Generate PDF
        pdf_buffer = io.BytesIO()
        html_doc.write_pdf(
            pdf_buffer,
            stylesheets=stylesheets,
            font_config=self.font_config
        )

        return pdf_buffer.getvalue()

    def generate_to_file(
        self,
        html_content: str,
        output_path: str,
        additional_css: Optional[str] = None
    ) -> str:
        """
        Generate PDF and save to file.

        Args:
            html_content: Complete HTML document string
            output_path: Path to save the PDF
            additional_css: Optional extra CSS for PDF-specific styling

        Returns:
            Path to generated PDF file
        """
        pdf_bytes = self.generate(html_content, additional_css)

        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

        return output_path

    def _get_pdf_styles(self) -> str:
        """Get PDF-specific CSS optimizations."""
        return """
/* PDF-specific styles */
@page {
    size: A4;
    margin: 2cm;

    @top-center {
        content: string(title);
        font-size: 9pt;
        color: #666;
    }

    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}

@page :first {
    @top-center {
        content: none;
    }
}

/* Set title for page headers */
h1 {
    string-set: title content();
}

/* Ensure good print quality */
body {
    font-size: 11pt;
    line-height: 1.5;
    orphans: 3;
    widows: 3;
}

/* Prevent page breaks in bad places */
h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
    page-break-inside: avoid;
}

table {
    page-break-inside: avoid;
}

tr {
    page-break-inside: avoid;
}

img {
    page-break-inside: avoid;
    max-width: 100%;
}

/* Ensure tables fit */
table {
    font-size: 10pt;
    width: 100%;
}

th, td {
    padding: 6pt 8pt;
}

/* Links in PDF */
a {
    color: #2563eb;
    text-decoration: none;
}

/* Code blocks */
pre, code {
    font-size: 9pt;
    background: #f5f5f5;
    padding: 2pt 4pt;
}

pre {
    padding: 8pt;
    overflow-wrap: break-word;
    white-space: pre-wrap;
}

/* Blockquotes */
blockquote {
    border-left: 3pt solid #3b82f6;
    padding-left: 12pt;
    margin-left: 0;
    color: #4b5563;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 0.5pt solid #d1d5db;
    margin: 16pt 0;
}

/* Lists */
ul, ol {
    padding-left: 20pt;
}

li {
    margin-bottom: 4pt;
}

/* Footer styling */
footer {
    margin-top: 24pt;
    padding-top: 12pt;
    border-top: 0.5pt solid #e5e7eb;
    font-size: 9pt;
    color: #6b7280;
}

/* Confidence indicators in print */
.confidence-high {
    color: #059669;
}

.confidence-medium {
    color: #d97706;
}

.confidence-low {
    color: #dc2626;
}
"""


def create_pdf_generator() -> PDFGenerator:
    """Factory function to create PDF generator."""
    return PDFGenerator()


def is_pdf_available() -> bool:
    """Check if PDF generation is available."""
    return WEASYPRINT_AVAILABLE
