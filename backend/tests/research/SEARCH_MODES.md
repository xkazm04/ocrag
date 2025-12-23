# Search Modes: Grounding vs Search Tool

## Overview

Two approaches for web-augmented LLM responses:

1. **Grounding** - LLM has built-in web search, searches and synthesizes in one call
2. **Search Tool** - Explicit web search API, then feed results to LLM

---

## Grounding (Built-in Google Search)

### How it works
```python
config = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())]
)
response = client.models.generate_content(prompt, config=config)
# Response includes grounding_metadata with sources
```

### Pros
- Single API call (lower latency)
- LLM decides when/what to search
- Sources automatically cited
- Cost-efficient for simple queries
- Real-time information access

### Cons
- Less control over search queries
- Can't inspect raw results before synthesis
- Sources are proxied URLs (not direct)
- May miss nuances if LLM skips search
- Hard to cache/reuse search results

### Best For
- Quick fact-checking ("What is X?")
- Current events summaries
- Simple Q&A with citations
- Cost-sensitive applications
- Perspective analysis (when findings already exist)

---

## Search Tool (Explicit Web Search)

### How it works
```python
# Step 1: Search
results = await search_api.search("query")  # Brave/Serper/Google

# Step 2: Synthesize
prompt = f"Based on these sources:\n{results}\n\nAnswer: {question}"
response = await llm.generate(prompt)
```

### Pros
- Full control over search queries
- Inspect/filter results before synthesis
- Multiple search providers available
- Cache search results separately
- Better source metadata (full URLs, dates)
- Can iterate and refine searches

### Cons
- Multiple API calls (higher latency)
- More complex implementation
- Need separate search API key
- Higher cost for complex research

### Best For
- Deep investigative research
- Knowledge graph building (need structured sources)
- Multi-query research pipelines
- When you need to store/audit sources
- Iterative research with follow-ups
- Source quality filtering

---

## Recommendation for Our Research System

| Research Phase | Recommended Mode | Reason |
|----------------|------------------|--------|
| Query Generation | No search | LLM generates queries from topic |
| Initial Research | **Search Tool** | Need to control queries, inspect sources |
| Source Synthesis | **Grounding** | Quick synthesis of known content |
| Finding Extraction | No search | Process existing synthesized content |
| Perspective Analysis | **Grounding** | Quick augmentation with current events |
| Follow-up Research | **Search Tool** | Need precise control for gaps |

### Hybrid Approach

```
[Query] -> [Search Tool: controlled queries]
                    |
                    v
            [Raw Sources] -> [Cache/Store]
                    |
                    v
            [Grounding: quick synthesis]
                    |
                    v
            [Findings] -> [Perspective Analysis with Grounding]
```

---

## Implementation Plan

1. **GeminiResearchClient** with modes:
   - `search_mode="grounding"` - Use built-in Google Search
   - `search_mode="tool"` - Use external search API
   - `search_mode="hybrid"` - Search Tool for main research, Grounding for synthesis

2. **Search Providers** (for tool mode):
   - Brave Search API (good balance of quality/cost)
   - Serper API (Google results, affordable)
   - Google Custom Search (official, higher cost)

3. **Caching Layer**:
   - Cache search results by query hash
   - Reuse results for similar queries
   - TTL-based expiration for freshness
