"""Query normalization for duplicate detection.

Normalizes queries to improve cache hit rates and detect duplicates.
"""

import hashlib
import re
from typing import Set, Tuple


class QueryNormalizer:
    """Normalizes queries for consistent comparison and hashing."""

    # Common filler words to remove
    FILLER_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "about", "into", "through", "during", "before", "after", "above",
        "below", "from", "up", "down", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "also", "now", "please", "tell", "me",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "am", "and", "but", "if", "or", "because", "as", "until", "while",
        "although", "though", "whether", "however", "therefore", "thus",
    }

    # Question starters to normalize
    QUESTION_STARTERS = [
        r"^(can you |could you |would you |please |)",
        r"^(tell me |explain |describe |show me |)",
        r"^(what is |what are |what was |what were |)",
        r"^(who is |who are |who was |who were |)",
        r"^(why is |why are |why was |why were |why did |)",
        r"^(how is |how are |how was |how were |how did |how do |)",
        r"^(when is |when are |when was |when were |when did |)",
        r"^(where is |where are |where was |where were |)",
    ]

    def normalize(self, query: str) -> str:
        """
        Normalize query for comparison.

        Steps:
        1. Lowercase
        2. Remove question starters
        3. Remove punctuation except hyphens in compound words
        4. Remove filler words
        5. Sort remaining words
        6. Join with single spaces
        """
        # Lowercase
        text = query.lower().strip()

        # Remove question starters
        for pattern in self.QUESTION_STARTERS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Preserve compound words with hyphens
        text = re.sub(r"(\w)-(\w)", r"\1_HYPHEN_\2", text)

        # Remove punctuation
        text = re.sub(r"[^\w\s]", " ", text)

        # Restore hyphens
        text = text.replace("_HYPHEN_", "-")

        # Split into words
        words = text.split()

        # Remove filler words
        words = [w for w in words if w not in self.FILLER_WORDS and len(w) > 1]

        # Sort for consistent ordering
        words.sort()

        # Join
        return " ".join(words)

    def get_hash(self, query: str, length: int = 32) -> str:
        """Get deterministic hash of normalized query."""
        normalized = self.normalize(query)
        return hashlib.sha256(normalized.encode()).hexdigest()[:length]

    def extract_key_terms(self, query: str) -> Set[str]:
        """Extract key terms from query for similarity matching."""
        normalized = self.normalize(query)
        return set(normalized.split())

    def similarity_score(self, q1: str, q2: str) -> float:
        """
        Calculate Jaccard similarity between two queries.

        Returns:
            Float between 0.0 (no similarity) and 1.0 (identical)
        """
        terms1 = self.extract_key_terms(q1)
        terms2 = self.extract_key_terms(q2)

        if not terms1 or not terms2:
            return 0.0

        intersection = terms1 & terms2
        union = terms1 | terms2

        return len(intersection) / len(union)

    def is_likely_duplicate(
        self,
        q1: str,
        q2: str,
        threshold: float = 0.8
    ) -> Tuple[bool, float]:
        """
        Check if two queries are likely duplicates.

        Args:
            q1: First query
            q2: Second query
            threshold: Similarity threshold (default 0.8)

        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        # First check exact hash match
        if self.get_hash(q1) == self.get_hash(q2):
            return True, 1.0

        # Then check similarity
        score = self.similarity_score(q1, q2)
        return score >= threshold, score


# Module-level instance for convenience
_normalizer = QueryNormalizer()


def normalize_query(query: str) -> str:
    """Normalize a query string."""
    return _normalizer.normalize(query)


def get_query_hash(query: str) -> str:
    """Get hash of normalized query."""
    return _normalizer.get_hash(query)


def query_similarity(q1: str, q2: str) -> float:
    """Get similarity score between two queries."""
    return _normalizer.similarity_score(q1, q2)
