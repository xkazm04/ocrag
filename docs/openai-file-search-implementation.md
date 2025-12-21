# OpenAI File Search Implementation Guide

This document describes how the OpenAI Assistants API with File Search is implemented in the OCRAG frontend.

## Overview

The implementation uses OpenAI's Assistants API with the `file_search` tool to enable RAG (Retrieval-Augmented Generation) over uploaded documents. The architecture consists of:

1. **Vector Store** - Stores document embeddings for semantic search
2. **Files** - Documents uploaded to OpenAI and indexed in the vector store
3. **Assistant** - AI agent configured with file_search capability
4. **Thread** - Conversation context for multi-turn chat
5. **Run** - Execution of the assistant on a thread

## API Call Cascade

### 1. Initialization Flow (on first load)

```
┌─────────────────────────────────────────────────────────────────┐
│                    _load_existing_resources()                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.vector_stores.list(limit=10)                       │
│  → Returns list of existing vector stores                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Find "RAG_Comparison_Store" or use first available             │
│  → Store vector_store_id in session state                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.vector_stores.files.list(vector_store_id, limit=100)│
│  → Returns files in the vector store with status                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  For each file: client.files.retrieve(file_id)                  │
│  → Get filename, bytes, created_at metadata                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.assistants.list(limit=20)                          │
│  → Find existing "RAG Comparison Assistant"                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2. File Upload Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    _openai_upload_file()                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  If no vector_store_id:                                         │
│  client.beta.vector_stores.create(name="RAG_Comparison_Store")  │
│  → Creates new vector store, returns vs.id                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.files.create(file=(filename, bytes), purpose="assistants")│
│  → Uploads file to OpenAI, returns file_obj.id                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.vector_stores.files.create_and_poll(               │
│      vector_store_id=vs_id,                                     │
│      file_id=file_obj.id                                        │
│  )                                                              │
│  → Adds file to vector store and WAITS for indexing             │
│  → Returns status: "completed" | "in_progress" | "failed"       │
└─────────────────────────────────────────────────────────────────┘
```

**Important:** Use `create_and_poll()` instead of `create()` to ensure the file is fully indexed before querying.

### 3. Query Flow (Chat)

