from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from knowledge.ingestion.ingest_pipeline import IngestPipeline
from src.backend.providers.ollama import OllamaProvider
from src.backend.providers.openai_compatible import OpenAICompatibleProvider
from src.backend.providers.kimi_cli import KimiCliProvider
from src.backend.rule_memory import RuleMemoryStore
from src.backend.utils import ensure_dir, list_demo_documents, load_config
from src.backend.regional_intelligence import regional_intelligence_as_chunks
from src.backend.web_search import web_results_as_chunks
from src.generation.generator import EvidenceGroundedGenerator
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.routing import QueryRouter


class KnowledgeBaseService:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or load_config()
        self.provider = create_provider(self.config)
        retrieval_cfg = self.config.get("retrieval", {})
        flags = self.config.get("feature_flags", {})
        self.flags = flags

        self.chunk_dir = ensure_dir(self.config.get("storage", {}).get("chunk_dir", "./knowledge/chunks"))
        self.raw_dir = ensure_dir(self.config.get("storage", {}).get("raw_dir", "./data/raw"))
        self.processed_dir = ensure_dir(self.config.get("storage", {}).get("processed_dir", "./data/processed"))
        self.session_dir = ensure_dir(self.config.get("storage", {}).get("session_dir", "./knowledge/sessions"))
        agent_cfg = self.config.get("agent_capabilities", {})
        memory_dir = ensure_dir(agent_cfg.get("memory_dir", "./knowledge/agent_memory"))
        self.rule_memory = RuleMemoryStore(memory_dir / "gbrain_rules.json")

        self.pipeline = IngestPipeline(self.config)
        self.router = QueryRouter(self.config)
        self.retriever = HybridRetriever(
            provider=self.provider,
            dense_weight=retrieval_cfg.get("dense_weight", 0.45),
            sparse_weight=retrieval_cfg.get("sparse_weight", 0.55),
            dense_dim=retrieval_cfg.get("dense_embedding_dim", 128),
            dense_enabled=bool(flags.get("ENABLE_DENSE_RETRIEVAL", False) or flags.get("ENABLE_HYBRID_RETRIEVAL", False)),
            remote_embeddings=bool(retrieval_cfg.get("remote_embeddings", False)),
            reranker_enabled=bool(flags.get("ENABLE_RERANKER", False) or flags.get("ENABLE_HYBRID_RETRIEVAL", False)),
            dense_candidate_only=bool(retrieval_cfg.get("dense_candidate_only", True)),
            sparse_candidate_multiplier=int(retrieval_cfg.get("sparse_candidate_multiplier", 10) or 10),
        )
        self.generator = EvidenceGroundedGenerator(provider=self.provider, config=self.config)
        self._indexed_chunk_count = 0
        self._chunks_cache: list[dict] = []
        self._index_signature: tuple | None = None
        self._provider_available = self.provider.check_connection()
        self.refresh_indexes_from_disk()

    def has_chunks(self) -> bool:
        return self._indexed_chunk_count > 0 or any(self.chunk_dir.glob("*.json"))

    def ingest_paths(self, paths: list[str], progress_callback: Callable[[dict], None] | None = None) -> dict:
        summary = self.pipeline.ingest_paths(paths, progress_callback=progress_callback)
        self.refresh_indexes_from_disk()
        summary["rule_memory"] = self.rule_memory.refresh_from_chunks(self._chunks_cache, limit=900)
        return summary

    def ingest_coarse_paths(self, paths: list[str], progress_callback: Callable[[dict], None] | None = None) -> dict:
        summary = self.pipeline.ingest_coarse_paths(paths, progress_callback=progress_callback)
        self.refresh_indexes_from_disk()
        summary["knowledge_progress"] = self.get_knowledge_progress()
        return summary

    def ingest_documents(self, documents: list[dict], progress_callback: Callable[[dict], None] | None = None) -> dict:
        prepared = []
        for item in documents:
            prepared.append(
                {
                    "name": item["name"],
                    "path": item.get("path", item["name"]),
                    "ext": Path(item["name"]).suffix.lower() or ".txt",
                    "content": item.get("content", ""),
                    "size_kb": round(len(item.get("content", "").encode("utf-8")) / 1024, 2),
                }
            )
        summary = self.pipeline.ingest_document_payloads(prepared, progress_callback=progress_callback)
        self.refresh_indexes_from_disk()
        summary["rule_memory"] = self.rule_memory.refresh_from_chunks(self._chunks_cache, limit=900)
        return summary

    def refresh_indexes_from_disk(self) -> None:
        signature = self._current_index_signature()
        if signature == self._index_signature:
            return
        chunks = self._load_chunks_from_db()
        if not chunks:
            chunks = self._load_chunks_from_files()
        self._chunks_cache = chunks
        self._indexed_chunk_count = len(chunks)
        self.retriever.build(chunks)
        self._index_signature = signature

    def _current_index_signature(self) -> tuple:
        db_path = self.pipeline.db_path
        if db_path.exists():
            stat = db_path.stat()
            return ("db", stat.st_size, stat.st_mtime_ns)
        files = list(self.chunk_dir.glob("*.json"))
        if not files:
            return ("empty", 0, 0)
        newest = max((path.stat().st_mtime_ns for path in files), default=0)
        total_size = sum(path.stat().st_size for path in files)
        return ("json", len(files), total_size, newest)

    def _load_chunks_from_db(self) -> list[dict]:
        db_path = self.pipeline.db_path
        if not db_path.exists():
            return []
        try:
            with closing(sqlite3.connect(db_path)) as conn:
                rows = conn.execute(
                    """
                    SELECT chunk_id, doc_name, source, chunk_type, text,
                           entities_json, conditions_json, relations_json, metadata_json
                    FROM chunks
                    """
                ).fetchall()
        except sqlite3.Error:
            return []
        chunks = []
        for row in rows:
            chunk_id, doc_name, source, chunk_type, text, entities_json, conditions_json, relations_json, metadata_json = row
            metadata = self._json_or_default(metadata_json, {})
            if doc_name and "doc_name" not in metadata:
                metadata["doc_name"] = doc_name
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_type": chunk_type or "evidence",
                    "text": text or "",
                    "entities": self._json_or_default(entities_json, []),
                    "conditions": self._json_or_default(conditions_json, []),
                    "relations": self._json_or_default(relations_json, []),
                    "source": source or doc_name or "",
                    "metadata": metadata,
                }
            )
        return chunks

    def _load_chunks_from_files(self) -> list[dict]:
        chunks = []
        for path in sorted(self.chunk_dir.glob("*.json")):
            try:
                chunks.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return chunks

    @staticmethod
    def _json_or_default(value: str, default):
        try:
            parsed = json.loads(value or "")
        except (TypeError, json.JSONDecodeError):
            return default
        return parsed if parsed is not None else default

    def get_knowledge_tree(self) -> dict:
        documents: dict[str, dict] = {}
        type_nodes: dict[tuple[str, str], dict] = {}
        entity_counts: dict[tuple[str, str, str], int] = defaultdict(int)

        chunks = self._load_chunks_from_db() or self._chunks_cache or self._load_chunks_from_files()
        for chunk in chunks:

            metadata = chunk.get("metadata", {}) or {}
            doc_name = metadata.get("doc_name") or chunk.get("source") or "Unknown document"
            stem = Path(doc_name).stem
            doc_node = documents.setdefault(
                doc_name,
                {
                    "name": doc_name,
                    "kind": "document",
                    "chunk_count": 0,
                    "wiki_url": f"/wiki/{stem}.md",
                    "children": [],
                },
            )
            doc_node["chunk_count"] += 1

            chunk_type = chunk.get("chunk_type", "evidence")
            type_key = (doc_name, chunk_type)
            type_node = type_nodes.get(type_key)
            if type_node is None:
                type_node = {
                    "name": chunk_type,
                    "kind": "chunk_type",
                    "chunk_count": 0,
                    "children": [],
                }
                type_nodes[type_key] = type_node
                doc_node["children"].append(type_node)
            type_node["chunk_count"] += 1

            entities = chunk.get("entities") or ["unlabeled"]
            for entity in entities[:6]:
                entity_counts[(doc_name, chunk_type, entity)] += 1

            preview = chunk.get("text", "").replace("\n", " ")[:180]
            type_node["children"].append(
                {
                    "name": chunk.get("chunk_id") or f"{stem}_{type_node['chunk_count']:04d}",
                    "kind": "chunk",
                    "chunk_type": chunk_type,
                    "source": chunk.get("source", ""),
                    "preview": preview,
                    "entities": chunk.get("entities", []),
                }
            )

        for (doc_name, chunk_type, entity), count in entity_counts.items():
            type_node = type_nodes[(doc_name, chunk_type)]
            type_node["children"].insert(
                0,
                {
                    "name": entity,
                    "kind": "entity",
                    "chunk_count": count,
                },
            )

        return {
            "name": "Knowledge Base",
            "kind": "root",
            "document_count": len(documents),
            "chunk_count": sum(node["chunk_count"] for node in documents.values()),
            "children": sorted(documents.values(), key=lambda item: item["name"]),
        }

    def get_dynamic_knowledge_tree(self, limit: int | None = None, doc_id: str = "", q: str = "") -> dict:
        chunks = self._filter_chunks(self._load_chunks_from_db() or self._chunks_cache or self._load_chunks_from_files(), doc_id, q)
        if limit:
            chunks = chunks[: max(1, int(limit))]

        generated_at = self._now_iso()
        docs: dict[str, dict] = {}
        topics: dict[tuple[str, str], dict] = {}
        entity_count = 0

        root = self._tree_node("root", "root", "Knowledge Base", source_type="document")
        root.update({"generated_at": generated_at, "document_count": 0, "chunk_count": len(chunks)})

        for chunk in chunks:
            metadata = chunk.get("metadata", {}) or {}
            doc_name = metadata.get("doc_name") or chunk.get("source") or "Unknown document"
            doc_id_value = str(metadata.get("doc_id") or Path(doc_name).stem)
            doc_node = docs.get(doc_id_value)
            if doc_node is None:
                doc_node = self._tree_node(
                    f"doc:{self._stable_id(doc_id_value)}",
                    "document",
                    doc_name,
                    doc_id=doc_id_value,
                    file_name=doc_name,
                    source_type="document",
                    wiki_url=f"/wiki/{Path(doc_name).stem}.md",
                )
                doc_node["children"] = []
                doc_node["chunk_count"] = 0
                docs[doc_id_value] = doc_node
                root["children"].append(doc_node)
            doc_node["chunk_count"] += 1

            topic_label = self._topic_for_chunk(chunk)
            topic_key = (doc_id_value, topic_label)
            topic_node = topics.get(topic_key)
            if topic_node is None:
                topic_node = self._tree_node(
                    f"topic:{self._stable_id(doc_id_value + ':' + topic_label)}",
                    "topic",
                    topic_label,
                    doc_id=doc_id_value,
                    file_name=doc_name,
                    section=topic_label,
                    source_type="document",
                )
                topic_node["children"] = []
                topic_node["chunk_count"] = 0
                topics[topic_key] = topic_node
                doc_node["children"].append(topic_node)
            topic_node["chunk_count"] += 1

            chunk_id = str(chunk.get("chunk_id") or self._stable_id(chunk.get("text", "")[:80]))
            chunk_node = self._tree_node(
                f"chunk:{self._stable_id(chunk_id)}",
                "chunk",
                self._chunk_label(chunk),
                doc_id=doc_id_value,
                file_name=doc_name,
                page=metadata.get("page"),
                section=topic_label,
                chunk_id=chunk_id,
                source_type="document",
                preview=self._excerpt(chunk.get("text", ""), 220),
                score=None,
                stage=metadata.get("stage", "refined"),
                refinement_status=metadata.get("refinement_status", "complete"),
            )
            chunk_node["children"] = []
            topic_node["children"].append(chunk_node)

            for keyword in self._entities_for_chunk(chunk)[:8]:
                entity_count += 1
                entity_node = self._tree_node(
                    f"entity:{self._stable_id(doc_id_value + ':' + chunk_id + ':' + keyword)}",
                    "entity",
                    keyword,
                    doc_id=doc_id_value,
                    file_name=doc_name,
                    page=metadata.get("page"),
                    section=topic_label,
                    chunk_id=chunk_id,
                    source_type="document",
                    preview="document entity / keyword",
                )
                chunk_node["children"].append(entity_node)

        root["children"].sort(key=lambda item: (-(item.get("chunk_count") or 0), item.get("label", "")))
        root["document_count"] = len(docs)
        stats = {
            "documents": len(docs),
            "sections": len(topics),
            "chunks": len(chunks),
            "entities": entity_count,
        }
        return {
            "generated_at": generated_at,
            "stats": stats,
            "root": root,
            "source_types": self.source_type_schema(),
            "knowledge_progress": self.get_knowledge_progress(chunks),
            "focus_query": q or "",
        }

    def get_knowledge_graph(self, limit: int = 300, doc_id: str = "", q: str = "", full: bool = False) -> dict:
        chunks = self._filter_chunks(self._load_chunks_from_db() or self._chunks_cache or self._load_chunks_from_files(), doc_id, q)
        if not full:
            chunks = chunks[: max(1, int(limit or 300))]

        nodes: dict[str, dict] = {}
        edges: dict[str, dict] = {}

        def add_node(node: dict) -> None:
            nodes.setdefault(node["id"], node)

        def add_edge(source: str, target: str, edge_type: str) -> None:
            edge_id = f"{edge_type}:{source}->{target}"
            edges.setdefault(edge_id, {"id": edge_id, "source": source, "target": target, "type": edge_type})

        add_node({"id": "root", "type": "root", "label": "Knowledge Base", "source_type": "document", "meta": {}})
        for chunk in chunks:
            metadata = chunk.get("metadata", {}) or {}
            doc_name = metadata.get("doc_name") or chunk.get("source") or "Unknown document"
            doc_id_value = str(metadata.get("doc_id") or Path(doc_name).stem)
            topic_label = self._topic_for_chunk(chunk)
            chunk_id = str(chunk.get("chunk_id") or self._stable_id(chunk.get("text", "")[:80]))
            doc_node_id = f"doc:{self._stable_id(doc_id_value)}"
            topic_node_id = f"topic:{self._stable_id(doc_id_value + ':' + topic_label)}"
            chunk_node_id = f"chunk:{self._stable_id(chunk_id)}"
            add_node(
                {
                    "id": doc_node_id,
                    "type": "document",
                    "label": doc_name,
                    "source_type": "document",
                    "meta": {"doc_id": doc_id_value, "file_name": doc_name},
                }
            )
            add_node(
                {
                    "id": topic_node_id,
                    "type": "topic",
                    "label": topic_label,
                    "source_type": "document",
                    "meta": {"doc_id": doc_id_value, "file_name": doc_name, "section": topic_label},
                }
            )
            add_node(
                {
                    "id": chunk_node_id,
                    "type": "chunk",
                    "label": chunk_id,
                    "source_type": "document",
                    "meta": {
                        "doc_id": doc_id_value,
                        "file_name": doc_name,
                        "chunk_id": chunk_id,
                        "section": topic_label,
                        "page": metadata.get("page"),
                        "raw_text": self._excerpt(chunk.get("text", ""), 360),
                        "stage": metadata.get("stage", "refined"),
                        "refinement_status": metadata.get("refinement_status", "complete"),
                    },
                }
            )
            add_edge("root", doc_node_id, "contains")
            add_edge(doc_node_id, topic_node_id, "contains")
            add_edge(topic_node_id, chunk_node_id, "contains")
            for keyword in self._entities_for_chunk(chunk)[:8]:
                entity_id = f"entity:{self._stable_id(keyword.lower())}"
                add_node(
                    {
                        "id": entity_id,
                        "type": "entity",
                        "label": keyword,
                        "source_type": "document",
                        "meta": {"keyword": keyword},
                    }
                )
                add_edge(chunk_node_id, entity_id, "mentions")

        return {
            "generated_at": self._now_iso(),
            "stats": {
                "nodes": len(nodes),
                "edges": len(edges),
                "chunks_considered": len(chunks),
                "limited": not full,
            },
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "source_types": self.source_type_schema(),
            "knowledge_progress": self.get_knowledge_progress(chunks),
            "focus_query": q or "",
        }

    def get_knowledge_progress(self, chunks: list[dict] | None = None) -> dict:
        chunks = chunks if chunks is not None else (self._load_chunks_from_db() or self._chunks_cache or self._load_chunks_from_files())
        docs: dict[str, dict] = {}
        coarse_chunks = 0
        refined_chunks = 0
        for chunk in chunks:
            metadata = chunk.get("metadata", {}) or {}
            doc_name = metadata.get("doc_name") or chunk.get("source") or "Unknown document"
            doc_id_value = str(metadata.get("doc_id") or Path(doc_name).stem)
            stage = str(metadata.get("stage") or ("coarse" if chunk.get("chunk_type") == "coarse_outline" else "refined"))
            info = docs.setdefault(doc_id_value, {"doc_id": doc_id_value, "file_name": doc_name, "coarse": False, "refined": False})
            if stage == "coarse" or chunk.get("chunk_type") == "coarse_outline":
                info["coarse"] = True
                coarse_chunks += 1
            else:
                info["refined"] = True
                refined_chunks += 1
        total_docs = len(docs)
        coarse_docs = sum(1 for item in docs.values() if item["coarse"])
        refined_docs = sum(1 for item in docs.values() if item["refined"])
        if total_docs and refined_docs < total_docs:
            stage = "refining" if refined_docs else "coarse_ready"
        else:
            stage = "refined" if total_docs else "empty"
        return {
            "stage": stage,
            "documents_total": total_docs,
            "documents_coarse": coarse_docs,
            "documents_refined": refined_docs,
            "chunks_total": len(chunks),
            "chunks_coarse": coarse_chunks,
            "chunks_refined": refined_chunks,
            "coverage": round(refined_docs / total_docs, 3) if total_docs else 0.0,
            "partial_answer_allowed": bool(total_docs),
        }

    def source_type_schema(self) -> dict:
        return {
            "document": "来自当前知识库文档 chunk 的证据",
            "web_search": "来自真实联网搜索结果；未配置搜索时不会伪造",
            "model_prior": "来自模型内置知识或通用推理，不是文档证据",
            "inferred": "由多个文档证据综合推理得到",
            "unsupported": "没有可靠证据支持或证据不足",
        }

    def refresh_provider_status(self) -> bool:
        self._provider_available = self.provider.check_connection()
        return self._provider_available

    def active_model_name(self) -> str:
        model = getattr(self.provider, "model", "") or ""
        if model:
            return str(model)
        backend = str(self.config.get("backend", "ollama")).lower()
        if backend == "kimi_cli":
            return self.config.get("kimi_cli", {}).get("model") or self.config.get("openai_compatible", {}).get("model", "kimi-for-coding")
        if backend in {"openai", "openai_compatible", "api_key"}:
            return self.config.get("openai_compatible", {}).get("model", "unknown")
        return self.config.get("ollama", {}).get("model", "unknown")

    def get_model_status(self) -> dict:
        ollama_provider = self.provider if isinstance(self.provider, OllamaProvider) else OllamaProvider(self.config)
        models = ollama_provider.list_models()
        ollama_available = bool(models) or ollama_provider.check_connection()
        active_model = self.active_model_name()
        return {
            "backend": self.config.get("backend", "ollama"),
            "active_provider": self.provider.__class__.__name__,
            "active_model": active_model,
            "provider_available": self._provider_available,
            "ollama_available": ollama_available,
            "can_select": bool(models),
            "models": models,
        }

    def select_ollama_model(self, model: str) -> dict:
        chosen = str(model or "").strip()
        if not chosen:
            raise ValueError("请选择一个本地模型。")

        ollama_provider = self.provider if isinstance(self.provider, OllamaProvider) else OllamaProvider(self.config)
        models = ollama_provider.list_models()
        available_names = {item.get("name") for item in models if item.get("name")}
        if not available_names:
            raise RuntimeError("未检测到可用的本地 Ollama 模型。")
        if chosen not in available_names:
            raise ValueError(f"本地模型不存在：{chosen}")

        self.config["backend"] = "ollama"
        self.config.setdefault("ollama", {})["model"] = chosen
        ollama_provider.set_model(chosen)
        self.provider = ollama_provider
        self.generator = EvidenceGroundedGenerator(provider=self.provider, config=self.config)
        if getattr(self.retriever, "dense", None) is not None:
            self.retriever.dense.provider = self.provider
        self._provider_available = self.provider.check_connection()
        return self.get_model_status()

    def apply_runtime_settings(self, settings: dict) -> dict:
        backend = str(settings.get("backend") or "").strip().lower()
        if backend:
            allowed = {"auto", "kimi_cli", "openai_compatible", "ollama"}
            if backend not in allowed:
                raise ValueError(f"不支持的模型后端：{backend}")
            self.config["backend"] = backend

        base_url = str(settings.get("base_url") or "").strip()
        model = str(settings.get("model") or "").strip()
        api_key = str(settings.get("api_key") or "").strip()
        frontend_base_url = str(settings.get("frontend_base_url") or "").strip()
        frontend_model = str(settings.get("frontend_model") or "").strip()
        frontend_api_key = str(settings.get("frontend_api_key") or "").strip()
        ollama_model = str(settings.get("ollama_model") or "").strip()
        kimi_executable = str(settings.get("kimi_executable") or "").strip()

        openai_cfg = self.config.setdefault("openai_compatible", {})
        kimi_cfg = self.config.setdefault("kimi_cli", {})
        frontend_cfg = self.config.setdefault("frontend_api", {})
        ollama_cfg = self.config.setdefault("ollama", {})
        if base_url:
            openai_cfg["base_url"] = base_url
            kimi_cfg["base_url"] = base_url
        if model:
            openai_cfg["model"] = model
            kimi_cfg["model"] = model
        if api_key:
            openai_cfg["api_key"] = api_key
            kimi_cfg["api_key"] = api_key
        if kimi_executable:
            kimi_cfg["executable"] = kimi_executable
        if frontend_base_url:
            frontend_cfg["base_url"] = frontend_base_url
        if frontend_model:
            frontend_cfg["model"] = frontend_model
        if frontend_api_key:
            frontend_cfg["api_key"] = frontend_api_key
        if ollama_model:
            ollama_cfg["model"] = ollama_model

        self.provider = create_provider(self.config)
        self.generator = EvidenceGroundedGenerator(provider=self.provider, config=self.config)
        if getattr(self.retriever, "dense", None) is not None:
            self.retriever.dense.provider = self.provider
        self._provider_available = self.provider.check_connection()
        return self.get_model_status()

    def retrieve(self, query: str, top_k: int | None = None) -> dict:
        if not self.has_chunks():
            demo_docs = list_demo_documents()
            if demo_docs:
                self.ingest_paths(demo_docs)

        top_k = top_k or self.config.get("retrieval", {}).get("top_k", 8)
        route = self.router.route(query)
        results = self.retriever.search(
            query,
            top_k=top_k,
            rerank_top_n=self.config.get("retrieval", {}).get("rerank_top_n", 12),
            min_score=self.config.get("retrieval", {}).get("min_score", 0.0),
        )
        return {
            "query": query,
            "route": route.to_dict(),
            "retrieval_results": results,
            "indexed_chunk_count": self._indexed_chunk_count,
        }

    def generate(
        self,
        query: str,
        top_k: int | None = None,
        use_llm: bool | None = None,
        retrieval_query: str | None = None,
        conversation_context: str = "",
        model: str | None = None,
        answer_language: str = "auto",
        web_results: list[dict] | None = None,
        regional_intelligence: dict | None = None,
        module_context: str = "",
    ) -> dict:
        selected_model = ""
        if model:
            selected_model = self.select_ollama_model(model).get("active_model", "")
        route = self.router.route(query)

        if route.use_rlm:
            from src.rlm.recursive_retrieval import RecursiveRetrievalEngine

            try:
                rlm_engine = RecursiveRetrievalEngine(self, config=self.config)
                rlm_result = rlm_engine.run(query, top_k=top_k)
                result = rlm_result.to_dict()
                evidence_chain = self.generator._build_evidence_chain(result.get("evidence_chunks", []))
                result["answer"] = self.generator.clean_answer_text(result.get("answer", ""))
                result["answer_claims"] = self.generator.build_answer_claims(result["answer"], evidence_chain)
                result["evidence_chain"] = evidence_chain
                result["evidence"] = self.generator.evidence_for_api(evidence_chain)
                result["evidence_graph"] = self.generator.build_evidence_graph(query, evidence_chain, result["answer"], result["answer_claims"])
                result["route"] = route.to_dict()
                result["llm_used"] = True
                result["agentic_used"] = False
                result["rlm_used"] = True
                result["selected_model"] = selected_model or self.active_model_name()
                return result
            except Exception:
                # RLM can make several nested model calls. If the external model is slow,
                # fall back to the normal evidence-grounded path so the UI still answers.
                pass

        if route.use_agentic:
            from src.agentic.agentic_retrieval import AgenticRetrievalEngine

            result = AgenticRetrievalEngine(self).run(
                query,
                max_steps=self.config.get("agentic", {}).get("max_steps", 3),
            )
            result["route"] = route.to_dict()
            result["llm_used"] = False
            result["agentic_used"] = True
            result["rlm_used"] = False
            evidence_chain = result.get("evidence_chain") or result.get("evidence") or []
            result["answer"] = self.generator.clean_answer_text(result.get("answer", ""))
            result["answer_claims"] = self.generator.build_answer_claims(result["answer"], evidence_chain)
            result.setdefault("evidence_graph", self.generator.build_evidence_graph(query, evidence_chain, result["answer"], result["answer_claims"]))
            result["selected_model"] = selected_model or self.active_model_name()
            return result

        retrieval = self.retrieve(retrieval_query or query, top_k=top_k)
        regional_chunks = []
        web_chunks = []
        if regional_intelligence:
            regional_chunks = regional_intelligence_as_chunks(regional_intelligence)
        if web_results:
            web_chunks = web_results_as_chunks(web_results)
        module_chunks = self._module_context_as_chunks(module_context)
        if module_chunks or regional_chunks or web_chunks:
            retrieval["retrieval_results"] = module_chunks + regional_chunks + retrieval.get("retrieval_results", []) + web_chunks
        strict_api_backend = isinstance(self.provider, (OpenAICompatibleProvider, KimiCliProvider)) and str(self.config.get("backend", "")).lower() in {
            "openai",
            "openai_compatible",
            "api_key",
            "kimi_cli",
        }
        if use_llm is None:
            llm_allowed = bool(self.provider) if strict_api_backend else self._provider_available
        else:
            llm_allowed = bool(use_llm) and (strict_api_backend or self._provider_available)
        generated = self.generator.generate(
            query,
            retrieval["retrieval_results"],
            use_llm=llm_allowed,
            conversation_context=conversation_context,
            model=selected_model or None,
            answer_language=answer_language,
        )
        retrieval.update(generated)
        retrieval["query"] = query
        if retrieval_query and retrieval_query != query:
            retrieval["retrieval_query"] = retrieval_query
        if regional_intelligence:
            retrieval["regional_intelligence"] = regional_intelligence
        retrieval["llm_used"] = llm_allowed
        retrieval["agentic_used"] = False
        retrieval["rlm_used"] = False
        retrieval["knowledge_progress"] = self.get_knowledge_progress()
        retrieval["selected_model"] = selected_model or self.active_model_name()
        return retrieval

    def query(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int | None = None,
        use_llm: bool | None = None,
        model: str | None = None,
        answer_language: str = "auto",
        web_results: list[dict] | None = None,
        regional_intelligence: dict | None = None,
        module_context: str = "",
    ) -> dict:
        session_id = session_id or uuid.uuid4().hex
        query_id = f"q_{uuid.uuid4().hex[:12]}"
        session = self._read_session_graph(session_id)
        conversation_context = self._session_context_for_prompt(session)
        retrieval_query = self._contextual_retrieval_query(query, session)
        result = self.generate(
            query,
            top_k=top_k,
            use_llm=use_llm,
            retrieval_query=retrieval_query,
            conversation_context=conversation_context,
            model=model,
            answer_language=answer_language,
            web_results=web_results,
            regional_intelligence=regional_intelligence,
            module_context=module_context,
        )
        result["session_id"] = session_id
        result["query_id"] = query_id
        result["source_types"] = self.source_type_schema()
        result["knowledge_progress"] = self.get_knowledge_progress()
        result["focused_knowledge_tree"] = self.get_question_focused_tree(query, result)
        result["session_evidence_graph"] = self._append_session_graph(session_id, query_id, query, result)
        result["memory_rules"] = self.rule_memory.update_from_query(query, result)
        return result

    def _module_context_as_chunks(self, module_context: str = "") -> list[dict]:
        text = str(module_context or "").strip()
        if not text:
            return []
        return [
            {
                "chunk_id": f"module_context_{uuid.uuid4().hex[:10]}",
                "doc_name": "当前页面模块聚合信息",
                "source": "AgriKB 当前界面",
                "chunk_type": "module_context",
                "source_type": "live_context",
                "text": text[:3000],
                "score": 0.92,
                "entities": ["当前模块", "实时聚合", "江苏句容"],
                "metadata": {
                    "doc_name": "当前页面模块聚合信息",
                    "source_type": "live_context",
                    "source_path": "AgriKB 当前界面",
                },
            }
        ]

    def get_question_focused_tree(self, query: str, result: dict | None = None, limit: int = 80) -> dict:
        chunks = self._filter_chunks(self._load_chunks_from_db() or self._chunks_cache or self._load_chunks_from_files(), q=query)
        if limit:
            chunks = chunks[:limit]
        root = self._tree_node(
            f"focus:{self._stable_id(query)}",
            "analysis",
            "Question focus",
            source_type="inferred",
            preview=self._excerpt(query, 180),
        )
        root["chunk_count"] = len(chunks)
        root["children"] = [
            self._tree_node(
                "focus:query",
                "topic",
                self._excerpt(query, 72) or "Current question",
                source_type="inferred",
                preview=query,
            )
        ]
        docs: dict[str, dict] = {}
        for chunk in chunks:
            metadata = chunk.get("metadata", {}) or {}
            doc_name = metadata.get("doc_name") or chunk.get("source") or "Unknown document"
            doc_id_value = str(metadata.get("doc_id") or Path(doc_name).stem)
            doc_node = docs.get(doc_id_value)
            if doc_node is None:
                doc_node = self._tree_node(
                    f"focus:doc:{self._stable_id(doc_id_value)}",
                    "document",
                    doc_name,
                    doc_id=doc_id_value,
                    file_name=doc_name,
                    source_type="document",
                    preview="Focused document branch",
                )
                doc_node["chunk_count"] = 0
                doc_node["children"] = []
                docs[doc_id_value] = doc_node
                root["children"].append(doc_node)
            doc_node["chunk_count"] += 1
            chunk_id = str(chunk.get("chunk_id") or self._stable_id(chunk.get("text", "")[:80]))
            doc_node["children"].append(
                self._tree_node(
                    f"focus:chunk:{self._stable_id(chunk_id)}",
                    "chunk",
                    self._chunk_label(chunk),
                    doc_id=doc_id_value,
                    file_name=doc_name,
                    chunk_id=chunk_id,
                    section=self._topic_for_chunk(chunk),
                    source_type="document",
                    preview=self._excerpt(chunk.get("text", ""), 260),
                    stage=metadata.get("stage", "refined"),
                    refinement_status=metadata.get("refinement_status", "complete"),
                )
            )
        for claim in (result or {}).get("answer_claims", [])[:4]:
            root["children"].append(
                self._tree_node(
                    f"focus:claim:{self._stable_id(claim.get('text', ''))}",
                    "answer_claim",
                    self._excerpt(claim.get("text", ""), 76) or "Answer claim",
                    source_type=claim.get("source_type", "inferred"),
                    preview=claim.get("warning") or claim.get("text", ""),
                )
            )
        return root

    def list_sessions(self, limit: int = 80) -> dict:
        sessions = []
        for path in sorted(self.session_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                session = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            turns = session.get("turns", []) if isinstance(session.get("turns"), list) else []
            sessions.append(
                {
                    "session_id": session.get("session_id") or path.stem,
                    "title": session.get("title") or self._session_title_from_turns(turns),
                    "updated_at": session.get("updated_at", ""),
                    "created_at": session.get("created_at", ""),
                    "turn_count": len(turns),
                    "summary": session.get("summary", ""),
                    "preview": self._excerpt((turns[-1].get("query", "") if turns else session.get("summary", "")), 120),
                    "temporary_memory_count": len(session.get("temporary_memory", []) or []),
                }
            )
            if len(sessions) >= limit:
                break
        return {"count": len(sessions), "sessions": sessions}

    def clear_sessions(self) -> dict:
        deleted = self._delete_files(self.session_dir, ["*.json"])
        return {"deleted": deleted, "sessions": []}

    def get_rule_memory(self, query: str = "", limit: int = 80) -> dict:
        return self.rule_memory.as_payload(query=query, limit=limit)

    def refresh_rule_memory(self, reset: bool = False, limit: int = 900) -> dict:
        chunks = self._load_chunks_from_db() or self._chunks_cache or self._load_chunks_from_files()
        return self.rule_memory.refresh_from_chunks(chunks, reset=reset, limit=limit)

    def clear_rule_memory(self) -> dict:
        return self.rule_memory.clear()

    def interpret_rule_memory(self, rule_id: str, context: str = "", persist: bool = False, answer_language: str = "auto") -> dict:
        rule = self.rule_memory.get_rule(rule_id)
        if not rule:
            raise ValueError("规则不存在或已被清空。")
        interpretation, prompt = self._build_rule_interpretation(rule, context=context, answer_language=answer_language)
        if persist:
            payload = self.rule_memory.save_interpretation(rule_id, interpretation)
            rule = self.rule_memory.get_rule(rule_id) or rule
            return {"rule": rule, "interpretation": interpretation, "prompt": prompt, "persisted": True, "memory_rules": payload}
        return {"rule": rule, "interpretation": interpretation, "prompt": prompt, "persisted": False}

    def persist_rule_interpretation(self, rule_id: str, interpretation: dict) -> dict:
        payload = self.rule_memory.save_interpretation(rule_id, interpretation)
        rule = self.rule_memory.get_rule(rule_id)
        return {"rule": rule, "interpretation": rule.get("latest_ai_interpretation") if rule else interpretation, "persisted": True, "memory_rules": payload}

    def _build_rule_interpretation(self, rule: dict, context: str = "", answer_language: str = "auto") -> tuple[dict, str]:
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "farmer_action": {"type": "string"},
                "why": {"type": "string"},
                "when_to_use": {"type": "string"},
                "action_steps": {"type": "array", "items": {"type": "string"}},
                "policy_market_weather_links": {"type": "array", "items": {"type": "string"}},
                "risk_boundary": {"type": "string"},
                "next_data_to_collect": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "farmer_action", "why", "when_to_use", "action_steps", "risk_boundary"],
        }
        prompt = "\n".join(
            [
                self._rule_language_instruction(rule, context, answer_language),
                "请把下面这条农业经营规则解读成可执行判断，面向新农人、农业管理部门和收购企业都能理解。",
                "不要输出后台技术词，不要使用歧视性表达。",
                "重点说明：这条规则为什么成立、什么时候用、今天该怎么做、需要结合哪些政策/市场/天气信息、边界和风险是什么。",
                "",
                f"规则ID：{rule.get('id', '')}",
                f"规则正文：{rule.get('text', '')}",
                f"已有说明：{rule.get('plain_explanation', '')}",
                f"做法：{'; '.join(map(str, rule.get('action_steps') or []))}",
                f"适用条件：{rule.get('applicable_conditions', '')}",
                f"风险提醒：{rule.get('risk_warning', '')}",
                f"依据边界：{rule.get('boundary', '')}",
                f"关键词：{', '.join(map(str, rule.get('keywords') or []))}",
                f"当前场景：{context or '江苏句容农业生产经营、政策、市场、天气、收购和物流场景'}",
            ]
        )
        fallback = self._fallback_rule_interpretation(rule, context, answer_language=answer_language)
        try:
            interpretation = self.provider.structured_output(
                prompt,
                schema,
                system=f"你是新农人助手的农业规则解读器。只返回 JSON，内容要清晰、可执行、可沉淀。{self._rule_language_instruction(rule, context, answer_language)}",
            )
        except Exception:
            interpretation = fallback
        if not isinstance(interpretation, dict):
            interpretation = fallback
        for key, value in fallback.items():
            interpretation.setdefault(key, value)
        interpretation["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        interpretation["provider"] = "新农人助手"
        interpretation["rule_id"] = rule.get("id", "")
        return interpretation, prompt

    def _rule_language_instruction(self, rule: dict, context: str = "", answer_language: str = "auto") -> str:
        mode = str(answer_language or "auto").strip().lower()
        if mode in {"zh", "zh-cn", "chinese", "中文"}:
            return "输出语言：简体中文。"
        if mode in {"en", "english", "英文"}:
            return "Output language: English. Keep Chinese place names or policy names when they are proper nouns."
        text = " ".join([str(rule.get("text") or ""), str(rule.get("plain_explanation") or ""), str(context or "")])
        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        latin_words = len(re.findall(r"\b[A-Za-z][A-Za-z-]{2,}\b", text))
        if latin_words >= 6 and latin_words > cjk:
            return "Output language: English, because the rule/context is mainly English."
        return "输出语言：自动判断上下文；中文场景用简体中文，英文场景用英文。"

    def _fallback_rule_interpretation(self, rule: dict, context: str = "", answer_language: str = "auto") -> dict:
        steps = rule.get("action_steps") if isinstance(rule.get("action_steps"), list) else []
        if self._rule_prefers_english(rule, context, answer_language):
            return {
                "summary": rule.get("plain_explanation") or rule.get("text") or "This rule supports agricultural business decisions.",
                "farmer_action": (steps or [rule.get("heuristic") or rule.get("text") or "Verify field conditions before acting."])[0],
                "why": rule.get("plain_explanation") or "The rule comes from the local knowledge base and accumulated operating experience, so it can turn complex signals into an action check.",
                "when_to_use": rule.get("applicable_conditions") or rule.get("decision_trigger") or "Use it when a similar crop, weather, market, policy, or procurement issue appears.",
                "action_steps": steps or ["Check the trigger conditions", "Review policy, price, weather, and procurement information", "Act in stages according to risk level"],
                "policy_market_weather_links": ["Check the latest policy notice", "Check market price and procurement channels", "Check today's and upcoming weather risks"],
                "risk_boundary": rule.get("risk_warning") or rule.get("boundary") or "This rule does not replace on-site verification; prices, subsidies, and weather must follow the latest public information.",
                "next_data_to_collect": ["Operator profile", "Crop category and batch", "Current price", "Weather alert", "Policy materials"],
            }
        return {
            "summary": rule.get("plain_explanation") or rule.get("text") or "这条规则用于辅助农业经营判断。",
            "farmer_action": (steps or [rule.get("heuristic") or rule.get("text") or "先核对现场条件，再安排生产经营动作。"])[0],
            "why": rule.get("plain_explanation") or "该规则来自知识库资料和历史经验沉淀，可帮助把复杂信息转成行动判断。",
            "when_to_use": rule.get("applicable_conditions") or rule.get("decision_trigger") or "遇到相似作物、天气、市场、政策或收购问题时使用。",
            "action_steps": steps or [rule.get("heuristic") or "核对条件", "查看政策、行情和天气", "按风险大小安排采收、销售或申报"],
            "policy_market_weather_links": ["同步查看政策通知", "同步查看市场行情和收购渠道", "同步查看当天及未来天气风险"],
            "risk_boundary": rule.get("risk_warning") or rule.get("boundary") or "规则不能替代现场核验；价格、补贴和天气以最新公开信息为准。",
            "next_data_to_collect": ["主体信息", "作物品类和批次", "实时价格", "天气预警", "政策材料"],
        }

    def _rule_prefers_english(self, rule: dict, context: str = "", answer_language: str = "auto") -> bool:
        mode = str(answer_language or "auto").strip().lower()
        if mode in {"en", "english", "英文"}:
            return True
        if mode in {"zh", "zh-cn", "chinese", "中文"}:
            return False
        text = " ".join([str(rule.get("text") or ""), str(rule.get("plain_explanation") or ""), str(context or "")])
        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        latin_words = len(re.findall(r"\b[A-Za-z][A-Za-z-]{2,}\b", text))
        return latin_words >= 6 and latin_words > cjk

    def reset_knowledge_tree(
        self,
        include_raw: bool = False,
        clear_sessions: bool = True,
        clear_rules: bool = True,
    ) -> dict:
        deleted = {
            "chunk_files": self._delete_files(self.chunk_dir, ["*.json"]),
            "wiki_pages": self._delete_files(self.pipeline.wiki_dir, ["*.md"]),
            "processed_files": self._delete_tree_contents(self.processed_dir),
            "sessions": self._delete_files(self.session_dir, ["*.json"]) if clear_sessions else 0,
            "raw_files": 0,
            "upload_temp_dirs": 0,
            "chunk_db": False,
            "rule_memory_cleared": False,
        }

        temp_upload = self.raw_dir / ".upload_chunks"
        if temp_upload.exists():
            deleted["upload_temp_dirs"] = self._delete_tree_contents(temp_upload, remove_root=True)
        if include_raw:
            deleted["raw_files"] = self._delete_tree_contents(self.raw_dir)
            self.raw_dir.mkdir(parents=True, exist_ok=True)

        if self.pipeline.db_path.exists():
            self.pipeline.db_path.unlink()
            deleted["chunk_db"] = True
        self.pipeline._init_db()

        if clear_rules:
            self.rule_memory.clear()
            deleted["rule_memory_cleared"] = True

        self.refresh_indexes_from_disk()
        tree = self.get_dynamic_knowledge_tree()
        return {
            "reset": True,
            "include_raw": include_raw,
            "deleted": deleted,
            "indexed_chunk_count": self._indexed_chunk_count,
            "tree": tree,
        }

    def get_session_evidence_graph(self, session_id: str) -> dict:
        return self._read_session_graph(session_id)

    def clear_session(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return {"session_id": session_id, "deleted": True}
        return {"session_id": session_id, "deleted": False}

    def _delete_files(self, directory: Path, patterns: list[str]) -> int:
        if not directory.exists():
            return 0
        count = 0
        for pattern in patterns:
            for path in directory.glob(pattern):
                if path.is_file():
                    path.unlink()
                    count += 1
        return count

    def _delete_tree_contents(self, directory: Path, remove_root: bool = False) -> int:
        if not directory.exists():
            return 0
        count = 0
        for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_file():
                path.unlink()
                count += 1
            elif path.is_dir():
                try:
                    path.rmdir()
                    count += 1
                except OSError:
                    pass
        if remove_root and directory.exists():
            try:
                directory.rmdir()
                count += 1
            except OSError:
                pass
        return count

    def _append_session_graph(self, session_id: str, query_id: str, query: str, result: dict) -> dict:
        session = self._read_session_graph(session_id)
        graph = result.get("evidence_graph") or {"nodes": [], "edges": []}
        id_map: dict[str, str] = {}
        existing_ids = {node.get("id") for node in session.get("nodes", [])}
        for node in graph.get("nodes", []):
            local_id = str(node.get("id", uuid.uuid4().hex))
            global_id = f"{query_id}:{local_id}"
            id_map[local_id] = global_id
            cloned = dict(node)
            cloned["id"] = global_id
            cloned["query_id"] = query_id
            cloned["session_id"] = session_id
            if local_id == "q" or cloned.get("type") == "query":
                cloned["id"] = query_id
                id_map[local_id] = query_id
                cloned["detail"] = query
                cloned["label"] = "用户问题"
            if cloned["id"] not in existing_ids:
                session["nodes"].append(cloned)
                existing_ids.add(cloned["id"])

        for edge in graph.get("edges", []):
            source = id_map.get(str(edge.get("source", "")))
            target = id_map.get(str(edge.get("target", "")))
            if not source or not target:
                continue
            edge_id = f"{query_id}:{edge.get('type', 'edge')}:{source}->{target}"
            session["edges"].append({"id": edge_id, "source": source, "target": target, "type": edge.get("type", "related_to")})

        previous_anchor = session.get("last_anchor_id")
        if previous_anchor:
            session["edges"].append(
                {
                    "id": f"follow_up:{previous_anchor}->{query_id}",
                    "source": previous_anchor,
                    "target": query_id,
                    "type": "follow_up",
                }
            )

        claim_ids = [
            node.get("id")
            for node in session.get("nodes", [])
            if node.get("query_id") == query_id and node.get("type") == "answer_claim"
        ]
        session["last_anchor_id"] = claim_ids[-1] if claim_ids else query_id
        session["turns"].append(
            {
                "query_id": query_id,
                "query": query,
                "answer": result.get("answer", ""),
                "created_at": self._now_iso(),
                "claim_ids": claim_ids,
            }
        )
        self._update_session_memory(session, query, result)
        session["updated_at"] = self._now_iso()
        self._write_session_graph(session)
        return session

    def _read_session_graph(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        now = self._now_iso()
        return {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "title": "",
            "summary": "",
            "temporary_memory": [],
            "nodes": [],
            "edges": [],
            "turns": [],
            "last_anchor_id": "",
            "source_types": self.source_type_schema(),
        }

    def _write_session_graph(self, session: dict) -> None:
        self._session_path(session["session_id"]).write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

    def _session_path(self, session_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(session_id or "default"))
        return self.session_dir / f"{safe}.json"

    def _session_context_for_prompt(self, session: dict) -> str:
        parts = []
        summary = str(session.get("summary") or "").strip()
        if summary:
            parts.append(f"长期摘要：{summary}")
        temporary_memory = session.get("temporary_memory", []) or []
        if temporary_memory:
            memory_lines = [f"- {item.get('text', '')}" for item in temporary_memory[-8:] if item.get("text")]
            if memory_lines:
                parts.append("当前对话临时记忆：\n" + "\n".join(memory_lines))
        turns = session.get("turns", []) or []
        if turns:
            recent = []
            for turn in turns[-4:]:
                query = self._excerpt(turn.get("query", ""), 140)
                answer = self._excerpt(turn.get("answer", ""), 180)
                recent.append(f"Q: {query}\nA: {answer}")
            parts.append("最近对话：\n" + "\n".join(recent))
        return "\n\n".join(parts)[:2400]

    def _contextual_retrieval_query(self, query: str, session: dict) -> str:
        context = []
        summary = str(session.get("summary") or "").strip()
        if summary:
            context.append(summary)
        for item in (session.get("temporary_memory", []) or [])[-6:]:
            if item.get("text"):
                context.append(str(item["text"]))
        for turn in (session.get("turns", []) or [])[-3:]:
            if turn.get("query"):
                context.append(str(turn["query"]))
        if not context:
            return query
        return self._excerpt(f"{query}\n" + "\n".join(context), 1800)

    def _update_session_memory(self, session: dict, query: str, result: dict) -> None:
        turns = session.get("turns", []) or []
        if not session.get("title"):
            session["title"] = self._session_title_from_turns(turns) or self._excerpt(query, 32)
        answer = result.get("answer", "")
        summary_line = f"{self._now_iso()} 用户关注：{self._excerpt(query, 100)}；系统结论：{self._excerpt(answer, 180)}"
        existing = str(session.get("summary") or "").strip()
        session["summary"] = self._trim_lines("\n".join([existing, summary_line]).strip(), max_chars=1600, max_lines=10)

        memory_text = self._build_temporary_memory_text(query, result)
        if memory_text:
            memories = list(session.get("temporary_memory", []) or [])
            self._merge_temporary_memory(memories, memory_text)
            session["temporary_memory"] = memories[-16:]

    def _build_temporary_memory_text(self, query: str, result: dict) -> str:
        entities = []
        for item in result.get("evidence", []) or []:
            entities.extend([str(entity) for entity in item.get("entities", [])[:4] if str(entity).strip()])
        claims = [
            claim.get("text", "")
            for claim in result.get("answer_claims", [])[:2]
            if claim.get("source_type") in {"document", "inferred"} and claim.get("text")
        ]
        tokens = self._extract_keywords(" ".join([query, " ".join(entities), " ".join(claims)]))[:8]
        if not tokens and not claims:
            return ""
        focus = "、".join(tokens[:6])
        claim_text = self._excerpt("；".join(claims), 220)
        if focus and claim_text:
            return f"本轮关注 {focus}；已形成结论：{claim_text}"
        return f"本轮关注 {focus or self._excerpt(query, 80)}"

    def _merge_temporary_memory(self, memories: list[dict], text: str) -> None:
        now = self._now_iso()
        text_tokens = set(self._extract_keywords(text.lower()))
        for item in memories:
            existing_tokens = set(self._extract_keywords(str(item.get("text", "")).lower()))
            if text_tokens and existing_tokens and len(text_tokens & existing_tokens) / max(1, len(text_tokens | existing_tokens)) >= 0.45:
                item["text"] = self._pick_shorter_memory(item.get("text", ""), text)
                item["updated_at"] = now
                item["count"] = int(item.get("count") or 1) + 1
                return
        memories.append({"id": f"mem_{uuid.uuid4().hex[:10]}", "text": text, "created_at": now, "updated_at": now, "count": 1})

    def _pick_shorter_memory(self, left: str, right: str) -> str:
        left = str(left or "").strip()
        right = str(right or "").strip()
        if not left:
            return right
        if not right:
            return left
        return right if len(right) < len(left) else left

    def _trim_lines(self, text: str, max_chars: int, max_lines: int) -> str:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        trimmed = "\n".join(lines[-max_lines:])
        return trimmed[-max_chars:]

    def _session_title_from_turns(self, turns: list[dict]) -> str:
        if not turns:
            return ""
        return self._excerpt(str(turns[0].get("query") or "新对话"), 38)

    def _filter_chunks(self, chunks: list[dict], doc_id: str = "", q: str = "") -> list[dict]:
        doc_key = (doc_id or "").strip().lower()
        query = (q or "").strip().lower()
        query_terms = [term.lower() for term in self._extract_keywords(q)[:8]]
        filtered = []
        query_matched = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {}) or {}
            doc_name = str(metadata.get("doc_name") or chunk.get("source") or "")
            doc_id_value = str(metadata.get("doc_id") or Path(doc_name).stem)
            haystack = f"{doc_name} {doc_id_value} {chunk.get('chunk_id', '')} {chunk.get('chunk_type', '')} {chunk.get('text', '')} {' '.join(chunk.get('entities', []))}".lower()
            if doc_key and doc_key not in doc_id_value.lower() and doc_key not in doc_name.lower():
                continue
            if query:
                hit = query in haystack or any(term and term in haystack for term in query_terms)
                if hit:
                    query_matched.append(chunk)
                filtered.append(chunk)
            else:
                filtered.append(chunk)
        if query and query_matched:
            matched_ids = {id(item) for item in query_matched}
            return query_matched + [item for item in filtered if id(item) not in matched_ids]
        return filtered

    def _tree_node(self, node_id: str, node_type: str, label: str, **extra) -> dict:
        node = {
            "id": node_id,
            "type": node_type,
            "kind": node_type,
            "label": label,
            "name": label,
            "source_type": extra.pop("source_type", "document"),
            "doc_id": extra.pop("doc_id", None),
            "file_name": extra.pop("file_name", None),
            "page": extra.pop("page", None),
            "section": extra.pop("section", None),
            "chunk_id": extra.pop("chunk_id", None),
            "score": extra.pop("score", None),
            "preview": extra.pop("preview", ""),
            "children": extra.pop("children", []),
        }
        node.update(extra)
        return node

    def _chunk_label(self, chunk: dict) -> str:
        metadata = chunk.get("metadata", {}) or {}
        if metadata.get("stage") == "coarse" or chunk.get("chunk_type") == "coarse_outline":
            return "Coarse outline"
        return str(chunk.get("chunk_id") or "chunk")

    def _topic_for_chunk(self, chunk: dict) -> str:
        metadata = chunk.get("metadata", {}) or {}
        for key in ("section", "title", "heading"):
            value = str(metadata.get(key) or "").strip()
            if value:
                return value[:80]
        chunk_type = str(chunk.get("chunk_type") or "").strip()
        if chunk_type:
            return chunk_type
        keywords = self._extract_keywords(chunk.get("text", ""))
        return " / ".join(keywords[:3]) if keywords else "Topic"

    def _entities_for_chunk(self, chunk: dict) -> list[str]:
        values = [str(item).strip() for item in chunk.get("entities", []) if str(item).strip()]
        for keyword in self._extract_keywords(chunk.get("text", "")):
            if keyword not in values:
                values.append(keyword)
        return values or ["unlabeled"]

    def _extract_keywords(self, text: str) -> list[str]:
        candidates = re.findall(r"\b[A-Z]{2,}[A-Z0-9-]*\b|[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9_/-]{2,24}", text or "")
        stop = {"the", "and", "for", "with", "this", "that", "from", "当前", "可以", "以及", "进行", "一个", "相关"}
        seen = set()
        keywords = []
        for candidate in candidates:
            key = candidate.lower()
            if key in stop or key in seen:
                continue
            seen.add(key)
            keywords.append(candidate)
            if len(keywords) >= 12:
                break
        return keywords

    def _excerpt(self, text: str, limit: int) -> str:
        value = re.sub(r"\s+", " ", str(text or "")).strip()
        value = re.sub(r"\b(?:undefined|null|None)\b", "", value)
        value = re.sub(r"\s{2,}", " ", value).strip(" ,;:")
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."

    def _stable_id(self, value: str) -> str:
        return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:16]

    def _now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S")


def create_provider(config: dict):
    backend = str(config.get("backend", "ollama")).lower()
    kimi_cli_provider = KimiCliProvider(config)
    api_provider = OpenAICompatibleProvider(config)
    openai_cfg = config.get("openai_compatible", {})
    kimi_cfg = config.get("kimi_cli", {})
    kimi_coding_endpoint = "api.kimi.com/coding" in str(openai_cfg.get("base_url", ""))
    coding_plan_key = _is_kimi_coding_plan_config(config)
    if coding_plan_key and backend in {"auto", "openai", "openai_compatible", "api_key", "kimi_cli"}:
        _normalize_kimi_coding_config(config)
        config["backend"] = "kimi_cli"
        return KimiCliProvider(config)
    if backend == "kimi_cli":
        _normalize_kimi_coding_config(config)
        config["backend"] = "kimi_cli"
        return KimiCliProvider(config)
    if backend == "auto":
        if kimi_coding_endpoint and kimi_cli_provider.check_connection():
            config["backend"] = "kimi_cli"
            return kimi_cli_provider
        if api_provider.check_connection():
            config["backend"] = "openai_compatible"
            return api_provider
        if kimi_cli_provider.check_connection():
            config["backend"] = "kimi_cli"
            return kimi_cli_provider
        ollama_provider = OllamaProvider(config)
        if ollama_provider.check_connection():
            config["backend"] = "ollama"
            return ollama_provider
        config["backend"] = "ollama"
        return ollama_provider
    if backend in {"openai", "openai_compatible", "api_key"}:
        if kimi_coding_endpoint and kimi_cli_provider.check_connection():
            # Kimi coding-plan keys reject plain chat/completions calls and require a
            # coding-agent client. Prefer the bundled CLI so the packaged app works
            # immediately on a fresh trusted PC.
            _normalize_kimi_coding_config(config)
            config["backend"] = "kimi_cli"
            return KimiCliProvider(config)
        config["backend"] = "openai_compatible"
        config["_api_backend_unavailable"] = not api_provider.check_connection()
        return api_provider
    return OllamaProvider(config)


def _is_kimi_coding_plan_config(config: dict) -> bool:
    openai_cfg = config.get("openai_compatible", {}) or {}
    kimi_cfg = config.get("kimi_cli", {}) or {}
    key = (
        kimi_cfg.get("api_key")
        or openai_cfg.get("api_key")
        or os.environ.get("KIMI_API_KEY")
        or os.environ.get("KNOWLEDGE_RAG_API_KEY")
        or ""
    )
    model = str(kimi_cfg.get("model") or openai_cfg.get("model") or os.environ.get("KNOWLEDGE_RAG_MODEL") or "")
    base_url = str(kimi_cfg.get("base_url") or openai_cfg.get("base_url") or os.environ.get("KNOWLEDGE_RAG_BASE_URL") or "")
    return str(key).strip().startswith("sk-kimi-") or model == "kimi-for-coding" or "api.kimi.com/coding" in base_url


def _normalize_kimi_coding_config(config: dict) -> None:
    openai_cfg = config.setdefault("openai_compatible", {})
    kimi_cfg = config.setdefault("kimi_cli", {})
    key = (
        kimi_cfg.get("api_key")
        or openai_cfg.get("api_key")
        or os.environ.get("KIMI_API_KEY")
        or os.environ.get("KNOWLEDGE_RAG_API_KEY")
        or ""
    )
    for target in (openai_cfg, kimi_cfg):
        target["base_url"] = "https://api.kimi.com/coding/v1"
        target["model"] = "kimi-for-coding"
        if key:
            target["api_key"] = key
