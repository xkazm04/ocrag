"""
Agentic SQL RAG Agent.
Uses Gemini for iterative query planning and execution.
"""
from typing import Optional
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.gemini_client import get_gemini_client
from app.core.agentic_sql.sql_tool import SQLQueryTool
from app.core.agentic_sql.schemas import SQL_SCHEMA_DESCRIPTION


AGENT_SYSTEM_PROMPT = """You are an intelligent document analyst with access to a SQL database containing structured information extracted from documents.

{schema_description}

YOUR TASK:
Answer the user's question by querying the database. You can execute SQL SELECT queries.

APPROACH:
1. **Understand the Question**: What information is needed? What tables are relevant?

2. **Plan Your Queries**: Think about which tables to query and how to join them.
   - Start with broad queries to understand what data exists
   - Then narrow down to specific information needed

3. **Query Guidelines**:
   - Always JOIN tables when you need data from multiple sources
   - Use WHERE clauses to filter relevant data
   - Include LIMIT to avoid huge result sets
   - Query sql_claims for factual statements
   - Query sql_metrics for numerical data
   - Query sql_entities to find information about specific companies/people
   - Use sql_document_chunks as fallback for full text search

4. **Synthesize Answer**: Once you have sufficient data, compose a clear answer.
   - Cite specific data points from query results
   - Note any limitations or gaps in the data
   - Indicate confidence level

EXAMPLE QUERIES:
```sql
-- Find revenue metrics for a company
SELECT m.metric_name, m.value, m.period, d.filename
FROM sql_metrics m
JOIN sql_documents d ON m.document_id = d.id
WHERE m.entity_name ILIKE '%Acme%'
  AND m.category = 'financial'
ORDER BY m.period_start DESC
LIMIT 20;

-- Find claims about a topic
SELECT c.claim_text, c.confidence, d.filename, d.document_date
FROM sql_claims c
JOIN sql_documents d ON c.document_id = d.id
WHERE c.topic ILIKE '%revenue%'
  AND c.confidence = 'high'
LIMIT 20;

-- Find all info about an entity
SELECT e.entity_name, e.entity_type, e.role, e.context, d.filename
FROM sql_entities e
JOIN sql_documents d ON e.document_id = d.id
WHERE e.entity_name ILIKE '%John Smith%'
LIMIT 20;
```

Current workspace: {workspace_id}

Respond with a JSON object containing:
1. "queries": List of SQL queries to execute (each with "sql" and "purpose")
2. After seeing results, provide "answer" with your response
"""


class AgenticSQLAgent:
    """
    Agentic RAG using SQL queries and Gemini.

    The agent iteratively:
    1. Analyzes the question
    2. Plans SQL queries
    3. Executes queries
    4. Evaluates results
    5. Refines or synthesizes answer
    """

    def __init__(self, db: AsyncSession, workspace_id: str = "default"):
        self.db = db
        self.workspace_id = workspace_id
        self.settings = get_settings()
        self.gemini = get_gemini_client()
        self.sql_tool = SQLQueryTool(db, workspace_id)

    async def query(
        self,
        question: str,
        chat_history: Optional[list[dict]] = None,
        max_iterations: int = 5
    ) -> dict:
        """
        Answer a question using iterative SQL queries.

        Returns:
            {
                "answer": str,
                "queries_executed": list[str],
                "sources": list[str],
                "reasoning_steps": list[str],
                "iterations": int
            }
        """
        from google.genai import types

        queries_executed = []
        sources = set()
        reasoning_steps = []
        all_results = []

        # Build initial prompt
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            schema_description=SQL_SCHEMA_DESCRIPTION,
            workspace_id=self.workspace_id
        )

        # Include chat history context
        history_context = ""
        if chat_history:
            history_context = "\n\nPrevious conversation:\n" + "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in chat_history[-5:]
            ])

        # Initial planning call
        planning_prompt = f"""
{system_prompt}

{history_context}

USER QUESTION: {question}

First, analyze this question and provide a JSON response with:
{{
    "analysis": "Brief analysis of what information is needed",
    "queries": [
        {{"sql": "SELECT ...", "purpose": "Why this query"}}
    ]
}}

Plan 1-3 queries to answer the question.
"""

        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[types.Part.from_text(text=planning_prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        plan = self.gemini._parse_json_response(response.text)
        reasoning_steps.append(plan.get("analysis", "Analyzing question"))

        # Execute planned queries
        for query_plan in plan.get("queries", [])[:max_iterations]:
            sql = query_plan.get("sql", "")
            purpose = query_plan.get("purpose", "")

            if sql:
                queries_executed.append(sql)
                reasoning_steps.append(f"Query: {purpose}")

                result = await self.sql_tool.execute(sql, purpose)
                result_data = json.loads(result)

                if result_data.get("success"):
                    all_results.append({
                        "query": sql,
                        "purpose": purpose,
                        "data": result_data.get("data", [])
                    })

                    # Extract source documents
                    for row in result_data.get("data", []):
                        if "filename" in row:
                            sources.add(row["filename"])

        # Generate final answer based on results
        synthesis_prompt = f"""
{system_prompt}

USER QUESTION: {question}

QUERY RESULTS:
{json.dumps(all_results, indent=2, default=str)}

Based on the query results above, provide a JSON response with:
{{
    "answer": "Your comprehensive answer citing specific data from the results",
    "confidence": 0.0-1.0,
    "sources_used": ["list of document filenames used"],
    "limitations": "Any gaps or limitations in the data"
}}

Be specific and cite actual values from the results. If the data is insufficient, say so clearly.
"""

        final_response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[types.Part.from_text(text=synthesis_prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        synthesis = self.gemini._parse_json_response(final_response.text)

        return {
            "answer": synthesis.get("answer", "I couldn't find sufficient information to answer this question."),
            "queries_executed": queries_executed,
            "sources": list(sources),
            "reasoning_steps": reasoning_steps,
            "iterations": len(queries_executed),
            "confidence": synthesis.get("confidence", 0.5),
            "limitations": synthesis.get("limitations", "")
        }


def get_agentic_sql_agent(db: AsyncSession, workspace_id: str = "default") -> AgenticSQLAgent:
    """Get agentic SQL agent instance."""
    return AgenticSQLAgent(db, workspace_id)
