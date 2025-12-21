"""
SQL execution tool for the Agentic SQL RAG.
Provides read-only access to the structured document database.
"""
from typing import Optional
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SQLQueryTool:
    """Tool for executing SQL queries against document database."""

    name: str = "sql_query"
    description: str = """
    Execute a SQL SELECT query against the document database.
    Use this to retrieve specific information from extracted document data.

    Available tables:
    - sql_documents: Document metadata (id, filename, summary, document_date, etc.)
    - sql_claims: Factual claims (claim_text, claim_type, topic, confidence)
    - sql_metrics: Quantitative data (metric_name, value, numeric_value, period, entity_name)
    - sql_entities: Named entities (entity_name, entity_type, role)
    - sql_topics: Document topics (topic_name, is_primary)
    - sql_document_chunks: Full text chunks (chunk_text, section_name)

    IMPORTANT:
    - Only SELECT queries allowed
    - Always include LIMIT clause (max 50)
    - Use JOINs to connect data across tables
    - Filter by workspace_id when relevant
    """

    def __init__(self, db: AsyncSession, workspace_id: str = "default"):
        self.db = db
        self.workspace_id = workspace_id

    async def execute(self, query: str, explanation: str = "") -> str:
        """Execute query and return results as JSON string."""
        # Validate query is SELECT only
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return json.dumps({
                "error": "Only SELECT queries are allowed",
                "hint": "Rewrite your query as a SELECT statement"
            })

        # Check for dangerous keywords
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
        for keyword in dangerous:
            if keyword in query_upper:
                return json.dumps({
                    "error": f"Query contains forbidden keyword: {keyword}",
                    "hint": "Only read operations are permitted"
                })

        # Ensure LIMIT clause
        if "LIMIT" not in query_upper:
            query = query.rstrip(";") + " LIMIT 50"

        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            columns = list(result.keys())

            # Convert to list of dicts
            data = [dict(zip(columns, row)) for row in rows]

            # Handle date serialization
            for row in data:
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):
                        row[key] = value.isoformat()

            return json.dumps({
                "success": True,
                "row_count": len(data),
                "columns": columns,
                "data": data,
                "query_explanation": explanation
            }, indent=2, default=str)

        except Exception as e:
            return json.dumps({
                "error": str(e),
                "hint": "Check your SQL syntax and table/column names",
                "query_attempted": query
            })


def get_sql_tool(db: AsyncSession, workspace_id: str = "default") -> SQLQueryTool:
    """Get SQL tool instance."""
    return SQLQueryTool(db, workspace_id)
