# Configuration Guide

## Configuration Files

```text
config.yaml     Default runtime configuration
.env.example    Safe template for per-computer environment variables
.env            Local secrets and overrides, never commit this file
```

## Backend Selection

Supported backend modes:

```text
auto                 prefer local Ollama, fallback to OpenAI-compatible API
ollama               force local Ollama
openai_compatible    force remote/intranet OpenAI-compatible API
api_key              alias for API-key backend
```

## Key Environment Variables

```text
KNOWLEDGE_RAG_BACKEND
OLLAMA_BASE_URL
OLLAMA_MODEL
KNOWLEDGE_RAG_BASE_URL
KNOWLEDGE_RAG_API_KEY
KNOWLEDGE_RAG_MODEL
KNOWLEDGE_RAG_EMBEDDING_MODEL
KNOWLEDGE_RAG_REMOTE_EMBEDDINGS
KNOWLEDGE_RAG_HOST
KNOWLEDGE_RAG_PORT
```

## Storage Paths

Default storage areas:

```text
data/raw/                 saved uploads
data/processed/           processed artifacts
knowledge/chunks.db       SQLite chunk index
knowledge/chunks/         optional JSON chunks
knowledge/wiki/           generated wiki-style pages
knowledge/sessions/       conversation memory
knowledge/agent_memory/   rule memory
runtime/                  temporary exports and runtime artifacts
```

## Ingestion Tuning

Important settings in `config.yaml`:

```yaml
ingestion:
  parse_workers: 12
  db_batch_size: 4000
  chunk_file_workers: 0
  write_chunk_json_files: false
```

For many documents, keep `write_chunk_json_files: false` so SQLite is the main index source.

## Retrieval Tuning

```yaml
retrieval:
  chunk_size: 420
  chunk_overlap: 80
  top_k: 10
  dense_weight: 0.3
  sparse_weight: 0.7
  rerank_top_n: 24
  remote_embeddings: false
```

Local-first mode uses fast sparse retrieval and optional local vector retrieval. Remote embeddings should only be enabled when a compatible embedding endpoint is configured.

## Answer Tuning

```yaml
answer:
  max_evidence: 4
  evidence_excerpt_chars: 220
```

Lower evidence count improves speed and readability. Higher count can improve coverage for complex questions.
