"""Source credibility assessment service."""

from typing import List, Dict
from urllib.parse import urlparse

from google import genai
from google.genai import types

from app.config import get_settings
from ..schemas import Source


# Domain authority scores for known domains
DOMAIN_AUTHORITY = {
    # Government
    ".gov": 0.95,
    ".gov.uk": 0.95,
    ".gov.au": 0.95,
    ".mil": 0.90,
    # Academic
    ".edu": 0.90,
    ".ac.uk": 0.90,
    # Major news
    "reuters.com": 0.90,
    "apnews.com": 0.90,
    "bbc.com": 0.85,
    "bbc.co.uk": 0.85,
    "nytimes.com": 0.85,
    "washingtonpost.com": 0.85,
    "theguardian.com": 0.80,
    "wsj.com": 0.85,
    "ft.com": 0.85,
    "economist.com": 0.85,
    "bloomberg.com": 0.85,
    # Wire services
    "afp.com": 0.90,
    "dpa.com": 0.88,
    # Research
    "nature.com": 0.95,
    "science.org": 0.95,
    "sciencedirect.com": 0.90,
    "springer.com": 0.90,
    "arxiv.org": 0.85,
    # Reference
    "wikipedia.org": 0.70,
    "britannica.com": 0.85,
    # Corporate
    "linkedin.com": 0.60,
    "medium.com": 0.50,
    # Social
    "twitter.com": 0.40,
    "x.com": 0.40,
    "facebook.com": 0.35,
    "reddit.com": 0.45,
}

# Source type patterns
SOURCE_TYPE_PATTERNS = {
    "government": [".gov", ".mil", "parliament", "congress", "senate"],
    "academic": [".edu", ".ac.", "university", "journal", "research"],
    "news": ["news", "times", "post", "herald", "tribune", "reuters", "ap", "bbc"],
    "corporate": ["investor", "earnings", "sec.gov", "annual report"],
    "blog": ["blog", "medium.com", "substack", "wordpress"],
    "social": ["twitter", "x.com", "facebook", "linkedin", "reddit"],
    "wiki": ["wikipedia", "wiki"],
}


class CredibilityAssessor:
    """
    Assesses the credibility of web sources.

    Uses a combination of:
    - Domain authority scores
    - Source type classification
    - LLM-based content assessment (optional)
    """

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_research_model

    async def assess_batch(self, sources: List[Source]) -> List[Source]:
        """
        Assess credibility for a batch of sources.

        Args:
            sources: List of sources to assess

        Returns:
            Sources with credibility scores and factors
        """
        assessed = []
        for source in sources:
            assessed_source = await self.assess_source(source)
            assessed.append(assessed_source)
        return assessed

    async def assess_source(self, source: Source) -> Source:
        """
        Assess credibility for a single source.

        Args:
            source: Source to assess

        Returns:
            Source with credibility score and factors
        """
        factors = {}

        # Domain authority
        domain_score = self._get_domain_authority(source.domain or "")
        factors["domain_authority"] = domain_score

        # Source type
        source_type = self._classify_source_type(source.url, source.domain or "")
        source.source_type = source_type
        factors["source_type_score"] = self._get_source_type_score(source_type)

        # Title quality (basic heuristic)
        if source.title:
            title_score = self._assess_title_quality(source.title)
            factors["title_quality"] = title_score
        else:
            factors["title_quality"] = 0.5

        # Calculate composite score
        weights = {
            "domain_authority": 0.5,
            "source_type_score": 0.3,
            "title_quality": 0.2,
        }

        composite_score = sum(
            factors[k] * weights[k] for k in weights if k in factors
        )

        source.credibility_score = round(composite_score, 3)
        source.credibility_factors = factors

        return source

    def _get_domain_authority(self, domain: str) -> float:
        """Get domain authority score."""
        domain = domain.lower()

        # Check exact match
        if domain in DOMAIN_AUTHORITY:
            return DOMAIN_AUTHORITY[domain]

        # Check TLD patterns
        for pattern, score in DOMAIN_AUTHORITY.items():
            if pattern.startswith(".") and domain.endswith(pattern):
                return score

        # Check subdomain of known domain
        for known_domain, score in DOMAIN_AUTHORITY.items():
            if not known_domain.startswith(".") and domain.endswith(known_domain):
                return score

        # Default based on TLD
        if domain.endswith(".org"):
            return 0.65
        elif domain.endswith(".com"):
            return 0.55
        elif domain.endswith(".net"):
            return 0.50

        return 0.50  # Unknown

    def _classify_source_type(self, url: str, domain: str) -> str:
        """Classify the type of source."""
        url_lower = url.lower()
        domain_lower = domain.lower()

        for source_type, patterns in SOURCE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower or pattern in domain_lower:
                    return source_type

        return "unknown"

    def _get_source_type_score(self, source_type: str) -> float:
        """Get credibility score for source type."""
        scores = {
            "government": 0.90,
            "academic": 0.85,
            "news": 0.75,
            "corporate": 0.65,
            "wiki": 0.60,
            "blog": 0.50,
            "social": 0.40,
            "unknown": 0.50,
        }
        return scores.get(source_type, 0.50)

    def _assess_title_quality(self, title: str) -> float:
        """Basic title quality assessment."""
        score = 0.5

        # Penalize clickbait indicators
        clickbait_phrases = [
            "you won't believe",
            "shocking",
            "!!!!",
            "???",
            "click here",
            "this is why",
            "what happened next",
        ]
        for phrase in clickbait_phrases:
            if phrase.lower() in title.lower():
                score -= 0.1

        # Reward specificity indicators
        if any(char.isdigit() for char in title):  # Contains numbers/dates
            score += 0.1
        if len(title) > 20 and len(title) < 150:  # Reasonable length
            score += 0.1

        return max(0.1, min(1.0, score))

    async def assess_with_llm(
        self,
        source: Source,
        content_snippet: str,
    ) -> Source:
        """
        Use LLM for deeper credibility assessment.

        This is optional and more expensive, used for key sources.
        """
        prompt = f"""
Assess the credibility of this web source:

URL: {source.url}
Title: {source.title}
Domain: {source.domain}
Content Snippet: {content_snippet[:500] if content_snippet else 'N/A'}

Evaluate on a scale of 0.0-1.0:
1. Source authority: Is this a reputable source?
2. Content quality: Is the writing professional and factual?
3. Bias indicators: Are there signs of bias or agenda?
4. Verification: Can claims be independently verified?

Return JSON:
{{
    "credibility_score": 0.0-1.0,
    "source_authority": 0.0-1.0,
    "content_quality": 0.0-1.0,
    "bias_level": 0.0-1.0,
    "assessment": "Brief explanation"
}}
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=config,
            )

            import json
            result = json.loads(response.text)

            source.credibility_score = result.get("credibility_score", source.credibility_score)
            source.credibility_factors = {
                "source_authority": result.get("source_authority", 0.5),
                "content_quality": result.get("content_quality", 0.5),
                "bias_level": result.get("bias_level", 0.5),
                "llm_assessment": result.get("assessment", ""),
            }

        except Exception:
            pass  # Fall back to heuristic assessment

        return source
