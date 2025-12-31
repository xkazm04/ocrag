"""Financial Research Service for financial forensics.

Uses LLM-guided source discovery to find and cite appropriate financial records
based on jurisdiction (SEC for US, Companies House for UK, etc.).

Key Design: No hardcoded external API clients. Instead, specialized prompts
instruct the LLM to identify and search appropriate sources based on entity
jurisdiction and type. This enables international investigations.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Set
from uuid import UUID, uuid4

from ..db import SupabaseResearchDB
from ..lib.clients import GeminiResearchClient, SearchMode
from ..schemas.financial import (
    FinancialEntityType,
    TransactionType,
    EvidenceStrength,
    ShellIndicatorType,
    FinancialEntity,
    FinancialTransaction,
    TransactionChain,
    CorporateStructure,
    CorporateRelationship,
    BeneficialOwner,
    PropertyRecord,
    ShellCompanyIndicator,
    ShellCompanyAnalysis,
    TraceMoneyRequest,
    TraceMoneyResponse,
    CorporateStructureRequest,
    CorporateStructureResponse,
    PropertySearchRequest,
    PropertySearchResponse,
)

logger = logging.getLogger(__name__)


class FinancialResearchService:
    """
    Specialized financial forensics research service.
    Uses LLM-guided source discovery for international financial investigations.

    Key Features:
    - Transaction chain tracing (follow the money)
    - Corporate structure analysis
    - Shell company detection
    - Property record research
    - Beneficial ownership identification
    """

    # LLM-guided source discovery prompt
    FINANCIAL_SOURCE_PROMPT = """You are researching financial information for: {entity_name}

Based on the entity's jurisdiction and type, search for financial records from appropriate sources:

**US Entities:**
- SEC EDGAR filings (10-K, 10-Q, DEF 14A, Form 4, 13F)
- State corporate registries (Delaware Division of Corporations, etc.)
- PACER/federal court records for settlements and judgments
- County property records for real estate

**UK Entities:**
- Companies House filings
- UK Land Registry

**France/EU:**
- RCS (Registre du Commerce et des Sociétés)
- BODACC (Official Gazette)

**Offshore Jurisdictions (BVI, Cayman, Panama, USVI, etc.):**
- Limited public records available
- Search leaked documents (Panama Papers, Paradise Papers)
- Court filings that reveal offshore structures
- Investigative journalism

For each finding, specify:
1. Source type (official filing, court document, journalism, leaked document)
2. Evidence strength (high/medium/low/alleged)
3. Direct URL or citation when available

Research query: {query}

Return JSON:
{{
    "findings": [
        {{
            "type": "transaction|ownership|property|corporate_structure|beneficial_owner",
            "description": "detailed finding",
            "amount": null or number,
            "currency": "USD",
            "date": "YYYY-MM-DD or null",
            "source_entity": "name of source/payer",
            "target_entity": "name of target/payee",
            "jurisdiction": "country/state",
            "source_type": "sec_filing|court_document|journalism|leaked_document|corporate_registry",
            "evidence_strength": "high|medium|low|alleged",
            "source_url": "url or citation",
            "notes": "additional context"
        }}
    ],
    "entities_discovered": [
        {{
            "name": "entity name",
            "type": "corporation|llc|trust|foundation|shell_company",
            "jurisdiction": "country/state",
            "relationship_to_target": "subsidiary|owner|director|etc"
        }}
    ],
    "sources_consulted": ["list of source types searched"]
}}"""

    # Shell company detection prompt
    SHELL_COMPANY_PROMPT = """Analyze this entity for shell company indicators:

Entity: {entity_name}
Type: {entity_type}
Jurisdiction: {jurisdiction}
Known Information:
{known_info}

Evaluate these shell company indicators:
1. **Secrecy Jurisdiction**: Registered in known secrecy haven (Delaware, Nevada, BVI, Cayman, Panama)
2. **No Physical Address**: Only registered agent address, no actual office
3. **Registered Agent Only**: Uses corporate service provider
4. **No Employees**: No reported employees or minimal staff
5. **Circular Ownership**: Complex ownership loops
6. **Rapid Ownership Changes**: Frequent changes in ownership/directors
7. **No Public Filings**: Missing expected regulatory filings
8. **Nominee Directors**: Directors are other shell companies or professional nominees

