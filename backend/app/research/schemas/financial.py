"""Schemas for financial forensics research."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class FinancialEntityType(str, Enum):
    """Types of financial entities."""
    CORPORATION = "corporation"
    LLC = "llc"
    TRUST = "trust"
    FOUNDATION = "foundation"
    PARTNERSHIP = "partnership"
    BANK_ACCOUNT = "bank_account"
    BROKERAGE = "brokerage"
    SHELL_COMPANY = "shell_company"
    UNKNOWN = "unknown"


class TransactionType(str, Enum):
    """Types of financial transactions."""
    TRANSFER = "transfer"
    SALE = "sale"
    PURCHASE = "purchase"
    LOAN = "loan"
    INVESTMENT = "investment"
    DONATION = "donation"
    FEE = "fee"
    SETTLEMENT = "settlement"
    SALARY = "salary"
    GIFT = "gift"


class EvidenceStrength(str, Enum):
    """Strength of evidence for financial claims."""
    HIGH = "high"          # Primary source (SEC filing, court doc)
    MEDIUM = "medium"      # Reliable journalism with sources
    LOW = "low"            # Single source, unverified
    ALLEGED = "alleged"    # Claimed but disputed


class CorporateRelationshipType(str, Enum):
    """Types of corporate relationships."""
    OWNS = "owns"
    CONTROLS = "controls"
    SUBSIDIARY = "subsidiary"
    AFFILIATE = "affiliate"
    DIRECTOR = "director"
    OFFICER = "officer"
    REGISTERED_AGENT = "registered_agent"
    BENEFICIAL_OWNER = "beneficial_owner"
    NOMINEE = "nominee"


class ShellIndicatorType(str, Enum):
    """Types of shell company indicators."""
    SECRECY_JURISDICTION = "secrecy_jurisdiction"
    NO_PHYSICAL_ADDRESS = "no_physical_address"
    REGISTERED_AGENT_ONLY = "registered_agent_only"
    NO_EMPLOYEES = "no_employees"
    CIRCULAR_OWNERSHIP = "circular_ownership"
    RAPID_OWNERSHIP_CHANGES = "rapid_ownership_changes"
    NO_PUBLIC_FILINGS = "no_public_filings"
    NOMINEE_DIRECTORS = "nominee_directors"


# ============================================
# Financial Entity Schemas
# ============================================

class FinancialEntity(BaseModel):
    """A financial entity (company, trust, account, etc.)."""
    id: Optional[UUID] = None
    name: str
    entity_type: FinancialEntityType
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None
    status: Optional[str] = None
    incorporation_date: Optional[date] = None
    dissolution_date: Optional[date] = None
    registered_agent: Optional[str] = None
    registered_address: Optional[str] = None
    linked_person_id: Optional[UUID] = None  # Link to knowledge_entities
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FinancialEntityCreate(BaseModel):
    """Request to create a financial entity."""
    name: str = Field(..., min_length=1)
    entity_type: FinancialEntityType
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None
    status: Optional[str] = None
    incorporation_date: Optional[date] = None
    entity_id: Optional[UUID] = None  # Link to knowledge_entities
    workspace_id: str = "default"


# ============================================
# Transaction Schemas
# ============================================

class FinancialTransaction(BaseModel):
    """A financial transaction between entities."""
    id: Optional[UUID] = None
    source_entity: Optional[FinancialEntity] = None
    source_entity_id: Optional[UUID] = None
    target_entity: Optional[FinancialEntity] = None
    target_entity_id: Optional[UUID] = None
    transaction_type: TransactionType
    amount: Optional[Decimal] = None
    currency: str = "USD"
    transaction_date: Optional[date] = None
    date_precision: str = "day"
    description: Optional[str] = None
    purpose: Optional[str] = None
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM
    source_document: Optional[str] = None
    source_url: Optional[str] = None


class TransactionChain(BaseModel):
    """A sequence of connected transactions."""
    id: Optional[UUID] = None
    transactions: List[FinancialTransaction]
    total_amount: Optional[Decimal] = None
    start_entity: str
    end_entity: str
    chain_length: int
    time_span_days: Optional[int] = None
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM


# ============================================
# Corporate Structure Schemas
# ============================================

class CorporateRelationship(BaseModel):
    """A relationship between corporate entities."""
    id: Optional[UUID] = None
    parent_entity: FinancialEntity
    child_entity: FinancialEntity
    relationship_type: CorporateRelationshipType
    ownership_percentage: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM
    source_document: Optional[str] = None


class CorporateStructure(BaseModel):
    """Hierarchical corporate ownership structure."""
    root_entity: FinancialEntity
    subsidiaries: List["CorporateStructure"] = Field(default_factory=list)
    ownership_percentage: Optional[float] = None
    relationship_type: str = "subsidiary"


# Enable forward reference
CorporateStructure.model_rebuild()


class BeneficialOwner(BaseModel):
    """Ultimate beneficial owner of a company."""
    id: Optional[UUID] = None
    owner_name: str
    owner_entity_id: Optional[UUID] = None
    ownership_percentage: Optional[float] = None
    ownership_type: str  # direct, indirect, beneficial, nominee
    control_type: Optional[str] = None  # voting, economic, both
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM
    source_document: Optional[str] = None


# ============================================
# Property Schemas
# ============================================

class PropertyRecord(BaseModel):
    """A real estate property record."""
    id: Optional[UUID] = None
    address: str
    property_type: Optional[str] = None  # residential, commercial, land, mixed
    jurisdiction: Optional[str] = None  # County, State
    parcel_id: Optional[str] = None
    owner: str
    owner_entity_id: Optional[UUID] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    sale_date: Optional[date] = None
    sale_price: Optional[Decimal] = None
    current_assessed_value: Optional[Decimal] = None
    source_url: Optional[str] = None


# ============================================
# Shell Company Schemas
# ============================================

class ShellCompanyIndicator(BaseModel):
    """An indicator of shell company activity."""
    indicator_type: ShellIndicatorType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    details: Optional[str] = None
    source_document: Optional[str] = None


class ShellCompanyAnalysis(BaseModel):
    """Analysis of potential shell company status."""
    entity: FinancialEntity
    indicators: List[ShellCompanyIndicator]
    indicator_count: int
    is_likely_shell: bool
    overall_confidence: float
    analysis_notes: Optional[str] = None


# ============================================
# Request Schemas
# ============================================

class TraceMoneyRequest(BaseModel):
    """Request to trace financial transactions."""
    entity_name: str = Field(..., min_length=1)
    entity_id: Optional[UUID] = None
    direction: Literal["forward", "backward", "both"] = "both"
    amount_filter: Optional[Decimal] = None  # Only transactions >= this amount
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    max_hops: int = Field(default=5, ge=1, le=10)
    include_shell_detection: bool = True
    workspace_id: str = "default"


class CorporateStructureRequest(BaseModel):
    """Request to build corporate structure."""
    entity_name: str = Field(..., min_length=1)
    entity_id: Optional[UUID] = None
    include_officers: bool = True
    include_historical: bool = False
    max_depth: int = Field(default=5, ge=1, le=10)
    workspace_id: str = "default"


class PropertySearchRequest(BaseModel):
    """Request to search property records."""
    entity_name: str = Field(..., min_length=1)
    entity_id: Optional[UUID] = None
    include_historical: bool = True
    jurisdictions: Optional[List[str]] = None
    workspace_id: str = "default"


class BeneficialOwnerRequest(BaseModel):
    """Request to find beneficial owners."""
    company_name: str = Field(..., min_length=1)
    company_id: Optional[UUID] = None
    max_depth: int = Field(default=5, ge=1, le=10)
    workspace_id: str = "default"


# ============================================
# Response Schemas
# ============================================

class TraceMoneyResponse(BaseModel):
    """Response from money tracing."""
    entity_name: str
    chains_found: int
    forward_chains: List[TransactionChain] = Field(default_factory=list)
    backward_chains: List[TransactionChain] = Field(default_factory=list)
    total_inflow: Optional[Decimal] = None
    total_outflow: Optional[Decimal] = None
    suspicious_patterns: List[str] = Field(default_factory=list)
    shell_companies_detected: List[FinancialEntity] = Field(default_factory=list)
    sources_consulted: List[str] = Field(default_factory=list)


class CorporateStructureResponse(BaseModel):
    """Response from corporate structure analysis."""
    root_entity: FinancialEntity
    structure: CorporateStructure
    officers: List[Dict[str, Any]] = Field(default_factory=list)
    beneficial_owners: List[BeneficialOwner] = Field(default_factory=list)
    total_subsidiaries: int = 0
    jurisdictions: List[str] = Field(default_factory=list)
    sources_consulted: List[str] = Field(default_factory=list)


class PropertySearchResponse(BaseModel):
    """Response from property search."""
    entity_name: str
    properties_found: int
    current_holdings: List[PropertyRecord] = Field(default_factory=list)
    historical_transactions: List[PropertyRecord] = Field(default_factory=list)
    total_current_value: Optional[Decimal] = None
    sources_consulted: List[str] = Field(default_factory=list)


class FinancialEntityTransactionsResponse(BaseModel):
    """Response with entity transactions."""
    entity_id: UUID
    entity_name: str
    transactions: List[FinancialTransaction]
    total_inflow: Decimal
    total_outflow: Decimal
    net_flow: Decimal
    transaction_count: int


class FinancialSummary(BaseModel):
    """Summary of financial analysis for an entity."""
    entity_name: str
    entity_id: Optional[UUID] = None
    total_inflow: Decimal = Decimal("0")
    total_outflow: Decimal = Decimal("0")
    net_flow: Decimal = Decimal("0")
    transaction_count: int = 0
    properties_count: int = 0
    subsidiaries_count: int = 0
    shell_indicator_count: int = 0
    is_likely_shell: bool = False
