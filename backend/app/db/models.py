"""SQLAlchemy models for PostgreSQL."""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Document(Base):
    """Document storage model."""
    __tablename__ = "documents"

    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50), default="default", index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    size_class = Column(String(20), default="small")  # small or large
    token_count = Column(Integer, default=0)
    doc_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Chunk storage for large documents."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(100), unique=True, index=True)  # e.g., "doc_123_c1"
    document_id = Column(String(50), ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    section = Column(String(255))
    context = Column(Text)  # Contextual metadata
    position = Column(String(20))  # e.g., "3/12"
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class DocumentMap(Base):
    """Living document map storage."""
    __tablename__ = "document_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(50), unique=True, index=True)
    map_data = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatHistory(Base):
    """Chat conversation history."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(50), index=True)
    session_id = Column(String(50), index=True)
    role = Column(String(20))  # user or assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