Return JSON:
{{
    "indicators": [
        {{
            "type": "secrecy_jurisdiction|no_physical_address|registered_agent_only|no_employees|circular_ownership|rapid_ownership_changes|no_public_filings|nominee_directors",
            "confidence": 0.0-1.0,
            "details": "specific evidence for this indicator"
        }}
    ],
    "overall_assessment": {{
        "is_likely_shell": true/false,
        "confidence": 0.0-1.0,
        "reasoning": "explanation"
    }}
}}"""

    # Corporate structure prompt
    CORPORATE_STRUCTURE_PROMPT = """Research the corporate structure for: {entity_name}

Find:
1. Parent companies and ultimate beneficial owners
2. Subsidiaries and controlled entities
3. Officers and directors
4. Ownership percentages where available
5. Historical changes in ownership

Search appropriate registries based on jurisdiction:
- US: SEC filings, state registries, PACER
- UK: Companies House
- Offshore: Available records, court documents, journalism

Return JSON:
{{
    "parent_entities": [
        {{
            "name": "parent name",
            "type": "corporation|llc|trust|person",
            "jurisdiction": "country/state",
            "ownership_percentage": null or number,
            "relationship": "owns|controls|beneficial_owner"
        }}
    ],
    "subsidiaries": [
        {{
            "name": "subsidiary name",
            "type": "corporation|llc",
            "jurisdiction": "country/state",
            "ownership_percentage": null or number
        }}
    ],
    "officers": [
        {{
            "name": "person name",
            "role": "CEO|CFO|Director|etc",
            "start_date": "YYYY-MM-DD or null",
            "end_date": "YYYY-MM-DD or null"
        }}
    ],
    "beneficial_owners": [
        {{
            "name": "ultimate owner name",
            "ownership_type": "direct|indirect|beneficial",
            "ownership_percentage": null or number,
            "evidence_strength": "high|medium|low|alleged"
        }}
    ],
    "sources_consulted": ["list of sources"]
}}"""

    def __init__(
        self,
        db: SupabaseResearchDB,
        gemini_client: Optional[GeminiResearchClient] = None,
    ):
        self.db = db
        self._gemini = gemini_client

    async def _get_gemini(self) -> Optional[GeminiResearchClient]:
        """Lazy load Gemini client."""
        if self._gemini is None:
            try:
                self._gemini = GeminiResearchClient(search_mode=SearchMode.GROUNDED)
            except (ImportError, ValueError) as e:
                logger.warning("Could not create GeminiResearchClient: %s", e)
        return self._gemini

    async def trace_money(
        self,
        request: TraceMoneyRequest,
    ) -> TraceMoneyResponse:
        """
        Trace financial transactions forward and/or backward from an entity.
        Uses LLM-guided source discovery based on jurisdiction.
        """
        gemini = await self._get_gemini()
        if not gemini:
            return TraceMoneyResponse(
                entity_name=request.entity_name,
                chains_found=0,
                suspicious_patterns=["LLM client not available"],
            )

        # Build query for financial research
        direction_text = {
            "forward": "Find where money went FROM this entity (outgoing payments, transfers, investments)",
            "backward": "Find where money came FROM to this entity (incoming payments, sources of funds)",
            "both": "Find all financial flows TO and FROM this entity",
        }[request.direction]

        date_filter = ""
        if request.date_start and request.date_end:
            date_filter = f" between {request.date_start} and {request.date_end}"
        elif request.date_start:
            date_filter = f" after {request.date_start}"
        elif request.date_end:
            date_filter = f" before {request.date_end}"

        amount_filter = ""
        if request.amount_filter:
            amount_filter = f" Focus on transactions over ${request.amount_filter:,.0f}."

        query = f"{direction_text}{date_filter}.{amount_filter} Include transaction amounts, dates, purposes, and counterparties."

        prompt = self.FINANCIAL_SOURCE_PROMPT.format(
            entity_name=request.entity_name,
            query=query,
        )

        try:
            # Execute grounded search
            response = await gemini.grounded_search(prompt, temperature=0.3)
            result, _ = await gemini.generate_json(prompt, temperature=0.3)

            # Process findings into transaction chains
            forward_chains = []
            backward_chains = []
            shell_companies = []
            suspicious_patterns = []
            sources_consulted = result.get("sources_consulted", [])

            for finding in result.get("findings", []):
                if finding.get("type") == "transaction":
                    tx = self._finding_to_transaction(finding)

                    # Determine direction
                    if finding.get("source_entity", "").lower() == request.entity_name.lower():
                        # Outgoing
                        forward_chains.append(TransactionChain(
                            transactions=[tx],
                            total_amount=tx.amount,
                            start_entity=request.entity_name,
                            end_entity=finding.get("target_entity", "Unknown"),
                            chain_length=1,
                        ))
                    else:
                        # Incoming
                        backward_chains.append(TransactionChain(
                            transactions=[tx],
                            total_amount=tx.amount,
                            start_entity=finding.get("source_entity", "Unknown"),
                            end_entity=request.entity_name,
                            chain_length=1,
                        ))

                    # Save transaction to database
                    await self._save_transaction(tx, request.workspace_id)

            # Discover and analyze related entities
            for entity_info in result.get("entities_discovered", []):
                fin_entity = FinancialEntity(
                    name=entity_info.get("name", ""),
                    entity_type=FinancialEntityType(entity_info.get("type", "unknown")),
                    jurisdiction=entity_info.get("jurisdiction"),
                )

                # Check for shell company indicators
                if request.include_shell_detection:
                    analysis = await self._analyze_shell_company(fin_entity, request.workspace_id)
                    if analysis.is_likely_shell:
                        shell_companies.append(fin_entity)
                        suspicious_patterns.append(
                            f"Potential shell company: {fin_entity.name} ({fin_entity.jurisdiction})"
                        )

            # Calculate totals
            total_inflow = sum(
                c.total_amount for c in backward_chains if c.total_amount
            ) or Decimal("0")
            total_outflow = sum(
                c.total_amount for c in forward_chains if c.total_amount
            ) or Decimal("0")

            return TraceMoneyResponse(
                entity_name=request.entity_name,
                chains_found=len(forward_chains) + len(backward_chains),
                forward_chains=forward_chains if request.direction in ["forward", "both"] else [],
                backward_chains=backward_chains if request.direction in ["backward", "both"] else [],
                total_inflow=total_inflow,
                total_outflow=total_outflow,
                suspicious_patterns=suspicious_patterns,
                shell_companies_detected=shell_companies,
                sources_consulted=sources_consulted,
            )

        except Exception as e:
            logger.error(f"Money tracing failed: {e}")
            return TraceMoneyResponse(
                entity_name=request.entity_name,
                chains_found=0,
                suspicious_patterns=[f"Research failed: {str(e)}"],
            )

    async def get_corporate_structure(
        self,
        request: CorporateStructureRequest,
    ) -> CorporateStructureResponse:
        """
        Build corporate ownership/control structure using LLM-guided research.
        """
        gemini = await self._get_gemini()
        if not gemini:
            return CorporateStructureResponse(
                root_entity=FinancialEntity(
                    name=request.entity_name,
                    entity_type=FinancialEntityType.UNKNOWN,
                ),
                structure=CorporateStructure(
                    root_entity=FinancialEntity(
                        name=request.entity_name,
                        entity_type=FinancialEntityType.UNKNOWN,
                    ),
                ),
            )

        prompt = self.CORPORATE_STRUCTURE_PROMPT.format(entity_name=request.entity_name)

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.3)

            # Build root entity
            root = FinancialEntity(
                name=request.entity_name,
                entity_type=FinancialEntityType.CORPORATION,
            )

            # Build subsidiaries recursively
            subsidiaries = []
            jurisdictions = set()

            for sub in result.get("subsidiaries", []):
                sub_entity = FinancialEntity(
                    name=sub.get("name", ""),
                    entity_type=FinancialEntityType(sub.get("type", "corporation")),
                    jurisdiction=sub.get("jurisdiction"),
                )
                subsidiaries.append(CorporateStructure(
                    root_entity=sub_entity,
                    ownership_percentage=sub.get("ownership_percentage"),
                    relationship_type="subsidiary",
                ))
                if sub.get("jurisdiction"):
                    jurisdictions.add(sub.get("jurisdiction"))

                # Save to database
                await self._save_financial_entity(sub_entity, request.workspace_id)

            # Build structure
            structure = CorporateStructure(
                root_entity=root,
                subsidiaries=subsidiaries,
            )

            # Extract officers
            officers = result.get("officers", [])

            # Extract beneficial owners
            beneficial_owners = [
                BeneficialOwner(
                    owner_name=bo.get("name", ""),
                    ownership_type=bo.get("ownership_type", "beneficial"),
                    ownership_percentage=bo.get("ownership_percentage"),
                    evidence_strength=EvidenceStrength(bo.get("evidence_strength", "medium")),
                )
                for bo in result.get("beneficial_owners", [])
            ]

            return CorporateStructureResponse(
                root_entity=root,
                structure=structure,
                officers=officers,
                beneficial_owners=beneficial_owners,
                total_subsidiaries=len(subsidiaries),
                jurisdictions=list(jurisdictions),
                sources_consulted=result.get("sources_consulted", []),
            )

        except Exception as e:
            logger.error(f"Corporate structure research failed: {e}")
            return CorporateStructureResponse(
                root_entity=FinancialEntity(
                    name=request.entity_name,
                    entity_type=FinancialEntityType.UNKNOWN,
                ),
                structure=CorporateStructure(
                    root_entity=FinancialEntity(
                        name=request.entity_name,
                        entity_type=FinancialEntityType.UNKNOWN,
                    ),
                ),
            )

    async def find_property_transfers(
        self,
        request: PropertySearchRequest,
    ) -> PropertySearchResponse:
        """
        Find real estate owned/transferred by entity using LLM-guided research.
        """
        gemini = await self._get_gemini()
        if not gemini:
            return PropertySearchResponse(
                entity_name=request.entity_name,
                properties_found=0,
            )

        jurisdiction_filter = ""
        if request.jurisdictions:
            jurisdiction_filter = f" Focus on properties in: {', '.join(request.jurisdictions)}."

        query = f"Find all real estate properties owned by or transferred to/from {request.entity_name}.{jurisdiction_filter} Include purchase/sale dates, prices, and addresses."

        prompt = self.FINANCIAL_SOURCE_PROMPT.format(
            entity_name=request.entity_name,
            query=query,
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.3)

            current_holdings = []
            historical = []
            total_value = Decimal("0")

            for finding in result.get("findings", []):
                if finding.get("type") == "property":
                    prop = PropertyRecord(
                        address=finding.get("description", ""),
                        jurisdiction=finding.get("jurisdiction"),
                        owner=request.entity_name,
                        purchase_date=self._parse_date(finding.get("date")),
                        purchase_price=self._parse_decimal(finding.get("amount")),
                        source_url=finding.get("source_url"),
                    )

                    if finding.get("notes", "").lower().find("sold") >= 0:
                        prop.sale_date = self._parse_date(finding.get("date"))
                        prop.sale_price = self._parse_decimal(finding.get("amount"))
                        historical.append(prop)
                    else:
                        current_holdings.append(prop)
                        if prop.purchase_price:
                            total_value += prop.purchase_price

                    # Save to database
                    await self._save_property_record(prop, request.workspace_id)

            return PropertySearchResponse(
                entity_name=request.entity_name,
                properties_found=len(current_holdings) + len(historical),
                current_holdings=current_holdings,
                historical_transactions=historical if request.include_historical else [],
                total_current_value=total_value if total_value > 0 else None,
                sources_consulted=result.get("sources_consulted", []),
            )

        except Exception as e:
            logger.error(f"Property search failed: {e}")
            return PropertySearchResponse(
                entity_name=request.entity_name,
                properties_found=0,
            )

    async def find_beneficial_owners(
        self,
        company_name: str,
        workspace_id: str = "default",
    ) -> List[BeneficialOwner]:
        """
        Identify ultimate beneficial owners of a company.
        Traces through shell companies and nominee structures.
        """
        gemini = await self._get_gemini()
        if not gemini:
            return []

        query = f"Find the ultimate beneficial owners of {company_name}. Trace through any shell companies, trusts, or nominee structures to identify real human owners."

        prompt = self.FINANCIAL_SOURCE_PROMPT.format(
            entity_name=company_name,
            query=query,
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.3)

            owners = []
            for finding in result.get("findings", []):
                if finding.get("type") == "beneficial_owner":
                    owner = BeneficialOwner(
                        owner_name=finding.get("target_entity", ""),
                        ownership_type=finding.get("notes", "beneficial").split()[0] if finding.get("notes") else "beneficial",
                        evidence_strength=EvidenceStrength(finding.get("evidence_strength", "medium")),
                    )
                    owners.append(owner)

                    # Save to database
                    await self._save_beneficial_owner(owner, company_name, workspace_id)

            return owners

        except Exception as e:
            logger.error(f"Beneficial owner search failed: {e}")
            return []

    async def _analyze_shell_company(
        self,
        entity: FinancialEntity,
        workspace_id: str,
    ) -> ShellCompanyAnalysis:
        """Analyze entity for shell company indicators."""
        gemini = await self._get_gemini()

        # Basic jurisdiction check (fast)
        indicators = []
        secrecy_jurisdictions = [
            "Delaware", "Nevada", "Wyoming", "British Virgin Islands",
            "Cayman Islands", "Panama", "Seychelles", "Bermuda"
        ]

        if entity.jurisdiction and any(j.lower() in entity.jurisdiction.lower() for j in secrecy_jurisdictions):
            indicators.append(ShellCompanyIndicator(
                indicator_type=ShellIndicatorType.SECRECY_JURISDICTION,
                confidence=0.7,
                details=f"Registered in {entity.jurisdiction}, a known secrecy jurisdiction",
            ))

        # LLM analysis for deeper indicators
        if gemini:
            prompt = self.SHELL_COMPANY_PROMPT.format(
                entity_name=entity.name,
                entity_type=entity.entity_type.value,
                jurisdiction=entity.jurisdiction or "Unknown",
                known_info=f"Registered agent: {entity.registered_agent or 'Unknown'}\nAddress: {entity.registered_address or 'Unknown'}",
            )

            try:
                result, _ = await gemini.generate_json(prompt, temperature=0.2)

                for ind in result.get("indicators", []):
                    try:
                        indicators.append(ShellCompanyIndicator(
                            indicator_type=ShellIndicatorType(ind["type"]),
                            confidence=float(ind.get("confidence", 0.5)),
                            details=ind.get("details", ""),
                        ))
                    except (KeyError, ValueError):
                        pass

                # Get overall assessment
                assessment = result.get("overall_assessment", {})
                is_likely_shell = assessment.get("is_likely_shell", len(indicators) >= 2)
                overall_confidence = assessment.get("confidence", 0.5 if indicators else 0.1)

            except Exception as e:
                logger.warning(f"Shell company LLM analysis failed: {e}")
                is_likely_shell = len(indicators) >= 2
                overall_confidence = 0.5 if indicators else 0.1
        else:
            is_likely_shell = len(indicators) >= 2
            overall_confidence = 0.5 if indicators else 0.1

        # Save indicators to database
        for ind in indicators:
            await self._save_shell_indicator(entity, ind, workspace_id)

        return ShellCompanyAnalysis(
            entity=entity,
            indicators=indicators,
            indicator_count=len(indicators),
            is_likely_shell=is_likely_shell,
            overall_confidence=overall_confidence,
        )

    # ========================================
    # Database Operations
    # ========================================

    async def _save_financial_entity(self, entity: FinancialEntity, workspace_id: str) -> UUID:
        """Save a financial entity to the database."""
        entity_id = uuid4()
        try:
            self.db.client.table("financial_entities").insert({
                "id": str(entity_id),
                "name": entity.name,
                "entity_type": entity.entity_type.value,
                "jurisdiction": entity.jurisdiction,
                "registration_number": entity.registration_number,
                "status": entity.status,
                "incorporation_date": str(entity.incorporation_date) if entity.incorporation_date else None,
                "registered_agent": entity.registered_agent,
                "registered_address": entity.registered_address,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save financial entity: {e}")
        return entity_id

    async def _save_transaction(self, tx: FinancialTransaction, workspace_id: str):
        """Save a transaction to the database."""
        try:
            self.db.client.table("financial_transactions").insert({
                "id": str(uuid4()),
                "source_entity_id": str(tx.source_entity_id) if tx.source_entity_id else None,
                "target_entity_id": str(tx.target_entity_id) if tx.target_entity_id else None,
                "transaction_type": tx.transaction_type.value,
                "amount": float(tx.amount) if tx.amount else None,
                "currency": tx.currency,
                "transaction_date": str(tx.transaction_date) if tx.transaction_date else None,
                "transaction_date_precision": tx.date_precision,
                "description": tx.description,
                "purpose": tx.purpose,
                "evidence_strength": tx.evidence_strength.value,
                "source_document": tx.source_document,
                "source_url": tx.source_url,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save transaction: {e}")

    async def _save_property_record(self, prop: PropertyRecord, workspace_id: str):
        """Save a property record to the database."""
        try:
            self.db.client.table("property_records").insert({
                "id": str(uuid4()),
                "property_address": prop.address,
                "property_type": prop.property_type,
                "jurisdiction": prop.jurisdiction,
                "owner_name": prop.owner,
                "purchase_date": str(prop.purchase_date) if prop.purchase_date else None,
                "purchase_price": float(prop.purchase_price) if prop.purchase_price else None,
                "sale_date": str(prop.sale_date) if prop.sale_date else None,
                "sale_price": float(prop.sale_price) if prop.sale_price else None,
                "source_url": prop.source_url,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save property record: {e}")

    async def _save_beneficial_owner(self, owner: BeneficialOwner, company_name: str, workspace_id: str):
        """Save a beneficial owner to the database."""
        try:
            self.db.client.table("beneficial_owners").insert({
                "id": str(uuid4()),
                "owner_name": owner.owner_name,
                "ownership_type": owner.ownership_type,
                "ownership_percentage": owner.ownership_percentage,
                "control_type": owner.control_type,
                "evidence_strength": owner.evidence_strength.value,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save beneficial owner: {e}")

    async def _save_shell_indicator(
        self,
        entity: FinancialEntity,
        indicator: ShellCompanyIndicator,
        workspace_id: str,
    ):
        """Save a shell company indicator to the database."""
        try:
            # First ensure entity exists
            if not entity.id:
                entity.id = await self._save_financial_entity(entity, workspace_id)

            self.db.client.table("shell_company_indicators").insert({
                "id": str(uuid4()),
                "entity_id": str(entity.id),
                "indicator_type": indicator.indicator_type.value,
                "confidence": indicator.confidence,
                "details": indicator.details,
                "source_document": indicator.source_document,
                "detected_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save shell indicator: {e}")

    # ========================================
    # Helper Methods
    # ========================================

    def _finding_to_transaction(self, finding: Dict[str, Any]) -> FinancialTransaction:
        """Convert a finding dict to a FinancialTransaction."""
        return FinancialTransaction(
            transaction_type=self._infer_transaction_type(finding),
            amount=self._parse_decimal(finding.get("amount")),
            currency=finding.get("currency", "USD"),
            transaction_date=self._parse_date(finding.get("date")),
            description=finding.get("description"),
            purpose=finding.get("notes"),
            evidence_strength=EvidenceStrength(finding.get("evidence_strength", "medium")),
            source_document=finding.get("source_type"),
            source_url=finding.get("source_url"),
        )

    def _infer_transaction_type(self, finding: Dict[str, Any]) -> TransactionType:
        """Infer transaction type from finding description."""
        desc = (finding.get("description", "") + " " + finding.get("notes", "")).lower()

        if "sale" in desc or "sold" in desc:
            return TransactionType.SALE
        elif "purchase" in desc or "bought" in desc:
            return TransactionType.PURCHASE
        elif "loan" in desc or "lent" in desc:
            return TransactionType.LOAN
        elif "invest" in desc:
            return TransactionType.INVESTMENT
        elif "donat" in desc or "gift" in desc:
            return TransactionType.DONATION
        elif "fee" in desc:
            return TransactionType.FEE
        elif "settl" in desc:
            return TransactionType.SETTLEMENT
        elif "salary" in desc or "compensation" in desc:
            return TransactionType.SALARY
        else:
            return TransactionType.TRANSFER

    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse a value to Decimal."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Remove currency symbols and commas
                value = value.replace("$", "").replace(",", "").strip()
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse a value to date."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Try common formats
                for fmt in ["%Y-%m-%d", "%Y-%m", "%Y", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        return datetime.strptime(value[:10], fmt).date()
                    except ValueError:
                        continue
            return None
        except Exception:
            return None
