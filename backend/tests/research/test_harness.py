"""Test harness for research templates.

Allows testing research templates without database persistence,
using Google's native Gemini client with Google Search grounding.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date

# Try relative import first, fall back to absolute
try:
    from .gemini_client import (
        GeminiResearchClient,
        SearchMode,
        TokenUsage,
        check_availability,
    )
    from .date_utils import (
        DateExtractor, TimelineBuilder, TimelineEvent,
        ExtractedDate, DatePrecision
    )
except ImportError:
    from gemini_client import (
        GeminiResearchClient,
        SearchMode,
        TokenUsage,
        check_availability,
    )
    from date_utils import (
        DateExtractor, TimelineBuilder, TimelineEvent,
        ExtractedDate, DatePrecision
    )


@dataclass
class TestSource:
    """Mock source for testing."""
    url: str
    title: str
    domain: str
    snippet: str
    source_type: str = "news"
    credibility_score: float = 0.7


@dataclass
class TestFinding:
    """Finding extracted during test."""
    finding_type: str
    content: str
    summary: Optional[str] = None
    temporal_context: str = "present"
    extracted_data: Optional[Dict] = None

    # Date fields for timeline ordering
    event_date: Optional[date] = None
    date_text: Optional[str] = None  # Original date string from LLM
    date_precision: str = "unknown"  # exact, month, year, range, approximate

    # Post-processed date from DateExtractor
    extracted_date: Optional[ExtractedDate] = None


@dataclass
class TestPerspective:
    """Analysis perspective result."""
    perspective_type: str
    analysis_text: str
    key_insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TokenStats:
    """Aggregated token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, usage: Optional[TokenUsage]):
        """Add token usage from a response."""
        if usage:
            self.input_tokens += usage.input_tokens
            self.output_tokens += usage.output_tokens
            self.total_tokens += usage.total_tokens

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class TestResult:
    """Complete test result."""
    query: str
    template_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Generated queries
    search_queries: List[str] = field(default_factory=list)

    # Search results
    sources: List[TestSource] = field(default_factory=list)
    synthesized_content: str = ""

    # Extracted findings
    findings: List[TestFinding] = field(default_factory=list)

    # Timeline (ordered events)
    timeline: List[TimelineEvent] = field(default_factory=list)

    # Perspective analyses
    perspectives: List[TestPerspective] = field(default_factory=list)

    # Detailed token metrics
    token_stats: TokenStats = field(default_factory=TokenStats)
    total_cost_usd: float = 0.0
    errors: List[str] = field(default_factory=list)

    # Backwards compatibility
    @property
    def total_tokens(self) -> int:
        return self.token_stats.total_tokens

    def add_tokens(self, token_usage: Optional[TokenUsage], cost: float = 0.0):
        """Track token usage."""
        self.token_stats.add(token_usage)
        self.total_cost_usd += cost or 0.0

    def get_events_by_date(self) -> List[TestFinding]:
        """Return event findings sorted by date."""
        events = [f for f in self.findings if f.finding_type == "event"]
        # Sort by extracted_date if available
        def sort_key(f):
            if f.extracted_date and f.extracted_date.date_start:
                d = f.extracted_date.date_start
                return (d.year, d.month, d.day)
            return (9999, 12, 31)
        return sorted(events, key=sort_key)


