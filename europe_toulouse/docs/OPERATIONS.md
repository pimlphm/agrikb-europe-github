# Operations Guide

## Routine Health Checks

Check backend:

```text
http://127.0.0.1:8010/health
```

Expected:

```text
status=ok
indexed_chunk_count > 0 after ingestion
```

Check local models:

```text
http://127.0.0.1:8010/api/models
```

## Reset Procedures

Use the UI "重置知识树" button or call:

```http
POST /api/knowledge/reset
```

Default behavior clears generated knowledge indexes, sessions and rule memory while preserving raw uploads.

## Backups

Before major changes, back up:

```text
config.yaml
.env
knowledge/chunks.db
knowledge/agent_memory/
knowledge/sessions/
data/raw/
```

Do not put `.env` or private documents in public GitHub repositories.

## Large Document Batches

Recommended process:

1. Upload documents in batches.
2. Wait for coarse tree to appear.
3. Allow background refinement to continue.
4. Ask broad questions only after coarse ingestion is ready.
5. Ask detailed evidence questions after refinement completes.

## Performance Notes

- SQLite chunk storage is faster than writing thousands of JSON chunk files.
- BM25-first retrieval keeps local search responsive.
- Dense retrieval and reranking can improve relevance but may increase latency.
- Local model speed depends on model size, CPU/GPU, context length and Ollama configuration.

## Package Hygiene

Before release, verify that a package does not contain:

```text
.env
.venv
runtime/
backups/
__pycache__/
private raw documents
API keys
legacy GUI folders
```

## Recommended Release Checklist

- Start service successfully.
- Open UI.
- Upload a small test document.
- Ask a test question.
- Verify evidence chain renders.
- Verify knowledge tree updates.
- Verify `/api/models` works.
- Run syntax checks.
- Inspect package contents for secrets.
