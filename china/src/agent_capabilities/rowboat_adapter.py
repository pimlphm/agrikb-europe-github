from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.utils import ensure_dir


ROWBOAT_SOURCE_URL = "https://github.com/rowboatlabs/rowboat"


class RowboatCapabilityAdapter:
    """Local adapter for Rowboat-style agent capabilities.

    This module intentionally does not vendor Rowboat. It maps Rowboat's useful
    product pattern into this project: local Markdown memory, inspectable graph
    context, reviewable workflows, and artifact export.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        cfg = config.get("agent_capabilities", {})
        self.memory_dir = ensure_dir(cfg.get("memory_dir", "./knowledge/agent_memory"))
        self.workflow_dir = ensure_dir(cfg.get("workflow_dir", "./knowledge/agent_workflows"))
        self.exports_dir = ensure_dir(cfg.get("exports_dir", "./runtime/agent_exports"))
        self.index_path = self.memory_dir / "_memory_index.json"
        self._ensure_index()

    def describe(self, indexed_chunk_count: int = 0) -> dict[str, Any]:
        return {
            "name": "rowboat_compatible_agent_layer",
            "source_project": {
                "name": "rowboatlabs/rowboat",
                "url": ROWBOAT_SOURCE_URL,
                "integration_mode": "capability_adapter_not_vendor_copy",
            },
            "local_first": True,
            "memory_vault": str(self.memory_dir),
            "workflow_dir": str(self.workflow_dir),
            "exports_dir": str(self.exports_dir),
            "indexed_chunk_count": indexed_chunk_count,
            "capabilities": [
                {
                    "id": "markdown_long_term_memory",
                    "label": "Local Markdown memory vault",
                    "status": "enabled",
                    "endpoint": "/agent/memory",
                },
                {
                    "id": "evidence_grounded_workflows",
                    "label": "Evidence-grounded agent workflows",
                    "status": "enabled",
                    "endpoint": "/agent/workflows/brief",
                },
                {
                    "id": "dynamic_knowledge_graph",
                    "label": "Dynamic zoomable knowledge graph",
                    "status": "enabled",
                    "endpoint": "/exports/knowledge-graph.html",
                },
                {
                    "id": "high_resolution_graph_export",
                    "label": "High-resolution SVG/PNG graph export",
                    "status": "enabled",
                    "endpoint": "/exports/knowledge-graph.svg",
                },
                {
                    "id": "word_report_export",
                    "label": "Word report generation",
                    "status": "enabled",
                    "endpoint": "/exports/word-report",
                },
            ],
            "workflow_templates": self.workflow_templates(),
        }

    def workflow_templates(self) -> list[dict[str, str]]:
        return [
            {
                "id": "evidence_brief",
                "name": "Evidence Brief",
                "description": "Retrieve, reason, assemble answer, and optionally persist a Markdown memory note.",
            },
            {
                "id": "knowledge_report",
                "name": "Knowledge Report",
                "description": "Generate a Word report with answer, evidence chain, graph summary, and export links.",
            },
            {
                "id": "graph_snapshot",
                "name": "Graph Snapshot",
                "description": "Export a self-contained zoomable graph plus high-resolution SVG/PNG snapshots.",
            },
            {
                "id": "memory_capture",
                "name": "Memory Capture",
                "description": "Write durable local Markdown notes that can be inspected and re-ingested.",
            },
        ]

    def capture_memory(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        source: str = "manual",
        links: list[str] | None = None,
    ) -> dict[str, Any]:
        tags = [item.strip() for item in (tags or []) if item.strip()]
        links = [item.strip() for item in (links or []) if item.strip()]
        note_id = uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc).isoformat()
        safe_title = _safe_slug(title) or f"memory-{note_id}"
        target = self.memory_dir / f"{created_at[:10]}-{safe_title}-{note_id}.md"

        body = [
            "---",
            f"id: {note_id}",
            f"title: {title}",
            f"source: {source}",
            f"created_at: {created_at}",
            "tags:",
        ]
        body.extend(f"  - {tag}" for tag in tags)
        body.append("links:")
        body.extend(f"  - [[{link}]]" for link in links)
        body.extend(["---", "", f"# {title}", "", content.strip(), ""])
        target.write_text("\n".join(body), encoding="utf-8")

        record = {
            "id": note_id,
            "title": title,
            "path": str(target),
            "source": source,
            "tags": tags,
            "links": links,
            "created_at": created_at,
            "preview": _compact(content, 220),
        }
        self._append_index(record)
        return record

    def search_memory(self, query: str = "", limit: int = 20) -> dict[str, Any]:
        records = self._load_index()
        query = query.strip().lower()
        ranked: list[tuple[int, dict[str, Any]]] = []
        for record in records:
            text = " ".join(
                [
                    record.get("title", ""),
                    record.get("preview", ""),
                    " ".join(record.get("tags", [])),
                ]
            ).lower()
            if not query:
                score = 1
            else:
                score = text.count(query)
                if query in text:
                    score += 3
            if score:
                ranked.append((score, record))
        ranked.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
        return {
            "query": query,
            "memory_dir": str(self.memory_dir),
            "count": len(ranked[:limit]),
            "items": [item for _, item in ranked[:limit]],
        }

    def save_workflow_run(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc).isoformat()
        target = self.workflow_dir / f"{created_at[:10]}-{workflow_id}-{run_id}.json"
        record = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "created_at": created_at,
            "payload": payload,
        }
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"run_id": run_id, "path": str(target), "created_at": created_at}

    def _ensure_index(self) -> None:
        if not self.index_path.exists():
            self.index_path.write_text("[]", encoding="utf-8")

    def _load_index(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.index_path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except json.JSONDecodeError:
            return []

    def _append_index(self, record: dict[str, Any]) -> None:
        records = self._load_index()
        records.append(record)
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        self.index_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "-", value.strip(), flags=re.UNICODE)
    return slug.strip("-_.")[:80]


def _compact(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
