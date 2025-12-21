"""
Semantic chunking for large documents.
Note: Primary chunking logic is in ocr_processor.py.
This module provides utility functions for chunking operations.
"""
import re
from typing import Optional
import tiktoken

from app.config import get_settings


class SemanticChunker:
    """Utility class for semantic document chunking."""

    def __init__(self):
        self.settings = get_settings()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def split_by_token_limit(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None
    ) -> list[str]:
        """
        Split text into chunks by token limit with overlap.

        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk (default from settings)
            overlap_tokens: Overlap between chunks (default from settings)

        Returns:
            List of text chunks
        """
        max_tokens = max_tokens or self.settings.chunk_size_tokens
        overlap_tokens = overlap_tokens or self.settings.chunk_overlap_tokens

        # Split into sentences
        sentences = self._split_into_sentences(text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))

                # Start new chunk with overlap
                overlap_text = " ".join(current_chunk[-3:])  # Keep last 3 sentences
                overlap_count = self.count_tokens(overlap_text)

                if overlap_count <= overlap_tokens:
                    current_chunk = current_chunk[-3:]
                    current_tokens = overlap_count
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def split_by_headers(self, text: str) -> list[dict]:
        """
        Split text by markdown headers.

        Returns:
            List of {"section": str, "content": str}
        """
        # Pattern to match markdown headers
        header_pattern = r'^(#{1,6})\s+(.+)$'

        lines = text.split('\n')
        sections = []
        current_section = "Introduction"
        current_content = []

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                # Save previous section if it has content
                if current_content:
                    sections.append({
                        "section": current_section,
                        "content": "\n".join(current_content).strip()
                    })

                # Start new section
                current_section = header_match.group(2).strip()
                current_content = [line]
            else:
                current_content.append(line)

        # Don't forget the last section
        if current_content:
            sections.append({
                "section": current_section,
                "content": "\n".join(current_content).strip()
            })

        return sections

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        # Handles common cases like Mr., Dr., etc.
        text = re.sub(r'(?<=[.!?])\s+', '\n', text)
        sentences = [s.strip() for s in text.split('\n') if s.strip()]
        return sentences

    def merge_small_chunks(
        self,
        chunks: list[str],
        min_tokens: int = 500
    ) -> list[str]:
        """
        Merge chunks that are too small.

        Args:
            chunks: List of text chunks
            min_tokens: Minimum tokens per chunk

        Returns:
            List of merged chunks
        """
        merged = []
        current = ""

        for chunk in chunks:
            if current:
                combined = current + "\n\n" + chunk
                combined_tokens = self.count_tokens(combined)

                if combined_tokens <= self.settings.chunk_size_tokens:
                    current = combined
                else:
                    merged.append(current)
                    current = chunk
            else:
                current = chunk

            # Check if current chunk is big enough
            if self.count_tokens(current) >= min_tokens:
                merged.append(current)
                current = ""

        # Don't forget the last one
        if current:
            merged.append(current)

        return merged


# Factory function
def get_chunker() -> SemanticChunker:
    """Get semantic chunker instance."""
    return SemanticChunker()
