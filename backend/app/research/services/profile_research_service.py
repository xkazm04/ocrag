"""Profile research service for entity enrichment.

Provides LLM-powered research capabilities for:
1. Finding information about profiles (positions, roles, ownership)
2. Finding connections between profiles (business, transactions, mentions)
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4

from ..db import SupabaseResearchDB
from ..lib.clients import GeminiResearchClient, SearchMode

logger = logging.getLogger(__name__)


class ProfileResearchService:
    """Researches entity profiles using LLM with web search."""

    def __init__(self, db: SupabaseResearchDB):
        self.db = db
        self._gemini = None

    async def _get_gemini(self) -> Optional[GeminiResearchClient]:
        """Lazy load Gemini client."""
        if self._gemini is None:
            try:
                self._gemini = GeminiResearchClient(search_mode=SearchMode.GROUNDED)
            except (ImportError, ValueError) as e:
                logger.warning("Could not create GeminiResearchClient: %s", e)
        return self._gemini

    async def research_profile(
        self,
        entity_id: UUID,
        entity_name: str,
        entity_type: str,
        date_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Research information about an entity profile.

        Searches for:
        - Professional positions and roles over time
        - Company ownership and board memberships
        - Business affiliations
        - Key events and timeline

        Args:
            entity_id: The entity's database ID
            entity_name: The entity's canonical name
            entity_type: Type of entity (person, organization, etc.)
            date_context: Optional date range context (e.g., "1990-2010")

        Returns:
            Dict with research results including positions, ownership, affiliations
        """
        gemini = await self._get_gemini()
        if not gemini:
            return {"error": "LLM client not available", "entity_id": str(entity_id)}

        # Build context-aware research query
        date_clause = f" during {date_context}" if date_context else ""

        if entity_type == "person":
            query = f"""Research {entity_name}{date_clause}. Find:
1. Professional positions and roles (with dates if available)
2. Companies owned, founded, or board memberships
3. Business partnerships and affiliations
4. Key events or controversies
5. Known associates and relationships

Focus on verifiable facts with sources. Include dates when available."""
        elif entity_type == "organization":
            query = f"""Research {entity_name}{date_clause}. Find:
1. Key executives and leadership (with dates)
2. Parent companies and subsidiaries
3. Major transactions and acquisitions
4. Business activities and industries
5. Notable events or controversies

Focus on verifiable facts with sources. Include dates when available."""
        else:
            query = f"""Research {entity_name}{date_clause}. Find all relevant information including:
1. Key facts and background
2. Related entities and relationships
3. Notable events and timeline
4. Current status

Focus on verifiable facts with sources."""

        try:
            response = await gemini.grounded_search(query, temperature=0.3)

            # Parse the response into structured data
            structured = await self._parse_profile_response(
                gemini, entity_name, entity_type, response.text
            )

            # Extract sources
            sources = [
                {"url": s.url, "title": s.title, "domain": s.domain}
                for s in response.sources[:10]
            ]

            # Check for companies that might exist in our database
            company_matches = await self._match_companies_to_db(
                structured.get("companies", [])
            )

            return {
                "entity_id": str(entity_id),
                "entity_name": entity_name,
                "research_date": datetime.utcnow().isoformat(),
                "positions": structured.get("positions", []),
                "companies": structured.get("companies", []),
                "company_db_matches": company_matches,
                "affiliations": structured.get("affiliations", []),
                "events": structured.get("events", []),
                "associates": structured.get("associates", []),
                "summary": structured.get("summary", response.text[:500]),
                "sources": sources,
                "raw_text": response.text,
            }

        except Exception as e:
            logger.error("Profile research failed for %s: %s", entity_name, e)
            return {
                "entity_id": str(entity_id),
                "entity_name": entity_name,
                "error": str(e),
            }

    async def _parse_profile_response(
        self,
        gemini: GeminiResearchClient,
        entity_name: str,
        entity_type: str,
        raw_text: str,
    ) -> Dict[str, Any]:
        """Parse raw research text into structured data."""
        prompt = f"""Parse this research about {entity_name} ({entity_type}) into structured JSON:

TEXT:
{raw_text[:8000]}

Return JSON with:
{{
    "summary": "2-3 sentence summary of key findings",
    "positions": [
        {{"title": "...", "organization": "...", "start_date": "YYYY or YYYY-MM-DD", "end_date": "...", "notes": "..."}}
    ],
    "companies": [
        {{"name": "...", "role": "owner/founder/board/executive", "dates": "...", "notes": "..."}}
    ],
    "affiliations": [
        {{"organization": "...", "type": "membership/partnership/affiliation", "dates": "..."}}
    ],
    "events": [
        {{"date": "YYYY-MM-DD or YYYY", "description": "...", "significance": "high/medium/low"}}
    ],
    "associates": [
        {{"name": "...", "relationship": "...", "context": "..."}}
    ]
}}

Only include items that are clearly stated in the text. Use null for missing dates."""

        try:
            parsed, _ = await gemini.generate_json(prompt, temperature=0.2)
            return parsed or {}
        except Exception as e:
            logger.warning("Failed to parse profile response: %s", e)
            return {"summary": raw_text[:500]}

    async def _match_companies_to_db(
        self, companies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check if any researched companies exist in our database."""
        matches = []
        for company in companies:
            name = company.get("name", "")
            if not name:
                continue

            try:
                # Search for company in knowledge_entities
                result = self.db.client.table("knowledge_entities").select(
                    "id, canonical_name, entity_type"
                ).eq("entity_type", "organization").ilike(
                    "canonical_name", f"%{name}%"
                ).limit(3).execute()

                if result.data:
                    matches.append({
                        "researched_name": name,
                        "db_matches": [
                            {
                                "id": r["id"],
                                "name": r["canonical_name"],
                            }
                            for r in result.data
                        ]
                    })
            except Exception:
                pass

        return matches

    async def find_connections(
        self,
        source_entity_id: UUID,
        source_entity_name: str,
        target_entities: List[Dict[str, Any]],
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Find connections between a source entity and target entities.

        Searches for:
        - Business relationships and transactions
        - Ownership and investment connections
        - Personal/professional relationships
        - Shared affiliations or events

        Args:
            source_entity_id: The source entity's database ID
            source_entity_name: The source entity's name
            target_entities: List of target entities to check connections with
                            Each: {"id": UUID, "name": str, "type": str}
            focus_areas: Optional focus areas (e.g., ["financial", "ownership"])

        Returns:
            Dict with connections found for each target entity
        """
        gemini = await self._get_gemini()
        if not gemini:
            return {"error": "LLM client not available"}

        focus_clause = ""
        if focus_areas:
            focus_clause = f" Focus on: {', '.join(focus_areas)}."

        results = {
            "source_entity_id": str(source_entity_id),
            "source_entity_name": source_entity_name,
            "research_date": datetime.utcnow().isoformat(),
            "connections": [],
        }

        for target in target_entities:
            target_id = target.get("id")
            target_name = target.get("name", "")

            # Check if already researched
            if await self._is_pair_researched(source_entity_id, UUID(str(target_id))):
                results["connections"].append({
                    "target_entity_id": str(target_id),
                    "target_entity_name": target_name,
                    "status": "already_researched",
                    "connections": [],
                })
                continue

            query = f"""Find connections between {source_entity_name} and {target_name}.{focus_clause}

Look for:
1. Business relationships (partnerships, transactions, contracts)
2. Ownership or investment connections
3. Personal or professional relationships
4. Shared organizations, boards, or affiliations
5. Meetings, events, or documented interactions
6. Financial flows or transactions

Include dates and sources when available. Focus on verified, documented connections."""

            try:
                response = await gemini.grounded_search(query, temperature=0.3)

                # Parse connections
                parsed = await self._parse_connection_response(
                    gemini, source_entity_name, target_name, response.text
                )

                # Extract sources
                sources = [
                    {"url": s.url, "title": s.title, "domain": s.domain}
                    for s in response.sources[:5]
                ]

                connection_result = {
                    "target_entity_id": str(target_id),
                    "target_entity_name": target_name,
                    "status": "researched",
                    "connections": parsed.get("connections", []),
                    "relationship_strength": parsed.get("strength", "unknown"),
                    "summary": parsed.get("summary", ""),
                    "sources": sources,
                }

                results["connections"].append(connection_result)

                # Mark pair as researched
                await self._mark_pair_researched(
                    source_entity_id,
                    UUID(str(target_id)),
                    connection_result
                )

            except Exception as e:
                logger.error(
                    "Connection research failed for %s -> %s: %s",
                    source_entity_name, target_name, e
                )
                results["connections"].append({
                    "target_entity_id": str(target_id),
                    "target_entity_name": target_name,
                    "status": "error",
                    "error": str(e),
                })

        return results

    async def _parse_connection_response(
        self,
        gemini: GeminiResearchClient,
        source_name: str,
        target_name: str,
        raw_text: str,
    ) -> Dict[str, Any]:
        """Parse raw connection research into structured data."""
        prompt = f"""Parse this research about connections between {source_name} and {target_name} into structured JSON:

TEXT:
{raw_text[:6000]}

Return JSON with:
{{
    "summary": "1-2 sentence summary of the relationship",
    "strength": "strong/moderate/weak/none",
    "connections": [
        {{
            "type": "business/financial/personal/organizational/event",
            "description": "...",
            "date": "YYYY-MM-DD or YYYY or null",
            "evidence_strength": "high/medium/low",
            "details": "..."
        }}
    ]
}}

If no connections found, return {{"summary": "No documented connections found", "strength": "none", "connections": []}}"""

        try:
            parsed, _ = await gemini.generate_json(prompt, temperature=0.2)
            return parsed or {"connections": [], "strength": "unknown"}
        except Exception as e:
            logger.warning("Failed to parse connection response: %s", e)
            return {"connections": [], "strength": "unknown", "summary": raw_text[:300]}

    async def _is_pair_researched(
        self, entity_a: UUID, entity_b: UUID
    ) -> bool:
        """Check if a pair of entities has already been researched."""
        try:
            # Normalize order for consistent lookups
            id_a, id_b = sorted([str(entity_a), str(entity_b)])

            result = self.db.client.table("entity_research_pairs").select(
                "id"
            ).eq("entity_a_id", id_a).eq("entity_b_id", id_b).limit(1).execute()

            return len(result.data) > 0
        except Exception:
            # Table might not exist yet
            return False

    async def _mark_pair_researched(
        self,
        entity_a: UUID,
        entity_b: UUID,
        research_result: Dict[str, Any],
    ) -> None:
        """Mark a pair of entities as researched."""
        try:
            # Normalize order for consistent storage
            id_a, id_b = sorted([str(entity_a), str(entity_b)])

            self.db.client.table("entity_research_pairs").upsert({
                "entity_a_id": id_a,
                "entity_b_id": id_b,
                "research_date": datetime.utcnow().isoformat(),
                "connection_strength": research_result.get("relationship_strength", "unknown"),
                "connections_count": len(research_result.get("connections", [])),
                "summary": research_result.get("summary", "")[:500],
            }).execute()
        except Exception as e:
            logger.warning("Failed to mark pair as researched: %s", e)

    async def get_research_stats(
        self, entity_id: UUID
    ) -> Dict[str, Any]:
        """Get research statistics for an entity."""
        try:
            # Count how many pairs this entity has been researched with
            result = self.db.client.table("entity_research_pairs").select(
                "id", count="exact"
            ).or_(
                f"entity_a_id.eq.{entity_id},entity_b_id.eq.{entity_id}"
            ).execute()

            return {
                "entity_id": str(entity_id),
                "pairs_researched": result.count or 0,
            }
        except Exception:
            return {"entity_id": str(entity_id), "pairs_researched": 0}

    async def get_unresearched_pairs(
        self,
        entity_id: UUID,
        target_entity_ids: List[UUID],
    ) -> List[UUID]:
        """Get list of target entities that haven't been researched yet."""
        unresearched = []

        for target_id in target_entity_ids:
            if not await self._is_pair_researched(entity_id, target_id):
                unresearched.append(target_id)

        return unresearched
