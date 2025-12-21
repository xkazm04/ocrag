"""
SQL schemas for structured document data.
Documents are decomposed into normalized tables for precise querying.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Float,
    ForeignKey, Boolean, Date, Index
)
from sqlalchemy.orm import relationship
from app.db.models import Base


class SQLDocument(Base):
    """Core document table for Agentic SQL RAG."""
    __tablename__ = "sql_documents"

    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50), index=True)
    filename = Column(String(255))
    document_type = Column(String(50))
    summary = Column(Text)
    purpose = Column(String(255))
    key_conclusion = Column(Text)
    document_date = Column(Date)
    period_start = Column(Date)
    period_end = Column(Date)
    confidence_level = Column(String(20))
    token_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    claims = relationship("SQLClaim", back_populates="document", cascade="all, delete-orphan")
    metrics = relationship("SQLMetric", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("SQLEntity", back_populates="document", cascade="all, delete-orphan")
    topics = relationship("SQLTopic", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("SQLDocumentChunk", back_populates="document", cascade="all, delete-orphan")


class SQLClaim(Base):
    """Factual claims extracted from documents."""
    __tablename__ = "sql_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)

    claim_text = Column(Text, nullable=False)
    claim_type = Column(String(50))  # fact, opinion, prediction, recommendation
    topic = Column(String(100), index=True)

    confidence = Column(String(20))  # high, medium, low
    source_section = Column(String(255))

    is_quantitative = Column(Boolean, default=False)
    can_be_verified = Column(Boolean, default=True)

    document = relationship("SQLDocument", back_populates="claims")

    __table_args__ = (
        Index('idx_claims_topic', topic),
        Index('idx_claims_document', document_id),
    )


class SQLMetric(Base):
    """Quantitative metrics extracted from documents."""
    __tablename__ = "sql_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)

    metric_name = Column(String(100), nullable=False, index=True)
    value = Column(String(100), nullable=False)
    numeric_value = Column(Float)
    unit = Column(String(50))

    period = Column(String(50))
    period_start = Column(Date)
    period_end = Column(Date)

    context = Column(Text)
    comparison_base = Column(String(100))

    entity_name = Column(String(255))
    category = Column(String(100), index=True)

    document = relationship("SQLDocument", back_populates="metrics")

    __table_args__ = (
        Index('idx_metrics_name', metric_name),
        Index('idx_metrics_period', period_start, period_end),
        Index('idx_metrics_entity', entity_name),
    )


class SQLEntity(Base):
    """Named entities extracted from documents."""
    __tablename__ = "sql_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)

    entity_name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), index=True)
    role = Column(String(50))

    title = Column(String(255))
    context = Column(Text)

    document = relationship("SQLDocument", back_populates="entities")

    __table_args__ = (
        Index('idx_entities_name_type', entity_name, entity_type),
    )


class SQLTopic(Base):
    """Topics associated with documents."""
    __tablename__ = "sql_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)

    topic_name = Column(String(100), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)

    document = relationship("SQLDocument", back_populates="topics")

    __table_args__ = (
        Index('idx_topics_name', topic_name),
    )


class SQLRelationship(Base):
    """Relationships between documents."""
    __tablename__ = "sql_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)
    target_document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)

    relationship_type = Column(String(50))
    description = Column(Text)


class SQLDocumentChunk(Base):
    """Full text chunks for fallback retrieval."""
    __tablename__ = "sql_document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id", ondelete="CASCADE"), index=True)

    chunk_index = Column(Integer)
    section_name = Column(String(255))
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer)

    document = relationship("SQLDocument", back_populates="chunks")


# Schema description for LLM
SQL_SCHEMA_DESCRIPTION = """
DATABASE SCHEMA:

## sql_documents
Main document metadata table.
Columns:
- id: Unique document identifier
- workspace_id: Workspace for multi-tenancy
- filename: Original filename
- document_type: Type (financial_report, legal_contract, technical_doc, etc.)
- summary: 2-3 sentence summary
- purpose: Why document exists
- key_conclusion: Main takeaway
- document_date: When created
- period_start, period_end: Time period covered
- confidence_level: Data reliability (high/medium/low)

## sql_claims
Factual claims extracted from documents.
Columns:
- id, document_id: Identifiers
- claim_text: The actual claim statement
- claim_type: fact, opinion, prediction, recommendation
- topic: Topic category
- confidence: Claim reliability
- source_section: Section of document
- is_quantitative: If claim involves numbers
- can_be_verified: If claim is verifiable

## sql_metrics
Quantitative metrics extracted from documents.
Columns:
- id, document_id: Identifiers
- metric_name: Name (Revenue, Growth Rate, Headcount, etc.)
- value: String value ($4.2B, 12%)
- numeric_value: Parsed float for comparison
- unit: Unit of measurement
- period: Time period string (Q3 2025)
- period_start, period_end: Date range
- context: Additional context
- comparison_base: Comparison type (YoY, QoQ)
- entity_name: Who metric is about
- category: Metric category (financial, operational)

## sql_entities
Named entities extracted from documents.
Columns:
- id, document_id: Identifiers
- entity_name: Name of entity
- entity_type: organization, person, product, location
- role: subject, author, mentioned, competitor
- title: Title (for people)
- context: Context in document

## sql_topics
Topics associated with documents.
Columns:
- id, document_id: Identifiers
- topic_name: Topic name
- is_primary: If primary topic (vs secondary)

## sql_relationships
Relationships between documents.
Columns:
- id: Identifier
- source_document_id, target_document_id: Related documents
- relationship_type: supersedes, references, supports, contradicts
- description: Relationship description

## sql_document_chunks
Full text chunks for fallback.
Columns:
- id, document_id: Identifiers
- chunk_index: Order in document
- section_name: Section heading
- chunk_text: Full text
- token_count: Size

COMMON QUERY PATTERNS:
- Join metrics with documents for context
- Filter by period_start/period_end for time ranges
- Use entity_name to find all info about specific company/person
- Use topics to find related documents
- Check confidence_level for reliability filtering
"""
