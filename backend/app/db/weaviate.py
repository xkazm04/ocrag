"""Weaviate client for hybrid search (fallback/augmentation)."""
import weaviate
from weaviate.classes.config import Configure, Property, DataType

from app.config import get_settings

client = None


async def init_weaviate():
    """Initialize Weaviate connection and schema."""
    global client

    settings = get_settings()

    if not settings.weaviate_url:
        raise RuntimeError("WEAVIATE_URL not configured")

    # Parse host from URL
    weaviate_host = settings.weaviate_url.replace("http://", "").replace("https://", "")
    if ":" in weaviate_host:
        host, port = weaviate_host.split(":")
        port = int(port)
    else:
        host = weaviate_host
        port = 8080

    try:
        client = weaviate.connect_to_custom(
            http_host=host,
            http_port=port,
            http_secure=False,
            grpc_host=host,
            grpc_port=50051,
            grpc_secure=False
        )

        # Create schema if not exists
        if not client.collections.exists("DocumentChunk"):
            client.collections.create(
                name="DocumentChunk",
                properties=[
                    Property(name="chunk_id", data_type=DataType.TEXT),
                    Property(name="document_id", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="section", data_type=DataType.TEXT),
                    Property(name="workspace_id", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none()
            )
    except Exception as e:
        print(f"Weaviate initialization: {e}")


def get_weaviate_client():
    """Get Weaviate client instance."""
    return client


async def store_chunk_vector(
    chunk_id: str,
    document_id: str,
    content: str,
    section: str,
    workspace_id: str,
    vector: list[float]
):
    """Store chunk with vector embedding."""
    if client is None:
        return

    collection = client.collections.get("DocumentChunk")

    collection.data.insert(
        properties={
            "chunk_id": chunk_id,
            "document_id": document_id,
            "content": content,
            "section": section,
            "workspace_id": workspace_id
        },
        vector=vector
    )


async def search_similar_chunks(
    query_vector: list[float],
    workspace_id: str,
    limit: int = 5
) -> list[dict]:
    """Search for similar chunks using vector similarity."""
    if client is None:
        return []

    collection = client.collections.get("DocumentChunk")

    results = collection.query.near_vector(
        near_vector=query_vector,
        limit=limit,
        filters=weaviate.classes.query.Filter.by_property("workspace_id").equal(workspace_id)
    )

    return [
        {
            "chunk_id": obj.properties["chunk_id"],
            "document_id": obj.properties["document_id"],
            "content": obj.properties["content"],
            "section": obj.properties["section"],
            "score": obj.metadata.certainty if obj.metadata else None
        }
        for obj in results.objects
    ]
