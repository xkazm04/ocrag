"""Quality filtering for extracted findings."""

from enum import Enum
from typing import Dict, Any, List, Tuple


class FindingQuality(str, Enum):
    """Quality levels for extracted findings."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FILTERED = "filtered"


class QualityFilter:
    """Quality filtering criteria for findings."""

    VAGUE_INDICATORS = [
        "something", "somehow", "maybe", "might be", "could be",
        "unclear", "unknown", "possibly", "perhaps", "probably",
        "seems", "appears", "likely", "unlikely", "may have",
        "it is said", "reportedly", "allegedly", "supposedly",
        "some people", "many believe", "some think",
    ]

    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
        self.min_content_length = 50
        self.max_vague_indicators = 2

    def evaluate(self, finding: Dict[str, Any]) -> Tuple[FindingQuality, List[str]]:
        """
        Evaluate finding quality.

        Returns:
            Tuple of (quality_level, reasons)
        """
        reasons = []
        content = finding.get("content", "")
        confidence = finding.get("confidence_score", 0.5)

        # Check content length
        if len(content) < self.min_content_length:
            reasons.append(f"Content too short ({len(content)} chars < {self.min_content_length})")
            return FindingQuality.FILTERED, reasons

        # Check confidence
        if confidence < self.min_confidence:
            reasons.append(f"Low confidence ({confidence:.2f} < {self.min_confidence})")
            return FindingQuality.FILTERED, reasons

        # Check vagueness
        content_lower = content.lower()
        vague_count = sum(1 for indicator in self.VAGUE_INDICATORS if indicator in content_lower)
        if vague_count > self.max_vague_indicators:
            reasons.append(f"Too vague ({vague_count} vague indicators found)")
            return FindingQuality.FILTERED, reasons

        # Determine quality level
        if confidence >= 0.8 and len(content) >= 100:
            return FindingQuality.HIGH, ["High confidence, substantial content"]
        elif confidence >= 0.6:
            return FindingQuality.MEDIUM, ["Meets minimum thresholds"]
        else:
            return FindingQuality.LOW, ["Passes minimum but below ideal thresholds"]
