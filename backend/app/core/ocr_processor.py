"""
PDF processing and OCR using Gemini multimodal capabilities.
"""
import fitz  # PyMuPDF
from typing import Optional
import tiktoken

from app.core.gemini_client import get_gemini_client
from app.config import get_settings


class OCRProcessor:
    """Process documents using Gemini's native multimodal OCR."""

    def __init__(self):
        self.gemini = get_gemini_client()
        self.settings = get_settings()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def process_pdf(
        self,
        file_bytes: bytes,
        filename: str
    ) -> dict:
        """
        Process PDF using Gemini native vision.

        Returns:
            {
                "content": str,
                "metadata": dict,
                "size_class": "small" | "large",
                "chunks": list[dict] | None
            }
        """
        # Get page count for logging
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(pdf)
        pdf.close()

        # Use Gemini for OCR
        ocr_result = await self.gemini.ocr_pdf(file_bytes)

        content = ocr_result["content"]
        metadata = ocr_result["metadata"]
        metadata["filename"] = filename
        metadata["pages"] = page_count

        # Count tokens
        token_count = len(self.tokenizer.encode(content))
        metadata["token_count"] = token_count

        # Determine size class
        size_class = "small" if token_count < self.settings.small_doc_threshold_tokens else "large"

        result = {
            "content": content,
            "metadata": metadata,
            "size_class": size_class,
            "chunks": None
        }

        # Chunk large documents
        if size_class == "large":
            result["chunks"] = await self._create_contextual_chunks(content, filename)

        return result

    async def process_image(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str
    ) -> dict:
        """Process image files (PNG, JPG, etc.)."""
        from google.genai import types

        prompt = """
        Extract ALL text and content from this image.

        If this is a document scan:
        - Convert to clean Markdown
        - Preserve structure and formatting

        If this is a diagram/chart:
        - Describe the visual elements
        - Extract any text labels
        - Explain the relationships shown

        Output the content in Markdown format.
        """

        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                types.Part.from_text(text=prompt)
            ],
            config=types.GenerateContentConfig()
        )

        content = response.text
        token_count = len(self.tokenizer.encode(content))

        return {
            "content": content,
            "metadata": {
                "filename": filename,
                "mime_type": mime_type,
                "token_count": token_count
            },
            "size_class": "small",  # Images are typically small
            "chunks": None
        }

    async def _create_contextual_chunks(
        self,
        content: str,
        filename: str
    ) -> list[dict]:
        """
        Create semantically meaningful chunks with context metadata.
        Uses Gemini to identify natural boundaries.
        """
        # First, get suggested chunk boundaries from Gemini
        intelligence = await self.gemini.extract_document_intelligence(content, filename)

        suggested_boundaries = intelligence.get("suggested_chunk_boundaries", [])

        if suggested_boundaries:
            # Use AI-suggested boundaries
            chunks = self._split_by_boundaries(content, suggested_boundaries)
        else:
            # Fall back to semantic splitting
            chunks = self._semantic_split(content)

        # Enrich each chunk with context
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            enriched_chunks.append({
                "chunk_id": f"c{i+1}",
                "position": f"{i+1}/{len(chunks)}",
                "content": chunk["content"],
                "section": chunk.get("section", f"Section {i+1}"),
                "context": self._generate_chunk_context(chunk, chunks, i),
                "token_count": len(self.tokenizer.encode(chunk["content"]))
            })

        return enriched_chunks

    def _split_by_boundaries(
        self,
        content: str,
        boundaries: list[dict]
    ) -> list[dict]:
        """Split content using AI-suggested boundaries."""
        chunks = []
        current_pos = 0

        for boundary in boundaries:
            start_marker = boundary.get("start_marker", "")
            end_marker = boundary.get("end_marker", "")
            topic = boundary.get("topic", "")

            # Find markers in content
            start_idx = content.find(start_marker, current_pos)
            if start_idx == -1:
                continue

            end_idx = content.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                end_idx = len(content)

            chunk_content = content[start_idx:end_idx]
            if chunk_content.strip():
                chunks.append({
                    "content": chunk_content,
                    "section": topic
                })

            current_pos = end_idx

        # Get any remaining content
        if current_pos < len(content):
            remaining = content[current_pos:].strip()
            if remaining:
                chunks.append({
                    "content": remaining,
                    "section": "Remainder"
                })

        return chunks if chunks else self._semantic_split(content)

    def _semantic_split(self, content: str) -> list[dict]:
        """Fall back to semantic splitting by headers/sections."""
        import re

        # Split on major headers
        header_pattern = r'\n(#{1,3}\s+.+)\n'
        parts = re.split(header_pattern, content)

        chunks = []
        current_section = "Introduction"
        current_content = ""

        settings = get_settings()
        max_tokens = settings.chunk_size_tokens

        for part in parts:
            if re.match(r'^#{1,3}\s+', part):
                # This is a header
                if current_content.strip():
                    # Save previous chunk if it has content
                    chunks.append({
                        "content": current_content.strip(),
                        "section": current_section
                    })
                current_section = part.strip('# \n')
                current_content = part + "\n"
            else:
                # This is content
                test_content = current_content + part
                test_tokens = len(self.tokenizer.encode(test_content))

                if test_tokens > max_tokens and current_content.strip():
                    # Save current chunk and start new one
                    chunks.append({
                        "content": current_content.strip(),
                        "section": current_section
                    })
                    current_content = part
                else:
                    current_content = test_content

        # Don't forget the last chunk
        if current_content.strip():
            chunks.append({
                "content": current_content.strip(),
                "section": current_section
            })

        return chunks

    def _generate_chunk_context(
        self,
        chunk: dict,
        all_chunks: list[dict],
        index: int
    ) -> str:
        """Generate context string for a chunk."""
        parts = [f"This is section '{chunk.get('section', 'Unknown')}' of the document."]

        if index > 0:
            prev = all_chunks[index - 1]
            parts.append(f"Previous section: '{prev.get('section', 'Unknown')}'")

        if index < len(all_chunks) - 1:
            next_chunk = all_chunks[index + 1]
            parts.append(f"Next section: '{next_chunk.get('section', 'Unknown')}'")

        return " ".join(parts)


# Factory function
def get_ocr_processor() -> OCRProcessor:
    """Get OCR processor instance."""
    return OCRProcessor()
