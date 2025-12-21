"""Document management API routes."""
import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
import tiktoken

from app.db.postgres import get_db
from app.db.models import Document, DocumentChunk
from app.core.ocr_processor import get_ocr_processor, OCRProcessor
from app.core.document_map import DocumentMapManager
from app.core.agentic_sql.extractor import StructuredExtractor
from app.core.agentic_sql.schemas import SQLDocument
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse
)
from app.config import get_settings

router = APIRouter()


# Response model for chunk data
class ChunkResponse(BaseModel):
    """Single chunk response."""
    chunk_id: str
    document_id: str
    content: str
    section: Optional[str] = None
    context: Optional[str] = None
    position: Optional[str] = None
    token_count: int = 0


class ChunkListResponse(BaseModel):
    """List of chunks response."""
    document_id: str
    filename: str
    chunks: List[ChunkResponse]
    total: int


async def process_markdown(file_bytes: bytes, filename: str) -> dict:
    """
    Process markdown/text files directly without OCR.

    Returns same format as OCR processor for compatibility.
    """
    settings = get_settings()
    tokenizer = tiktoken.get_encoding("cl100k_base")

    # Decode content
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    # Count tokens
    token_count = len(tokenizer.encode(content))

    # Determine size class
    size_class = "small" if token_count < settings.small_doc_threshold_tokens else "large"

    result = {
        "content": content,
        "metadata": {
            "filename": filename,
            "token_count": token_count,
            "file_type": "markdown"
        },
        "size_class": size_class,
        "chunks": None
    }

    # Create chunks for large documents
    if size_class == "large":
        result["chunks"] = create_markdown_chunks(content, tokenizer, settings.chunk_size_tokens)

    return result