```
┌─────────────────────────────────────────────────────────────────┐
│                      _openai_query()                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  If no assistant_id:                                            │
│  client.beta.assistants.create(                                 │
│      name="RAG Comparison Assistant",                           │
│      model="gpt-4o-mini",                                       │
│      tools=[{"type": "file_search"}],                           │
│      tool_resources={                                           │
│          "file_search": {"vector_store_ids": [vs_id]}           │
│      }                                                          │
│  )                                                              │
│  → Creates assistant with file_search tool                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  If no thread_id:                                               │
│  client.beta.threads.create()                                   │
│  → Creates conversation thread                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.threads.messages.create(                           │
│      thread_id=thread_id,                                       │
│      role="user",                                               │
│      content=question                                           │
│  )                                                              │
│  → Adds user message to thread                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.threads.runs.create_and_poll(                      │
│      thread_id=thread_id,                                       │
│      assistant_id=assistant_id                                  │
│  )                                                              │
│  → Executes assistant and WAITS for completion                  │
│  → Returns run.status: "completed" | "failed" | "expired"       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.threads.messages.list(                             │
│      thread_id=thread_id,                                       │
│      order="desc",                                              │
│      limit=1                                                    │
│  )                                                              │
│  → Gets the latest assistant response                           │
│  → Extract text and annotations (citations)                     │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Cleanup Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      _openai_cleanup()                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.assistants.delete(assistant_id)                    │
│  → Deletes the assistant                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  For each file: client.files.delete(file_id)                    │
│  → Deletes files from OpenAI storage                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  client.beta.vector_stores.delete(vector_store_id)              │
│  → Deletes the vector store                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Key API Methods Reference

### Vector Stores

| Method | Description |
|--------|-------------|
| `client.beta.vector_stores.list(limit=N)` | List all vector stores |
| `client.beta.vector_stores.create(name="...")` | Create new vector store |
| `client.beta.vector_stores.retrieve(vs_id)` | Get vector store details |
| `client.beta.vector_stores.delete(vs_id)` | Delete vector store |

### Vector Store Files

| Method | Description |
|--------|-------------|
| `client.beta.vector_stores.files.list(vector_store_id, limit=N)` | List files in store |
| `client.beta.vector_stores.files.create(vector_store_id, file_id)` | Add file (async) |
| `client.beta.vector_stores.files.create_and_poll(...)` | Add file and wait |
| `client.beta.vector_stores.files.retrieve(vs_id, file_id)` | Get file status |

### Files

| Method | Description |
|--------|-------------|
| `client.files.list()` | List all files in account |
| `client.files.create(file=(...), purpose="assistants")` | Upload file |
| `client.files.retrieve(file_id)` | Get file metadata |
| `client.files.delete(file_id)` | Delete file |

### Assistants

| Method | Description |
|--------|-------------|
| `client.beta.assistants.list(limit=N)` | List assistants |
| `client.beta.assistants.create(...)` | Create assistant |
| `client.beta.assistants.delete(assistant_id)` | Delete assistant |

### Threads & Messages

| Method | Description |
|--------|-------------|
| `client.beta.threads.create()` | Create conversation thread |
| `client.beta.threads.messages.create(thread_id, role, content)` | Add message |
| `client.beta.threads.messages.list(thread_id, order, limit)` | Get messages |

### Runs

| Method | Description |
|--------|-------------|
| `client.beta.threads.runs.create(thread_id, assistant_id)` | Start run (async) |
| `client.beta.threads.runs.create_and_poll(...)` | Start run and wait |
| `client.beta.threads.runs.retrieve(thread_id, run_id)` | Check run status |

## File Status Values

When a file is added to a vector store, it goes through processing:

| Status | Description |
|--------|-------------|
| `in_progress` | File is being chunked and embedded |
| `completed` | File is ready for search |
| `failed` | Processing failed (check error) |
| `cancelled` | Processing was cancelled |

## Run Status Values

When a run is executed:

| Status | Description |
|--------|-------------|
| `queued` | Waiting to start |
| `in_progress` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Execution failed |
| `cancelled` | Was cancelled |
| `expired` | Timed out |
| `requires_action` | Needs tool call response |

## Session State Variables

The implementation uses these Streamlit session state variables:

| Variable | Type | Description |
|----------|------|-------------|
| `openai_api_key` | str | OpenAI API key |
| `openai_vector_store_id` | str | Current vector store ID |
| `openai_files` | list | Files in vector store |
| `openai_assistant_id` | str | Current assistant ID |
| `openai_thread_id` | str | Current conversation thread |
| `openai_messages` | list | Chat message history |
| `openai_initialized` | bool | Whether resources have been loaded |

## Pricing Considerations

- **Storage**: $0.10 per GB per day for vector store storage
- **File Search**: $2.50 per 1,000 tool calls
- **Vector stores expire** after 7 days of inactivity by default

## Common Issues & Solutions

### Issue: Files not appearing after upload
**Solution:** Use `create_and_poll()` instead of `create()` to wait for indexing.

### Issue: "No vector store" error
**Solution:** Ensure vector store is created before uploading files.

### Issue: Citations not extracted
**Solution:** Check `content.text.annotations` for `file_citation` type annotations.

### Issue: Run times out
**Solution:** Increase timeout or check if files are still processing.

## References

- [OpenAI Assistants File Search Guide](https://platform.openai.com/docs/assistants/tools/file-search)
- [Vector Stores API Reference](https://platform.openai.com/docs/api-reference/vector-stores)
- [Vector Store Files API Reference](https://platform.openai.com/docs/api-reference/vector-stores-files)
- [Assistants API Reference](https://platform.openai.com/docs/api-reference/assistants)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
