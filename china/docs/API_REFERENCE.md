# API Reference

Base URL:

```text
http://127.0.0.1:8010
```

## Health

### `GET /health`

Returns backend status, active provider, model and indexed chunk count.

## Upload and Ingestion

### `POST /upload`

Uploads one or more files. Supports background and deferred ingestion options.

### `POST /upload/chunk`

Uploads a large file in chunks.

### `POST /upload/chunk/cancel`

Cancels an active chunked upload.

### `POST /ingest/jobs`

Creates a background ingestion job from existing file paths.

### `GET /ingest/jobs/{job_id}`

Returns a single ingestion job state.

### `POST /ingest/jobs-batch-status`

Returns status for multiple ingestion jobs.

## Retrieval and Answering

### `POST /retrieve`

Runs retrieval only.

Request:

```json
{
  "query": "string",
  "top_k": 8
}
```

### `POST /generate`

Retrieves evidence and generates an answer.

Request:

```json
{
  "query": "string",
  "top_k": 8,
  "use_llm": true,
  "model": "optional-ollama-model"
}
```

### `POST /api/query`

Main chat endpoint. Returns answer, evidence, answer claims, current evidence graph, session graph and knowledge progress.

Request:

```json
{
  "query": "string",
  "session_id": "optional-session-id",
  "top_k": 8,
  "use_llm": true,
  "model": "optional-ollama-model"
}
```

Important response fields:

```json
{
  "session_id": "...",
  "query_id": "...",
  "answer": "...",
  "answer_claims": [],
  "evidence": [],
  "evidence_graph": {
    "nodes": [],
    "edges": []
  },
  "session_evidence_graph": {},
  "source_types": {}
}
```

## Knowledge Tree and Graph

### `GET /api/knowledge/tree`

Query parameters:

```text
limit   optional node/chunk limit
doc_id  optional document filter
q       optional search/focus query
```

Returns a dynamic tree generated from the current knowledge base.

### `GET /api/knowledge/graph`

Returns nodes and edges for graph visualization.

### `POST /api/knowledge/reset`

Clears generated knowledge indexes and optional sessions/rules.

Request:

```json
{
  "include_raw": false,
  "clear_sessions": true,
  "clear_rules": true
}
```

## Model Selection

### `GET /api/models`

Returns active provider, active model and detected local Ollama models.

### `POST /api/models/select`

Selects a local Ollama model for future answers.

Request:

```json
{
  "model": "qwen2.5:7b-instruct"
}
```

## Sessions

### `GET /api/sessions`

Lists local conversation sessions.

### `GET /api/session/{session_id}`

Loads a session graph and memory summary.

### `GET /api/session/{session_id}/evidence-graph`

Returns the accumulated evidence graph for a session.

### `DELETE /api/session/{session_id}`

Deletes one local session.

## Rule Memory

### `GET /api/memory/rules`

Lists refined rule memory.

### `POST /api/memory/rules/refresh`

Rebuilds or merges rule memory from current chunks.

### `DELETE /api/memory/rules`

Clears rule memory.

## Exports

```text
GET  /exports/knowledge-graph.svg
GET  /exports/knowledge-graph.html
GET  /exports/knowledge-graph.png
GET  /exports/word-report
POST /exports/word-report
```

These endpoints export knowledge graph visuals and Word reports when dependencies are available.