def create_markdown_chunks(content: str, tokenizer, max_tokens: int) -> list:
    """Create chunks from markdown content using header boundaries."""
    import re

    # Split on markdown headers
    header_pattern = r'\n(#{1,3}\s+.+)\n'
    parts = re.split(header_pattern, content)

    chunks = []
    current_section = "Introduction"
    current_content = ""

    for part in parts:
        if re.match(r'^#{1,3}\s+', part):
            # This is a header
            if current_content.strip():
                chunks.append({
                    "content": current_content.strip(),
                    "section": current_section
                })
            current_section = part.strip('# \n')
            current_content = part + "\n"
        else:
            test_content = current_content + part
            test_tokens = len(tokenizer.encode(test_content))

            if test_tokens > max_tokens and current_content.strip():
                chunks.append({
                    "content": current_content.strip(),
                    "section": current_section
                })
                current_content = part
            else:
                current_content = test_content

    if current_content.strip():
        chunks.append({
            "content": current_content.strip(),
            "section": current_section
        })

    # Convert to expected format with metadata
    enriched_chunks = []
    for i, chunk in enumerate(chunks):
        context_parts = [f"This is section '{chunk.get('section', 'Unknown')}' of the document."]
        if i > 0:
            context_parts.append(f"Previous section: '{chunks[i-1].get('section', 'Unknown')}'")
        if i < len(chunks) - 1:
            context_parts.append(f"Next section: '{chunks[i+1].get('section', 'Unknown')}'")

        enriched_chunks.append({
            "chunk_id": f"c{i+1}",
            "position": f"{i+1}/{len(chunks)}",
            "content": chunk["content"],
            "section": chunk.get("section", f"Section {i+1}"),
            "context": " ".join(context_parts),
            "token_count": len(tokenizer.encode(chunk["content"]))
        })

    return enriched_chunks


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    extraction_mode: str = Query(
        default="both",
        description="Extraction mode: 'map_only', 'sql_only', or 'both'"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process a document.

    1. OCR extraction using Gemini
    2. Intelligence extraction for document map (if mode includes 'map')
    3. Structured extraction to SQL tables (if mode includes 'sql')
    4. Chunking if large document
    5. Store in PostgreSQL

    extraction_mode options:
    - "map_only": Only populate document map (original RAG)
    - "sql_only": Only populate SQL tables (agentic RAG)
    - "both": Populate both (default, recommended)
    """
    # Validate file type
    allowed_types = {
        "application/pdf": "pdf",
        "image/png": "image",
        "image/jpeg": "image",
        "image/jpg": "image",
        "image/webp": "image",
        "text/markdown": "markdown",
        "text/x-markdown": "markdown",
        "text/plain": "text"  # Some systems send .md as text/plain
    }

    content_type = file.content_type
    filename = file.filename or ""

    # Check if it's a markdown file by extension (some systems don't set correct MIME type)
    if filename.lower().endswith(".md"):
        file_type = "markdown"
    elif content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Supported: PDF, PNG, JPG, WEBP, MD"
        )
    else:
        file_type = allowed_types[content_type]

    # Read file
    file_bytes = await file.read()

    # Generate document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # Process document based on type
    if file_type == "markdown":
        # Markdown files - no OCR needed, just read the content
        result = await process_markdown(file_bytes, filename)
    elif file_type == "pdf":
        ocr_processor = get_ocr_processor()
        result = await ocr_processor.process_pdf(file_bytes, filename)
    elif file_type == "text":
        # Plain text files - similar to markdown
        result = await process_markdown(file_bytes, filename)
    else:
        ocr_processor = get_ocr_processor()
        result = await ocr_processor.process_image(file_bytes, filename, content_type)

    # Store document
    document = Document(
        id=doc_id,
        workspace_id=workspace_id,
        filename=file.filename,
        content=result["content"],
        size_class=result["size_class"],
        token_count=result["metadata"].get("token_count", 0),
        doc_metadata=result["metadata"]
    )
    db.add(document)

    # Store chunks if large document
    if result["chunks"]:
        for chunk in result["chunks"]:
            db_chunk = DocumentChunk(
                chunk_id=f"{doc_id}_{chunk['chunk_id']}",
                document_id=doc_id,
                content=chunk["content"],
                section=chunk["section"],
                context=chunk["context"],
                position=chunk["position"],
                token_count=chunk["token_count"]
            )
            db.add(db_chunk)

    await db.commit()

    doc_entry = None
    sql_stats = None

    # Update document map (original RAG)
    if extraction_mode in ["map_only", "both"]:
        map_manager = DocumentMapManager(db)
        doc_entry = await map_manager.add_document(
            workspace_id=workspace_id,
            document_id=doc_id,
            filename=file.filename,
            content=result["content"],
            size_class=result["size_class"],
            chunks=result["chunks"]
        )

    # Extract to SQL tables (Agentic SQL RAG)
    if extraction_mode in ["sql_only", "both"]:
        extractor = StructuredExtractor(db)
        sql_stats = await extractor.extract_and_store(
            document_id=doc_id,
            workspace_id=workspace_id,
            filename=file.filename,
            content=result["content"],
            chunks=result["chunks"]
        )

    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        size_class=result["size_class"],
        token_count=result["metadata"].get("token_count", 0),
        chunk_count=len(result["chunks"]) if result["chunks"] else 0,
        essence=doc_entry["essence"] if doc_entry else "",
        topics=doc_entry["topics"] if doc_entry else []
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """List all documents in workspace."""
    result = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id)
    )
    documents = result.scalars().all()

    doc_responses = []
    for doc in documents:
        # Count chunks
        chunk_result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        chunks = chunk_result.scalars().all()

        doc_responses.append(
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                size_class=doc.size_class,
                token_count=doc.token_count,
                chunk_count=len(chunks),
                essence=doc.doc_metadata.get("essence", "") if doc.doc_metadata else "",
                topics=doc.doc_metadata.get("topics", []) if doc.doc_metadata else []
            )
        )

    return DocumentListResponse(
        documents=doc_responses,
        total=len(doc_responses)
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document by ID."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Count chunks
    chunk_result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    chunks = chunk_result.scalars().all()

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        size_class=document.size_class,
        token_count=document.token_count,
        chunk_count=len(chunks),
        essence=document.doc_metadata.get("essence", "") if document.doc_metadata else "",
        topics=document.doc_metadata.get("topics", []) if document.doc_metadata else []
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and update map."""
    # Check if document exists
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from database (chunks cascade)
    await db.execute(
        delete(Document).where(Document.id == document_id)
    )

    # Also delete from SQL tables (Agentic SQL RAG)
    await db.execute(
        delete(SQLDocument).where(SQLDocument.id == document_id)
    )

    await db.commit()

    # Update document map
    map_manager = DocumentMapManager(db)
    await map_manager.remove_document(workspace_id, document_id)

    return DocumentDeleteResponse(status="deleted", document_id=document_id)


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
async def get_document_chunks(
    document_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get all chunks for a document."""
    # Get the document first
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get chunks
    chunk_result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    chunks = chunk_result.scalars().all()

    chunk_responses = []

    if chunks:
        # Document has chunks - return them
        for chunk in chunks:
            chunk_responses.append(
                ChunkResponse(
                    chunk_id=chunk.chunk_id,
                    document_id=document_id,
                    content=chunk.content,
                    section=chunk.section,
                    context=chunk.context,
                    position=chunk.position,
                    token_count=chunk.token_count
                )
            )
    else:
        # Small document - return full content as single "chunk"
        chunk_responses.append(
            ChunkResponse(
                chunk_id=f"{document_id}_full",
                document_id=document_id,
                content=document.content,
                section="Full Document",
                context="This is the complete document content.",
                position="1/1",
                token_count=document.token_count
            )
        )

    return ChunkListResponse(
        document_id=document_id,
        filename=document.filename,
        chunks=chunk_responses,
        total=len(chunk_responses)
    )


@router.get("/map/view")
async def get_document_map(
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get the current document map for visualization."""
    map_manager = DocumentMapManager(db)
    doc_map = await map_manager.get_map(workspace_id)
    return doc_map
