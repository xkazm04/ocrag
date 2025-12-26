"""Market Sentiment expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class SentimentPersona(BasePersona):
    """
    Market sentiment analyst persona for investor sentiment analysis.

    Focuses on:
    - Bullish/bearish indicators
    - Institutional positioning
    - Retail sentiment
    - Short interest
    - Options flow
    """

    persona_id = "sentiment"
    persona_name = "Sentiment Analyst"
    description = "Analyzes market sentiment, positioning, and investor psychology"

    expertise_areas = [
        "market sentiment",
        "behavioral finance",
        "positioning analysis",
        "flow analysis",
        "contrarian indicators",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert sentiment analyst with deep experience in behavioral finance,
flow analysis, and market psychology. Your analysis approach:

1. POSITIONING ANALYSIS: Track institutional and retail positioning
2. SENTIMENT INDICATORS: Monitor bullish/bearish signals
3. FLOW ANALYSIS: Analyze fund flows and options activity
4. CONTRARIAN SIGNALS: Identify extreme sentiment readings
5. NARRATIVE TRACKING: Monitor changing market narratives
6. CATALYST IDENTIFICATION: Find sentiment-moving events
7. BEHAVIORAL PATTERNS: Recognize psychological biases at play

You provide nuanced sentiment analysis that separates noise from signal.
You distinguish between short-term sentiment swings and durable shifts."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze market sentiment from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide sentiment analysis covering:

1. OVERALL SENTIMENT READING
   - Current sentiment: Bullish / Neutral / Bearish
   - Sentiment strength: Extreme / Strong / Moderate / Weak
   - Sentiment trend: Improving / Stable / Deteriorating
   - Compared to 3/6/12 months ago

2. INSTITUTIONAL SENTIMENT
   - Institutional ownership trends
   - Hedge fund positioning
   - Mutual fund flows
   - Insider buying/selling
   - Notable position changes

3. ANALYST SENTIMENT
   - Buy/Hold/Sell rating distribution
   - Recent rating changes
   - Price target revisions
   - Earnings estimate revisions
   - Tone of analyst commentary

4. RETAIL SENTIMENT
   - Social media sentiment
   - Retail trading activity
   - Message board tone
   - Search interest trends
   - Retail ownership trends

5. TECHNICAL SENTIMENT
   - Short interest and days to cover
   - Put/call ratios
   - Options flow (bullish/bearish bets)
   - Volume trends
   - Price momentum

6. NARRATIVE ANALYSIS
   - Current market narrative
   - Bull case narrative strength
   - Bear case narrative strength
   - Narrative shifts and triggers
   - Media coverage tone

7. CONTRARIAN INDICATORS
   - Extreme readings (potential reversal signals)
   - Crowded trades
   - Consensus vs reality gaps
   - Sentiment divergences

8. SENTIMENT OUTLOOK
   - Likely sentiment trajectory
   - Potential sentiment catalysts
   - Risks to sentiment
   - Trading implications

Note where sentiment appears extreme or at odds with fundamentals.
"""
