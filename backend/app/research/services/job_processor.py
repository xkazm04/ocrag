"""Async job processor for research tasks.

Orchestrates the complete research pipeline:
1. Topic matching
2. Time scope analysis (dynamic)
3. Query decomposition
4. Web search & finding extraction
5. Perspective analysis
6. Relationship building
7. Deduplication
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from ..db import get_supabase_db, SupabaseResearchDB
from ..db.jobs import JobOperations
from ..schemas import Finding, Source, Perspective
from ..schemas.jobs import (
    JobStatus,
    JobStage,
    TopicMatchResult,
    DedupStats,
    STAGE_PROGRESS,
)
from ..lib.clients import InferenceClient, get_inference_client
from .topic_matcher import TopicMatcher
from .deduplicator import FindingDeduplicator
from .time_scope_analyzer import TimeScopeAnalyzer, TimeScopeDecision

logger = logging.getLogger(__name__)


async def process_research_job(job_id: UUID, workspace_id: str = "default") -> None:
    """
    Main entry point for background job processing.

    Args:
        job_id: The job ID to process
        workspace_id: Workspace ID for database operations
    """
    processor = JobProcessor(workspace_id)
    await processor.process(job_id)


class JobProcessor:
    """Processes async research jobs through the full pipeline."""

    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.db = get_supabase_db(workspace_id)
        self.jobs = JobOperations(self.db.client, workspace_id)

    async def process(self, job_id: UUID) -> None:
        """
        Process a research job through all stages.

        Stages:
        - health_check (5%): Verify API availability
        - topic_matching (10%): Match query to existing topics
        - decomposition (20%): Analyze and decompose query
        - searching (35%): Execute web searches
        - extraction (50%): Extract findings from results
        - perspectives (70%): Run perspective analysis
        - relationships (85%): Build relationship graph
        - deduplication (95%): Compare and deduplicate findings
        - completed (100%): Save stats and complete
        """
        job = await self.jobs.get_job(job_id)
        if not job:
            return

        start_time = datetime.utcnow()

        try:
            # Mark job as running
            await self.jobs.update_job_status(
                job_id,
                JobStatus.RUNNING,
                JobStage.HEALTH_CHECK.value,
                STAGE_PROGRESS[JobStage.HEALTH_CHECK],
            )

            # Stage 1: Topic Matching
            await self.jobs.update_job_progress(job_id, JobStage.TOPIC_MATCHING)

            # Initialize inference client for LLM calls
            inference_client = await self._get_inference_client()
            topic_matcher = TopicMatcher(self.db, inference_client)

            topic_result = await topic_matcher.match_topic(job.query, self.workspace_id)

            # Save topic match result
            await self.jobs.set_topic_match(
                job_id,
                topic_result.topic_id,
                topic_result.confidence,
                topic_result.reasoning,
            )

            # Get existing context if topic matched
            existing_context = None
            context_prompt = ""
            if topic_result.topic_id and topic_result.confidence >= 0.7:
                existing_context = await topic_matcher.get_topic_context(topic_result.topic_id)
                context_prompt = topic_matcher.build_context_prompt(existing_context)

            # Stage 1.5: Dynamic Time Scope Analysis
            time_scope_analyzer = TimeScopeAnalyzer(inference_client)
            time_scope = await time_scope_analyzer.analyze(job.query)

            # Build time scope context for decomposition
            time_scope_context = self._build_time_scope_context(time_scope)

            # Stage 2-5: Run enhanced research harness
            await self.jobs.update_job_progress(job_id, JobStage.DECOMPOSITION)

            result = await self._run_research_pipeline(
                job_id=job_id,
                query=job.query,
                template_type=job.template_type,
                parameters=job.parameters,
                context_prompt=context_prompt,
                time_scope=time_scope,
                time_scope_context=time_scope_context,
            )

            if not result:
                await self.jobs.fail_job(job_id, "Research pipeline returned no results")
                return

            # Create research session and save data
            session = await self.db.create_session(
                title=f"Research: {job.query[:50]}...",
                query=job.query,
                template_type=job.template_type,
                parameters=job.parameters,
                workspace_id=self.workspace_id,
            )

            # Convert and save findings
            saved_findings = await self._save_findings(session.id, result.findings)

            # Save sources
            await self._save_sources(session.id, result.sources)

            # Save perspectives
            await self._save_perspectives(session.id, result.perspectives)

            # Stage 6: Deduplication
            await self.jobs.update_job_progress(job_id, JobStage.DEDUPLICATION)

            deduplicator = FindingDeduplicator(self.db, inference_client)
            decisions = await deduplicator.deduplicate_findings(
                saved_findings,
                topic_result.topic_id if topic_result.confidence >= 0.7 else None,
                session.id,
            )

            dedup_stats = await deduplicator.execute_decisions(
                decisions,
                saved_findings,
                session.id,
            )

            # Generate key summary
            key_summary = await self._generate_summary(
                job.query,
                result.findings[:5],
                inference_client,
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Build completion stats
            stats = {
                "findings_count": len(saved_findings),
                "perspectives_count": len(result.perspectives),
                "sources_count": len(result.sources),
                "key_summary": key_summary,
                "token_usage": {
                    "total": result.token_stats.total_tokens if hasattr(result, 'token_stats') else 0,
                    "search": getattr(result, 'tokens_search', 0),
                    "extraction": getattr(result, 'tokens_extraction', 0),
                    "perspectives": getattr(result, 'tokens_perspectives', 0),
                },
                "cost_usd": getattr(result, 'total_cost_usd', 0.0),
                "duration_seconds": duration,
                "topic_id": str(topic_result.topic_id) if topic_result.topic_id else None,
                "topic_name": existing_context.topic_name if existing_context else None,
                "dedup_stats": {
                    "new": dedup_stats.new,
                    "updated": dedup_stats.updated,
                    "discarded": dedup_stats.discarded,
                },
                "time_scope": {
                    "type": time_scope.scope_type.value,
                    "start_year": time_scope.start_year,
                    "end_year": time_scope.end_year,
                    "reasoning": time_scope.reasoning,
                } if time_scope else None,
            }

            # Complete the job
            await self.jobs.complete_job(job_id, session.id, stats)

        except Exception as e:
            import traceback
            await self.jobs.fail_job(
                job_id,
                str(e),
                {"traceback": traceback.format_exc()}
            )

    async def _get_inference_client(self):
        """Get or create inference client for LLM calls."""
        try:
            return InferenceClient()
        except (ImportError, ValueError) as e:
            logger.warning("Could not create InferenceClient: %s, using fallback", e)
            return SimpleInferenceClient()

    def _build_time_scope_context(self, time_scope: TimeScopeDecision) -> str:
        """Build context string from time scope analysis for LLM prompts."""
        if not time_scope:
            return ""

        parts = [f"Time Scope Analysis: {time_scope.scope_type.value}"]

        if time_scope.start_year and time_scope.end_year:
            parts.append(f"Date Range: {time_scope.start_year} to {time_scope.end_year}")
        elif time_scope.start_year:
            parts.append(f"From: {time_scope.start_year}")

        if time_scope.reasoning:
            parts.append(f"Reasoning: {time_scope.reasoning}")

        if time_scope.focus_on_recent:
            parts.append("Focus: Recent developments prioritized")

        if time_scope.include_historical_context:
            parts.append("Include: Historical background context")

        if time_scope.needs_temporal_split and time_scope.suggested_periods:
            periods_str = ", ".join([f"{p[0]}-{p[1]}" for p in time_scope.suggested_periods])
            parts.append(f"Suggested periods for decomposition: {periods_str}")

        return "\n".join(parts)

    async def _run_research_pipeline(
        self,
        job_id: UUID,
        query: str,
        template_type: str,
        parameters: Dict[str, Any],
        context_prompt: str = "",
        time_scope: Optional[TimeScopeDecision] = None,
        time_scope_context: str = "",
    ):
        """Run the enhanced research harness."""
        try:
            # EnhancedResearchHarness is still in tests (complex orchestration)
            from pathlib import Path
            import sys
            _tests_path = Path(__file__).parent.parent.parent.parent / "tests" / "research"
            if str(_tests_path) not in sys.path:
                sys.path.insert(0, str(_tests_path))
            from enhanced_harness import EnhancedResearchHarness

            # Use proper lib clients
            from ..lib.clients import GeminiResearchClient

            # Initialize clients
            gemini_client = GeminiResearchClient()
            inference_client = InferenceClient()

            # Create harness
            harness = EnhancedResearchHarness(
                gemini_client=gemini_client,
                inference_client=inference_client,
            )

            # Progress callback to update job status
            async def on_stage_change(stage: str, progress: float):
                stage_map = {
                    "decomposition": JobStage.DECOMPOSITION,
                    "searching": JobStage.SEARCHING,
                    "extraction": JobStage.EXTRACTION,
                    "perspectives": JobStage.PERSPECTIVES,
                    "relationships": JobStage.RELATIONSHIPS,
                }
                if stage in stage_map:
                    await self.jobs.update_job_progress(job_id, stage_map[stage], progress)

            # Update progress as stages complete
            await self.jobs.update_job_progress(job_id, JobStage.SEARCHING)

            # Enhance query with time scope if specific enough
            enhanced_query = query
            if time_scope and time_scope.start_year and time_scope.end_year:
                year_span = time_scope.end_year - time_scope.start_year
                # Only add time constraint to query if scope is narrow
                if year_span <= 3 and time_scope.scope_type.value in ("current", "specific"):
                    if str(time_scope.end_year) not in query and str(time_scope.start_year) not in query:
                        enhanced_query = f"{query} ({time_scope.start_year}-{time_scope.end_year})"

            # Run the research
            result = await harness.run_enhanced_test(
                query=enhanced_query,
                template_type=template_type,
                max_searches=parameters.get("max_searches", 5),
                granularity=parameters.get("granularity", "standard"),
                run_decomposition=True,
                execute_sub_queries=True,
                run_perspectives=True,
                run_finding_perspectives=False,  # Skip for performance
                run_relationships=True,
            )

            # Update to extraction/perspectives stages
            await self.jobs.update_job_progress(job_id, JobStage.EXTRACTION)
            await asyncio.sleep(0.1)  # Brief pause for status update
            await self.jobs.update_job_progress(job_id, JobStage.PERSPECTIVES)
            await asyncio.sleep(0.1)
            await self.jobs.update_job_progress(job_id, JobStage.RELATIONSHIPS)

            return result

        except ImportError as e:
            raise Exception(f"Failed to import research harness: {e}")
        except Exception as e:
            raise Exception(f"Research pipeline failed: {e}")

    async def _save_findings(self, session_id: UUID, findings) -> List[Finding]:
        """Convert and save findings to database."""
        saved = []
        for f in findings:
            finding_data = {
                "finding_type": getattr(f, 'finding_type', 'fact'),
                "content": getattr(f, 'content', str(f)),
                "summary": getattr(f, 'summary', None),
                "temporal_context": getattr(f, 'temporal_context', None),
                "confidence_score": 0.7,
            }
            try:
                finding = Finding(**finding_data)
                saved.append(finding)
            except Exception:
                logger.error("Failed to convert finding to model")

        if saved:
            try:
                return await self.db.save_findings(session_id, saved)
            except Exception:
                logger.warning("Failed to save findings to database")
                return saved

        return saved

    async def _save_sources(self, session_id: UUID, sources) -> None:
        """Convert and save sources to database."""
        source_list = []
        for s in sources:
            source_data = {
                "url": getattr(s, 'url', ''),
                "title": getattr(s, 'title', ''),
                "domain": getattr(s, 'domain', ''),
                "snippet": getattr(s, 'snippet', ''),
                "source_type": getattr(s, 'source_type', 'web'),
            }
            try:
                source = Source(**source_data)
                source_list.append(source)
            except Exception:
                logger.warning("Failed to convert source to model")

        if source_list:
            try:
                await self.db.save_sources(session_id, source_list)
            except Exception:
                logger.warning("Failed to save sources to database")

    async def _save_perspectives(self, session_id: UUID, perspectives) -> None:
        """Save perspective analyses to database."""
        for p in perspectives:
            try:
                perspective = Perspective(
                    perspective_type=getattr(p, 'perspective_type', 'unknown'),
                    analysis_text=getattr(p, 'analysis_text', ''),
                    key_insights=getattr(p, 'key_insights', []),
                    recommendations=getattr(p, 'recommendations', []),
                    warnings=getattr(p, 'warnings', []),
                )
                await self.db.save_perspective(session_id, perspective)
            except Exception:
                logger.warning("Failed to save perspective to database")

    async def _generate_summary(
        self,
        query: str,
        findings,
        client,
    ) -> str:
        """Generate a key summary of findings."""
        findings_text = "\n".join([
            f"- {getattr(f, 'summary', None) or getattr(f, 'content', str(f))[:150]}"
            for f in findings[:5]
        ])

        prompt = f"""Summarize the key findings from this research in 2-3 sentences.

Query: {query}

Findings:
{findings_text}

Provide a concise summary focusing on the most important discoveries. Be factual and specific."""

        try:
            response = await client.generate(prompt, temperature=0.3, max_tokens=200)
            return response.text if hasattr(response, 'text') else str(response)
        except Exception:
            logger.info("Summary generation failed, using default message")
            return "Research completed. See findings for details."


class SimpleInferenceClient:
    """Fallback inference client using direct Gemini calls."""

    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000):
        """Generate text response."""
        try:
            from google import genai
            client = genai.Client()
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            return type('Response', (), {'text': response.text})()
        except Exception as e:
            return type('Response', (), {'text': f"Error: {e}"})()

    async def generate_json(self, prompt: str, system_prompt: str = "", temperature: float = 0.3):
        """Generate JSON response."""
        import json
        try:
            from google import genai
            client = genai.Client()

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=full_prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": 2000,
                },
            )

            # Parse JSON from response
            text = response.text
            # Try to extract JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip()), None
        except Exception as e:
            return None, str(e)
