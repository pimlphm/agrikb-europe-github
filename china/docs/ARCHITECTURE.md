# Architecture

## High-Level Flow

```text
User Upload
  -> Document Parser
  -> Ingestion Pipeline
  -> SQLite Chunk Store
  -> Hybrid Retriever
  -> Evidence-Grounded Generator
  -> Answer Claims + Evidence Graph
  -> Web UI Visualization
```

## Main Components

### Frontend

```text
web/index.html
web/app.js
web/style.css
```

The frontend is a static, build-free UI. It handles uploads, chat, history, dynamic graph rendering, evidence-chain visualization, speech controls and local model selection.

### Backend

```text
src/backend/app.py
src/backend/service.py
src/backend/utils.py
src/backend/rule_memory.py
```

The backend uses FastAPI. `app.py` defines routes. `service.py` orchestrates ingestion, retrieval, generation, session graphs, dynamic knowledge trees and model provider selection.

### Providers

```text
src/backend/providers/ollama.py
src/backend/providers/openai_compatible.py
```

Provider selection supports:

- local Ollama
- OpenAI-compatible remote API
- auto mode: prefer Ollama, fallback to API provider

### Ingestion

```text
knowledge/ingestion/
core/doc_parser.py
```

The ingestion pipeline parses documents, creates chunks, extracts lightweight metadata and writes to SQLite. Large uploads use background jobs and progressive status updates.

### Retrieval

```text
src/retrieval/
```

Hybrid retrieval combines sparse BM25 with optional dense retrieval and heuristic reranking. The default runtime favors speed and local operation.

### Generation

```text
src/generation/generator.py
```

The generator builds prompts from retrieved evidence, produces an answer, cleans citation markers from the answer body, splits the answer into claims, and assigns provenance.

### Session Memory

```text
knowledge/sessions/
```

Each browser session has a local session graph. Follow-up questions append to the graph instead of replacing it.

### Rule Memory

```text
knowledge/agent_memory/
```

Rule memory stores refined rules extracted from document-backed claims and evidence chains. It is designed to merge similar rules instead of accumulating noisy fragments.

## Knowledge Graph Model

Dynamic knowledge tree:

```text
root
  document
    topic / section
      chunk
        entity / keyword
```

Evidence graph:

```text
query
  entity
    retrieved_chunk
      answer_claim
```

Session graph:

```text
Q1 -> Evidence -> Claim -> Q2 -> Evidence -> Claim
```

## Provenance Rule

No model-generated statement should be presented as document evidence. If a claim cannot be matched to retrieved chunks, label it as `model_prior` or `unsupported`.
