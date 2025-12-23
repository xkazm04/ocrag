"""Perspective Runner.

Orchestrates running multiple perspective agents on research findings.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type

from .base import BasePerspectiveAgent, PerspectiveContext
from .agents import (
    HistoricalAgent,
    FinancialAgent,
    JournalistAgent,
    ConspiratorAgent,
    NetworkAgent,
)

# Handle imports
try:
    from ..inference_client import InferenceClient, TokenUsage
    from ..schemas.perspective import (
        PerspectiveType,
        PerspectiveAnalysis,
        FindingPerspectives as FindingPerspectivesSchema,
        FindingHistoricalAnalysis,
        FindingFinancialAnalysis,
        FindingJournalistAnalysis,
        FindingConspiratorAnalysis,
        FindingNetworkAnalysis,
        finding_perspective_from_dict,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from inference_client import InferenceClient, TokenUsage
    from schemas.perspective import (
        PerspectiveType,
        PerspectiveAnalysis,
        FindingPerspectives as FindingPerspectivesSchema,
        FindingHistoricalAnalysis,
        FindingFinancialAnalysis,
        FindingJournalistAnalysis,
        FindingConspiratorAnalysis,
        FindingNetworkAnalysis,
        finding_perspective_from_dict,
    )


# Registry of all available agents
AGENT_REGISTRY: Dict[PerspectiveType, Type[BasePerspectiveAgent]] = {
    PerspectiveType.HISTORICAL: HistoricalAgent,
    PerspectiveType.FINANCIAL: FinancialAgent,
    PerspectiveType.JOURNALIST: JournalistAgent,
    PerspectiveType.CONSPIRATOR: ConspiratorAgent,
    PerspectiveType.NETWORK: NetworkAgent,
}


@dataclass
class FindingPerspectives:
    """Perspective analyses for a single finding."""

    finding_content: str
    finding_type: str
    perspectives: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TopicPerspectives:
    """Complete perspective analyses for a topic."""

    topic: str
    analyses: Dict[PerspectiveType, PerspectiveAnalysis] = field(default_factory=dict)

    # Token usage tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


@dataclass
class PerspectiveRunResult:
    """Result of running perspectives."""

    topic_perspectives: TopicPerspectives
    finding_perspectives: List[FindingPerspectives] = field(default_factory=list)

    # Execution metadata
    perspectives_run: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class PerspectiveRunner:
    """Runs perspective agents on research findings."""

    def __init__(
        self,
        client: Optional[InferenceClient] = None,
        perspectives: Optional[List[PerspectiveType]] = None,
    ):
        """Initialize the runner.

        Args:
            client: Inference client to use (shared across agents)
            perspectives: Which perspectives to run (default: all)
        """
        self.client = client or InferenceClient()

        # Default to all perspectives
        self.perspectives = perspectives or list(PerspectiveType)

        # Initialize agents
        self.agents: Dict[PerspectiveType, BasePerspectiveAgent] = {}
        for ptype in self.perspectives:
            if ptype in AGENT_REGISTRY:
                self.agents[ptype] = AGENT_REGISTRY[ptype](self.client)

    async def run_topic_analysis(
        self,
        context: PerspectiveContext,
        parallel: bool = True,
    ) -> TopicPerspectives:
        """Run all perspective agents on the topic.

        Args:
            context: Research context with topic and findings
            parallel: Run agents in parallel (faster but more API calls at once)

        Returns:
            TopicPerspectives with all analyses
        """
        result = TopicPerspectives(topic=context.topic)

        if parallel:
            # Run all agents in parallel
            tasks = [
                agent.analyze_topic(context)
                for agent in self.agents.values()
            ]
            analyses = await asyncio.gather(*tasks, return_exceptions=True)

            for ptype, analysis in zip(self.agents.keys(), analyses):
                if isinstance(analysis, Exception):
                    print(f"Error in {ptype.value} analysis: {analysis}")
                else:
                    result.analyses[ptype] = analysis
        else:
            # Run agents sequentially
            for ptype, agent in self.agents.items():
                try:
                    analysis = await agent.analyze_topic(context)
                    result.analyses[ptype] = analysis
                except Exception as e:
                    print(f"Error in {ptype.value} analysis: {e}")

        return result

    async def run_finding_analysis(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
        parallel: bool = True,
    ) -> FindingPerspectives:
        """Run all perspective agents on a single finding.

        Args:
            finding_content: The finding text
            finding_type: Type of finding
            context: Research context
            parallel: Run agents in parallel

        Returns:
            FindingPerspectives with all analyses
        """
        result = FindingPerspectives(
            finding_content=finding_content,
            finding_type=finding_type,
        )

        # Update context with current finding
        context.current_finding = finding_content
        context.current_finding_type = finding_type

        if parallel:
            tasks = [
                agent.analyze_finding(finding_content, finding_type, context)
                for agent in self.agents.values()
            ]
            analyses = await asyncio.gather(*tasks, return_exceptions=True)

            for ptype, analysis in zip(self.agents.keys(), analyses):
                if isinstance(analysis, Exception):
                    print(f"Error in {ptype.value} finding analysis: {analysis}")
                else:
                    result.perspectives[ptype.value] = analysis
        else:
            for ptype, agent in self.agents.items():
                try:
                    analysis = await agent.analyze_finding(
                        finding_content, finding_type, context
                    )
                    result.perspectives[ptype.value] = analysis
                except Exception as e:
                    print(f"Error in {ptype.value} finding analysis: {e}")

        return result

    async def run_all_findings_analysis(
        self,
        findings: List[Dict[str, str]],
        context: PerspectiveContext,
        max_findings: int = 30,
        batch_size: int = 5,
        parallel: bool = True,
    ) -> List[FindingPerspectivesSchema]:
        """Analyze all findings with all perspectives in batches.

        Args:
            findings: List of findings with 'id', 'content', 'type', 'summary' keys
            context: Research context
            max_findings: Maximum number of findings to analyze
            batch_size: Number of findings to process in each batch
            parallel: Run agents in parallel within each finding

        Returns:
            List of FindingPerspectivesSchema with typed perspective analyses
        """
        results: List[FindingPerspectivesSchema] = []
        findings_to_process = findings[:max_findings]

        print(f"  Analyzing {len(findings_to_process)} findings in batches of {batch_size}")

        # Process in batches to avoid overwhelming the API
        for batch_start in range(0, len(findings_to_process), batch_size):
            batch = findings_to_process[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(findings_to_process) + batch_size - 1) // batch_size
            print(f"    Batch {batch_num}/{total_batches}: {len(batch)} findings")

            # Process batch in parallel
            tasks = [
                self._analyze_single_finding_typed(finding, context, parallel)
                for finding in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for finding, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    print(f"      Error analyzing finding: {result}")
                    # Create empty container for failed finding
                    results.append(FindingPerspectivesSchema(
                        finding_id=finding.get("id", "unknown"),
                        finding_content=finding.get("content", ""),
                        finding_summary=finding.get("summary"),
                    ))
                else:
                    results.append(result)

        return results

    async def _analyze_single_finding_typed(
        self,
        finding: Dict[str, str],
        context: PerspectiveContext,
        parallel: bool = True,
    ) -> FindingPerspectivesSchema:
        """Analyze a single finding and return typed perspective analyses."""
        finding_id = finding.get("id", "f0")
        finding_content = finding.get("content", "")
        finding_type = finding.get("type", "unknown")
        finding_summary = finding.get("summary")

        # Create result container
        result = FindingPerspectivesSchema(
            finding_id=finding_id,
            finding_content=finding_content,
            finding_summary=finding_summary,
        )

        # Update context with current finding
        context.current_finding = finding_content
        context.current_finding_type = finding_type

        # Run all perspective agents
        if parallel:
            tasks = [
                agent.analyze_finding(finding_content, finding_type, context)
                for agent in self.agents.values()
            ]
            analyses = await asyncio.gather(*tasks, return_exceptions=True)

            for ptype, analysis in zip(self.agents.keys(), analyses):
                if isinstance(analysis, Exception):
                    continue

                # Convert to typed finding-level analysis
                typed_analysis = finding_perspective_from_dict(
                    ptype.value,
                    analysis if isinstance(analysis, dict) else {},
                    finding_id,
                )

                # Assign to appropriate field
                if ptype == PerspectiveType.HISTORICAL:
                    result.historical = typed_analysis
                elif ptype == PerspectiveType.FINANCIAL:
                    result.financial = typed_analysis
                elif ptype == PerspectiveType.JOURNALIST:
                    result.journalist = typed_analysis
                elif ptype == PerspectiveType.CONSPIRATOR:
                    result.conspirator = typed_analysis
                elif ptype == PerspectiveType.NETWORK:
                    result.network = typed_analysis
        else:
            for ptype, agent in self.agents.items():
                try:
                    analysis = await agent.analyze_finding(
                        finding_content, finding_type, context
                    )
                    typed_analysis = finding_perspective_from_dict(
                        ptype.value,
                        analysis if isinstance(analysis, dict) else {},
                        finding_id,
                    )

                    if ptype == PerspectiveType.HISTORICAL:
                        result.historical = typed_analysis
                    elif ptype == PerspectiveType.FINANCIAL:
                        result.financial = typed_analysis
                    elif ptype == PerspectiveType.JOURNALIST:
                        result.journalist = typed_analysis
                    elif ptype == PerspectiveType.CONSPIRATOR:
                        result.conspirator = typed_analysis
                    elif ptype == PerspectiveType.NETWORK:
                        result.network = typed_analysis
                except Exception:
                    pass

        return result

    async def run_all(
        self,
        context: PerspectiveContext,
        findings: List[Dict[str, str]],
        analyze_findings: bool = True,
        max_findings: int = 30,
        parallel: bool = True,
    ) -> PerspectiveRunResult:
        """Run complete perspective analysis on topic and findings.

        Args:
            context: Research context
            findings: List of findings with 'content' and 'type' keys
            analyze_findings: Whether to analyze individual findings
            max_findings: Maximum number of findings to analyze
            parallel: Run agents in parallel

        Returns:
            PerspectiveRunResult with all analyses
        """
        result = PerspectiveRunResult(
            topic_perspectives=TopicPerspectives(topic=context.topic),
            perspectives_run=[p.value for p in self.perspectives],
        )

        try:
            # Run topic-level analysis
            result.topic_perspectives = await self.run_topic_analysis(
                context, parallel=parallel
            )

            # Optionally run finding-level analysis
            if analyze_findings and findings:
                for finding in findings[:max_findings]:
                    try:
                        fp = await self.run_finding_analysis(
                            finding.get("content", ""),
                            finding.get("type", "unknown"),
                            context,
                            parallel=parallel,
                        )
                        result.finding_perspectives.append(fp)
                    except Exception as e:
                        result.errors.append(f"Finding analysis error: {e}")

        except Exception as e:
            result.errors.append(f"Topic analysis error: {e}")

        return result


async def run_perspectives(
    topic: str,
    topic_summary: str,
    finding_summaries: List[str],
    actors: List[str] = None,
    events: List[str] = None,
    perspectives: List[PerspectiveType] = None,
    client: Optional[InferenceClient] = None,
) -> TopicPerspectives:
    """Convenience function to run perspective analysis.

    Args:
        topic: Research topic/query
        topic_summary: Summary of findings
        finding_summaries: List of finding summary strings
        actors: Key actors identified
        events: Key events identified
        perspectives: Which perspectives to run
        client: Inference client

    Returns:
        TopicPerspectives with all analyses
    """
    context = PerspectiveContext(
        topic=topic,
        topic_summary=topic_summary,
        finding_summaries=finding_summaries,
        actors=actors or [],
        events=events or [],
    )

    runner = PerspectiveRunner(client=client, perspectives=perspectives)
    return await runner.run_topic_analysis(context)
