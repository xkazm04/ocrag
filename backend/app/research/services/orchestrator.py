"""Research orchestrator - coordinates the entire research process."""

import time
from typing import AsyncGenerator, Optional, List
from uuid import UUID

from app.config import get_settings
from ..schemas import (
    ResearchRequest,
    ResearchSession,
    ResearchProgress,
    ResearchParameters,
    Finding,
    Source,
)
from ..templates import get_template
from ..db import SupabaseResearchDB
from .web_search import WebSearchService, get_web_search_service
from .credibility import CredibilityAssessor
from .analysis import MultiPerspectiveAnalyzer


class ResearchOrchestrator:
    """
    Orchestrates multi-step research investigations.

    Research Flow:
    1. Check cache for existing research
    2. Generate initial search queries from template
    3. Execute web searches with Gemini grounding
    4. Assess source credibility
    5. Extract findings
    6. Run multi-perspective analysis
    7. Cache results
    """

    def __init__(
        self,
        db: SupabaseResearchDB,
        workspace_id: str = "default",
    ):
        self.db = db
        self.workspace_id = workspace_id
        self.web_search = get_web_search_service()
        self.analyzer = MultiPerspectiveAnalyzer()
        self.credibility = CredibilityAssessor()
        self.settings = get_settings()

    async def start_research(
        self,
        request: ResearchRequest,
        use_cache: bool = True,
    ) -> AsyncGenerator[ResearchProgress, None]:
        """
        Start a new research session with streaming progress.

        Yields:
            ResearchProgress updates as research proceeds
        """
        start_time = time.time()

        # Check cache first
        if use_cache and request.parameters.use_cache:
            cached = await self.db.get_cached_session(
                request.query,
                request.template_type,
            )
            if cached:
                yield ResearchProgress(
                    status="completed",
                    message="Retrieved from cache",
                    session_id=cached.id,
                    is_cached=True,
                    progress=100.0,
                )
                return

        # Create new session
        session = await self.db.create_session(
            title=request.title or f"Research: {request.query[:50]}...",
            query=request.query,
            template_type=request.template_type,
            parameters=request.parameters.model_dump(),
            workspace_id=request.workspace_id or self.workspace_id,
        )

        yield ResearchProgress(
            status="started",
            message="Research session created",
            session_id=session.id,
            phase=0,
            total_phases=4,
            progress=5.0,
        )

        try:
            # Get template
            template = get_template(request.template_type)

            # Phase 1: Generate and execute searches
            yield ResearchProgress(
                status="searching",
                message="Generating search queries...",
                session_id=session.id,
                phase=1,
                total_phases=4,
                progress=10.0,
            )

            search_queries = await template.generate_search_queries(
                request.query,
                request.parameters,
            )

            all_sources: List[Source] = []
            all_synthesized_content: List[str] = []

            for i, query_text in enumerate(search_queries):
                yield ResearchProgress(
                    status="searching",
                    message=f"Executing search {i + 1}/{len(search_queries)}: {query_text[:50]}...",
                    session_id=session.id,
                    phase=1,
                    total_phases=4,
                    progress=10.0 + (i / len(search_queries)) * 20.0,
                )

                # Execute search
                search_start = time.time()
                result = await self.web_search.search_with_grounding(
                    query_text,
                    purpose=f"Research query {i + 1}",
                )
                search_time_ms = int((time.time() - search_start) * 1000)

                # Save query
                await self.db.save_query(
                    session_id=session.id,
                    query_text=query_text,
                    query_purpose=f"Search query {i + 1}",
                    query_round=1,
                    execution_time_ms=search_time_ms,
                    result_count=len(result.sources),
                    grounding_metadata={
                        "search_queries": result.search_queries,
                        "chunks_count": len(result.grounding_metadata.grounding_chunks) if result.grounding_metadata else 0,
                    },
                )

                all_sources.extend(result.sources)
                all_synthesized_content.append(result.synthesized_content)

            # Update session status
            await self.db.update_session_status(session.id, "analyzing")

            # Phase 2: Assess credibility
            yield ResearchProgress(
                status="assessing",
                message=f"Assessing credibility of {len(all_sources)} sources...",
                session_id=session.id,
                phase=2,
                total_phases=4,
                progress=35.0,
            )

            assessed_sources = await self.credibility.assess_batch(all_sources)

            # Deduplicate by URL
            seen_urls = set()
            unique_sources = []
            for source in assessed_sources:
                if source.url not in seen_urls:
                    seen_urls.add(source.url)
                    unique_sources.append(source)

            # Save sources
            saved_sources = await self.db.save_sources(session.id, unique_sources)

            yield ResearchProgress(
                status="assessing",
                message=f"Assessed {len(saved_sources)} unique sources",
                session_id=session.id,
                phase=2,
                total_phases=4,
                progress=45.0,
            )

            # Phase 3: Extract findings
            yield ResearchProgress(
                status="extracting",
                message="Extracting findings from research...",
                session_id=session.id,
                phase=3,
                total_phases=4,
                progress=50.0,
            )

            combined_content = "\n\n---\n\n".join(all_synthesized_content)
            findings = await template.extract_findings(
                request.query,
                saved_sources,
                combined_content,
                request.parameters,
            )

            saved_findings = await self.db.save_findings(session.id, findings)

            yield ResearchProgress(
                status="extracting",
                message=f"Extracted {len(saved_findings)} findings",
                session_id=session.id,
                phase=3,
                total_phases=4,
                progress=60.0,
            )

            # Phase 4: Multi-perspective analysis
            perspectives_to_run = request.parameters.perspectives or template.default_perspectives

            for i, perspective in enumerate(perspectives_to_run):
                yield ResearchProgress(
                    status="analyzing",
                    message=f"Analyzing from {perspective} perspective...",
                    session_id=session.id,
                    phase=4,
                    total_phases=4,
                    progress=60.0 + (i / len(perspectives_to_run)) * 35.0,
                )

                analysis = await self.analyzer.analyze(
                    perspective_type=perspective,
                    findings=saved_findings,
                    sources=saved_sources,
                    original_query=request.query,
                )
                await self.db.save_perspective(session.id, analysis)

            # Complete session
            await self.db.complete_session(session.id)

            # Cache results
            await self.db.cache_session(
                request.query,
                request.template_type,
                session.id,
                ttl_hours=self.settings.research_cache_ttl_hours,
            )

            total_time = time.time() - start_time

            yield ResearchProgress(
                status="completed",
                message=f"Research complete in {total_time:.1f}s",
                session_id=session.id,
                phase=4,
                total_phases=4,
                progress=100.0,
            )

        except Exception as e:
            await self.db.update_session_status(session.id, "failed")
            yield ResearchProgress(
                status="failed",
                message=f"Research failed: {str(e)}",
                session_id=session.id,
                progress=0.0,
            )
            raise

    async def continue_research(
        self,
        session_id: UUID,
        additional_queries: List[str],
    ) -> AsyncGenerator[ResearchProgress, None]:
        """
        Continue research with additional queries.

        Args:
            session_id: Existing session to continue
            additional_queries: New queries to execute

        Yields:
            ResearchProgress updates
        """
        session = await self.db.get_session(session_id)
        if not session:
            yield ResearchProgress(
                status="failed",
                message="Session not found",
                session_id=session_id,
            )
            return

        await self.db.update_session_status(session_id, "searching")

        yield ResearchProgress(
            status="searching",
            message=f"Continuing research with {len(additional_queries)} new queries",
            session_id=session_id,
            progress=10.0,
        )

        # Execute additional searches
        all_sources: List[Source] = []
        all_content: List[str] = []

        for i, query_text in enumerate(additional_queries):
            yield ResearchProgress(
                status="searching",
                message=f"Executing query {i + 1}/{len(additional_queries)}",
                session_id=session_id,
                progress=10.0 + (i / len(additional_queries)) * 40.0,
            )

            result = await self.web_search.search_with_grounding(query_text)
            all_sources.extend(result.sources)
            all_content.append(result.synthesized_content)

            await self.db.save_query(
                session_id=session_id,
                query_text=query_text,
                query_purpose="Additional query",
                query_round=2,
                result_count=len(result.sources),
            )

        # Assess and save new sources
        assessed = await self.credibility.assess_batch(all_sources)
        await self.db.save_sources(session_id, assessed)

        # Extract additional findings
        template = get_template(session.template_type)
        params = ResearchParameters(**session.parameters)

        new_findings = await template.extract_findings(
            session.query,
            assessed,
            "\n\n".join(all_content),
            params,
        )
        await self.db.save_findings(session_id, new_findings)

        await self.db.complete_session(session_id)

        yield ResearchProgress(
            status="completed",
            message="Additional research complete",
            session_id=session_id,
            progress=100.0,
        )