class ResearchTestHarness:
    """Test harness for research templates without DB."""

    # Investigative perspectives to test
    DEFAULT_PERSPECTIVES = ["political", "economic", "psychological", "historical"]

    def __init__(self, gemini_client: Optional[GeminiResearchClient] = None):
        # Check availability first
        avail = check_availability()
        if not avail["api_key_set"]:
            raise ValueError(
                "Google API key not set. Set GOOGLE_API_KEY or GEMINI_API_KEY env var."
            )
        if not avail["genai_available"]:
            raise ImportError("google-genai package not installed.")

        self.client = gemini_client or GeminiResearchClient(search_mode=SearchMode.GROUNDED)
        self.date_extractor = DateExtractor()
        self.timeline_builder = TimelineBuilder()

    async def run_test(
        self,
        query: str,
        template_type: str = "investigative",
        max_searches: int = 5,
        perspectives: Optional[List[str]] = None,
        granularity: str = "standard",
    ) -> TestResult:
        """Run a complete research test."""
        result = TestResult(
            query=query,
            template_type=template_type,
            started_at=datetime.now(),
        )

        perspectives = perspectives or self.DEFAULT_PERSPECTIVES

        try:
            # Step 1: Generate search queries
            print(f"\n{'='*60}")
            print(f"RESEARCH TEST: {query[:50]}...")
            print(f"{'='*60}\n")

            print("Step 1: Generating search queries...")
            queries, token_usage, cost = await self._generate_queries(
                query, max_searches, granularity
            )
            result.search_queries = queries
            result.add_tokens(token_usage, cost)
            print(f"  Generated {len(queries)} queries")

            # Step 2: Execute searches using Gemini's native Google Search
            print("\nStep 2: Executing web searches (Google Search via Gemini)...")
            all_sources = []
            all_content = []

            for i, q in enumerate(queries):
                print(f"  [{i+1}/{len(queries)}] {q[:50]}...")
                search_response = await self.client.grounded_search(q)
                result.add_tokens(
                    search_response.token_usage,
                    search_response.cost_usd or 0.0,
                )

                # Convert sources from grounded search
                for s in search_response.sources:
                    all_sources.append(TestSource(
                        url=s.url,
                        title=s.title,
                        domain=s.domain,
                        snippet=s.snippet,
                        source_type=s.source_type,
                    ))

                # The grounded search returns synthesized content in .text
                if search_response.text:
                    all_content.append(search_response.text)

            result.sources = all_sources
            result.synthesized_content = "\n\n---\n\n".join(all_content)
            print(f"  Found {len(all_sources)} sources")

            # Step 3: Extract findings
            print("\nStep 3: Extracting findings...")
            findings, token_usage, cost = await self._extract_findings(
                query, result.sources, result.synthesized_content
            )
            result.findings = findings
            result.add_tokens(token_usage, cost)
            print(f"  Extracted {len(findings)} findings")

            # Step 3b: Build timeline from event findings
            print("\nStep 3b: Building timeline...")
            result.timeline = self._build_timeline(result.findings)
            dated_events = len([e for e in result.timeline if e.extracted_date.date_start])
            print(f"  Built timeline with {len(result.timeline)} events ({dated_events} with dates)")

            # Step 4: Run perspective analyses
            print("\nStep 4: Running perspective analyses...")
            for perspective in perspectives:
                print(f"  Analyzing from {perspective} perspective...")
                analysis, token_usage, cost = await self._analyze_perspective(
                    query, perspective, result.findings, result.sources
                )
                result.perspectives.append(analysis)
                result.add_tokens(token_usage, cost)

            result.completed_at = datetime.now()
            print(f"\nTest completed in {(result.completed_at - result.started_at).seconds}s")
            ts = result.token_stats
            print(f"Total tokens: {ts.total_tokens:,} (input: {ts.input_tokens:,}, output: {ts.output_tokens:,})")
            print(f"Total cost: ${result.total_cost_usd:.4f}")

        except Exception as e:
            result.errors.append(str(e))
            print(f"\nError during test: {e}")
            raise

        return result

    async def _generate_queries(
        self,
        query: str,
        max_searches: int,
        granularity: str,
    ) -> tuple[List[str], Optional[TokenUsage], float]:
        """Generate search queries using the investigative template logic."""
        prompt = f"""
You are an investigative journalist planning research queries for a deep investigation.

Investigation Topic: {query}

Depth Level: {granularity}

Generate search queries covering these investigative angles:
1. KEY ACTORS: Who are the main people/organizations involved?
2. TIMELINE: What events happened and when?
3. LOCATIONS: Where did key events occur? What jurisdictions are involved?
4. MOTIVATIONS: What are the underlying interests and relationships?
5. METHODS: How were things done? What mechanisms were used?
6. MONEY TRAIL: Financial connections and transactions
7. OFFICIAL RECORDS: Government filings, court documents, regulatory actions
8. MEDIA COVERAGE: News reports, interviews, public statements

For a "{granularity}" depth level:
- "quick": Focus on 1-3 most critical angles
- "standard": Cover 4-5 key angles with balanced depth
- "deep": Comprehensive coverage of all angles with follow-up queries

Return a JSON array of exactly {max_searches} search query strings, ordered by importance.
Example: ["query about main actor", "query about key event", ...]
"""

        result, response = await self.client.generate_json(prompt)

        queries = []
        if isinstance(result, list):
            queries = result[:max_searches]

        return queries, response.token_usage, response.cost_usd or 0.0

    async def _extract_findings(
        self,
        query: str,
        sources: List[TestSource],
        synthesized_content: str,
    ) -> tuple[List[TestFinding], Optional[TokenUsage], float]:
        """Extract findings from synthesized content."""
        source_context = "\n".join([
            f"- {s.title} ({s.domain}): {s.snippet[:100]}..."
            for s in sources[:15]
        ])

        prompt = f"""
You are an investigative analyst extracting key findings for a deep investigation.

Investigation Topic: {query}

Synthesized Research Content:
{synthesized_content[:12000]}

Sources Referenced:
{source_context}

Extract findings in these investigative categories:

1. ACTORS (finding_type: "actor")
   - People, organizations, entities involved
   - Include: name, role, affiliations, significance

2. EVENTS (finding_type: "event")
   - Key incidents, actions, decisions
   - CRITICAL: Include specific date when known (e.g., "February 24, 2022")
   - Include: location, participants, outcome

3. RELATIONSHIPS (finding_type: "relationship")
   - Connections between actors
   - Types: financial, personal, professional, political

4. EVIDENCE (finding_type: "evidence")
   - Documents, statements, data points
   - Include: type, source, significance

5. PATTERNS (finding_type: "pattern")
   - Recurring behaviors, methods, structures

6. GAPS (finding_type: "gap")
   - Missing information, unanswered questions

Return a JSON array of finding objects. Each object must have these fields:
- finding_type: One of 'actor', 'event', 'relationship', 'evidence', 'pattern', 'gap'
- content: Detailed finding with specific facts. For EVENTS, always include the date in the content.
- summary: One sentence summary
- temporal_context: 'past', 'present', 'ongoing', or 'prediction'
- date_text: For events, the specific date or date range as a string (e.g., "February 24, 2022", "March 2014", "2014-2022"). Use null if no date is known.
- date_precision: One of 'exact' (full date), 'month' (month/year), 'year' (year only), 'range' (date range), 'unknown'

IMPORTANT: Return ONLY a valid JSON array. Do not include any markdown formatting, code blocks, or explanatory text.

Example format:
[
  {{"finding_type": "event", "content": "Russia invaded Ukraine on February 24, 2022", "summary": "Russian invasion began", "temporal_context": "past", "date_text": "February 24, 2022", "date_precision": "exact"}},
  {{"finding_type": "actor", "content": "Vladimir Putin ordered the invasion", "summary": "Putin as decision-maker", "temporal_context": "past", "date_text": null, "date_precision": "unknown"}}
]
"""

        result, response = await self.client.generate_json(prompt)

        findings = []

        # Handle None result (JSON parsing failed)
        if result is None:
            parse_error = getattr(response, 'parse_error', 'Unknown parsing error')
            print(f"[WARNING] Finding extraction failed - JSON parsing error: {parse_error}")
            print(f"[DEBUG] Raw response text length: {len(response.text) if response.text else 0}")

            # Try fallback: manually parse response.text
            if response.text:
                import json
                import re
                # Try to find JSON array in response
                array_match = re.search(r'\[[\s\S]*\]', response.text)
                if array_match:
                    try:
                        result = json.loads(array_match.group(0))
                        print(f"[INFO] Fallback parsing succeeded, found {len(result)} items")
                    except json.JSONDecodeError as e:
                        print(f"[WARNING] Fallback parsing also failed: {e}")

        if isinstance(result, list):
            for f in result:
                if isinstance(f, dict):
                    finding = TestFinding(
                        finding_type=f.get("finding_type", "fact"),
                        content=f.get("content", ""),
                        summary=f.get("summary"),
                        temporal_context=f.get("temporal_context", "present"),
                        extracted_data=f.get("extracted_data"),
                        date_text=f.get("date_text"),
                        date_precision=f.get("date_precision", "unknown"),
                    )

                    # Extract date from content using DateExtractor
                    self._extract_finding_date(finding)
                    findings.append(finding)
        elif result is not None:
            print(f"[WARNING] Unexpected result type: {type(result)}. Expected list.")

        if not findings:
            print(f"[WARNING] No findings extracted from response")

        return findings, response.token_usage, response.cost_usd or 0.0

    def _extract_finding_date(self, finding: TestFinding) -> None:
        """Extract and normalize date from a finding."""
        # First try the LLM-provided date_text
        if finding.date_text:
            extracted = self.date_extractor.extract(finding.date_text)
            if extracted.date_start:
                finding.extracted_date = extracted
                finding.event_date = extracted.date_start
                return

        # Fall back to extracting from content
        extracted = self.date_extractor.extract(finding.content)
        if extracted.date_start:
            finding.extracted_date = extracted
            finding.event_date = extracted.date_start

    def _build_timeline(self, findings: List[TestFinding]) -> List[TimelineEvent]:
        """Build ordered timeline from event findings."""
        # Filter to events and findings with dates
        events = [f for f in findings if f.finding_type == "event"]

        # Build timeline events
        timeline = self.timeline_builder.build_timeline(events)

        return timeline

    async def _analyze_perspective(
        self,
        query: str,
        perspective: str,
        findings: List[TestFinding],
        sources: List[TestSource],
    ) -> tuple[TestPerspective, Optional[TokenUsage], float]:
        """Run perspective analysis."""
        # Get perspective-specific system prompt
        system_prompts = {
            "political": "You are a political analyst specializing in international relations and geopolitics.",
            "economic": "You are an economist analyzing financial impacts and economic dynamics.",
            "psychological": "You are a psychologist analyzing human behavior and group dynamics.",
            "historical": "You are a historian providing historical context and parallels.",
            "military": "You are a military analyst assessing strategic and tactical aspects.",
        }

        findings_text = "\n".join([
            f"- [{f.finding_type}] {f.content[:200]}..."
            for f in findings[:15]
        ])

        prompt = f"""
Analyze the following research findings from your {perspective} perspective.

Research Topic: {query}

Key Findings:
{findings_text}

Provide your expert analysis including:
1. Your interpretation of these findings from a {perspective} viewpoint
2. Key insights that others might miss
3. Recommendations for further investigation
4. Warnings or risks to be aware of

Format as JSON:
{{
    "analysis_text": "Your detailed analysis...",
    "key_insights": ["insight 1", "insight 2", ...],
    "recommendations": ["recommendation 1", ...],
    "warnings": ["warning 1", ...]
}}
"""

        result, response = await self.client.generate_json(
            prompt,
            system_prompt=system_prompts.get(perspective, "You are an expert analyst."),
        )

        analysis = TestPerspective(
            perspective_type=perspective,
            analysis_text=result.get("analysis_text", "") if result else response.text,
            key_insights=result.get("key_insights", []) if result else [],
            recommendations=result.get("recommendations", []) if result else [],
            warnings=result.get("warnings", []) if result else [],
        )

        return analysis, response.token_usage, response.cost_usd or 0.0
