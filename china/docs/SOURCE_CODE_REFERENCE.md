# Source Code Reference

This document maps the source-code modules in AeroKB.

## Frontend

| File | Responsibility |
| --- | --- |
| `web/index.html` | Static page structure, chat composer, upload area, tree panel and controls |
| `web/app.js` | Application state, API calls, upload flow, session list, evidence graph rendering, knowledge tree rendering, voice controls, model selector |
| `web/style.css` | Layout, Apple/workbench-inspired styling, graph and evidence UI styles |

## Backend API Layer

| File | Responsibility |
| --- | --- |
| `src/backend/app.py` | FastAPI application factory, routes, upload handlers, export endpoints |
| `src/backend/service.py` | Main orchestration service: ingestion, retrieval, generation, sessions, knowledge graph, memory, model switching |
| `src/backend/utils.py` | Config loading and utility helpers |
| `src/backend/rule_memory.py` | Gbrain-style rule memory storage, merge and refresh logic |

## Model Providers

| File | Responsibility |
| --- | --- |
| `src/backend/providers/ollama.py` | Local Ollama connection, chat generation, embeddings, model list and model selection |
| `src/backend/providers/openai_compatible.py` | OpenAI-compatible API provider, chat generation, model listing and embeddings fallback |

## Retrieval

| File | Responsibility |
| --- | --- |
| `src/retrieval/bm25.py` | Sparse BM25-style retrieval |
| `src/retrieval/dense.py` | Dense vector retrieval and embedding fallback behavior |
| `src/retrieval/hybrid.py` | Hybrid retrieval coordination and score merging |
| `src/retrieval/reranker.py` | Lightweight heuristic reranking |
| `src/retrieval/routing.py` | Query routing and feature selection |

## Generation

| File | Responsibility |
| --- | --- |
| `src/generation/generator.py` | Evidence prompt construction, answer generation, answer cleaning, claim splitting, provenance matching, evidence graph creation |

## Ingestion

| File | Responsibility |
| --- | --- |
| `core/doc_parser.py` | Multi-format document parsing |
| `knowledge/ingestion/ingest_pipeline.py` | File ingestion, ZIP expansion, coarse/refined chunk creation, SQLite write path |
| `knowledge/ingestion/segmenter.py` | Semantic and token-aware segmentation |
| `knowledge/ingestion/extractor.py` | Entity/condition/relation extraction helpers |

## Agent and Export Capabilities

| File | Responsibility |
| --- | --- |
| `src/agentic/agentic_retrieval.py` | Optional multi-step agentic retrieval flow |
| `src/agentic/graph.yaml` | Agent graph configuration |
| `src/rlm/recursive_retrieval.py` | Optional recursive language model retrieval strategy |
| `src/rlm/repl_engine.py` | REPL-style execution support for recursive reasoning |
| `src/agent_capabilities/graph_export.py` | Knowledge graph SVG/PNG/HTML rendering |
| `src/agent_capabilities/word_report.py` | Word report generation |
| `src/agent_capabilities/rowboat_adapter.py` | Rowboat-inspired capability adapter |

## Data and Graph Code

| File | Responsibility |
| --- | --- |
| `knowledge/graph/graph_builder.py` | Graph artifact builder |
| `knowledge/graph/schema.yaml` | Graph schema |
| `knowledge/graph/graph.graphml` | Existing graph artifact |

## Design Notes

- The frontend is intentionally static. There is no React/Vue build step.
- The backend service is the main boundary for feature behavior.
- Providers should stay swappable.
- Retrieval and generation must preserve evidence provenance.
- Source code should not depend on private local absolute paths.
