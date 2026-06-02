from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from core.doc_parser import parse_document
from knowledge.ingestion.extractor import enrich_chunk
from knowledge.ingestion.segmenter import segment_parsed_document
from src.backend.utils import ensure_dir, resolve_repo_path


class IngestPipeline:
    def __init__(self, config: dict) -> None:
        self.config = config
        storage = config.get("storage", {})
        ingestion = config.get("ingestion", {})
        self.chunk_dir = ensure_dir(storage.get("chunk_dir", "./knowledge/chunks"))
        self.wiki_dir = ensure_dir(storage.get("wiki_dir", "./knowledge/wiki"))
        self.db_path = resolve_repo_path(storage.get("chunk_db", "./knowledge/chunks.db"))
        self.write_chunk_json_files = bool(ingestion.get("write_chunk_json_files", True))
        self.db_batch_size = max(100, int(ingestion.get("db_batch_size", 2000) or 2000))
        self.chunk_file_workers = max(0, int(ingestion.get("chunk_file_workers", 0) or 0))
        self._init_db()

    def ingest_paths(self, paths: list[str], progress_callback: Callable[[dict], None] | None = None) -> dict:
        parse_workers = int(self.config.get("ingestion", {}).get("parse_workers", 0) or 0)
        parse_workers = parse_workers or min(8, max(2, (os.cpu_count() or 4)))
        valid_paths = [str(path) for path in paths if path]
        summary = {"documents_processed": 0, "chunks_written": 0, "wiki_pages_written": 0}
        if not valid_paths:
            return summary
        if len(valid_paths) <= 1:
            return self._commit_prepared_items(
                [self._prepare_path(valid_paths[0])],
                summary,
                progress_callback,
            )

        with ThreadPoolExecutor(max_workers=min(parse_workers, len(valid_paths))) as executor:
            futures = [executor.submit(self._prepare_path, path) for path in valid_paths]
            return self._commit_prepared_items(
                (future.result() for future in as_completed(futures)),
                summary,
                progress_callback,
            )

    def ingest_coarse_paths(self, paths: list[str], progress_callback: Callable[[dict], None] | None = None) -> dict:
        """Write one very cheap outline chunk per document before deep parsing.

        This gives the UI and retriever a document-level tree/graph in seconds
        for large batches. Deep parsing later replaces the coarse-only view with
        refined chunks, but the outline chunk remains useful as a document index.
        """
        valid_paths = [str(path) for path in paths if path]
        summary = {
            "documents_processed": 0,
            "chunks_written": 0,
            "wiki_pages_written": 0,
            "coarse_documents": 0,
            "stage": "coarse",
        }
        if not valid_paths:
            return summary

        buffer: list[dict] = []
        for path in valid_paths:
            payload = self._coarse_payload_for_path(path)
            if not payload:
                continue
            chunk = enrich_chunk(self._coarse_chunk_for_payload(payload))
            buffer.append(chunk)
            summary["documents_processed"] += 1
            summary["chunks_written"] += 1
            summary["coarse_documents"] += 1
            if len(buffer) >= self.db_batch_size:
                self._write_chunks(buffer)
                self._insert_chunk_rows(buffer)
                buffer.clear()
            if progress_callback:
                progress_callback(
                    {
                        **summary,
                        "current_file": payload.get("name", ""),
                        "last_chunks_written": 1,
                        "coarse_ready": True,
                        "refinement_status": "pending",
                    }
                )

        if buffer:
            self._write_chunks(buffer)
            self._insert_chunk_rows(buffer)
        return summary

    def ingest_document_payloads(self, payloads: list[dict], progress_callback: Callable[[dict], None] | None = None) -> dict:
        summary = {"documents_processed": 0, "chunks_written": 0, "wiki_pages_written": 0}
        valid_payloads = [payload for payload in payloads if payload]
        if not valid_payloads:
            return summary
        parse_workers = int(self.config.get("ingestion", {}).get("parse_workers", 0) or 0)
        parse_workers = parse_workers or min(8, max(2, (os.cpu_count() or 4)))
        if len(valid_payloads) <= 1:
            return self._commit_prepared_items(
                [self._prepare_payload_chunks(valid_payloads[0])],
                summary,
                progress_callback,
            )
        with ThreadPoolExecutor(max_workers=min(parse_workers, len(valid_payloads))) as executor:
            futures = [executor.submit(self._prepare_payload_chunks, payload) for payload in valid_payloads]
            return self._commit_prepared_items(
                (future.result() for future in as_completed(futures)),
                summary,
                progress_callback,
            )

    def _ingest_one_payload(
        self,
        payload: dict | None,
        summary: dict,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> None:
        if not payload or not payload.get("content", "").strip():
            return
        payload, chunks = self._prepare_payload_chunks(payload)
        self._write_chunks(chunks)
        self._insert_chunk_rows(chunks)
        summary["documents_processed"] += 1
        summary["chunks_written"] += len(chunks)
        if self.config.get("ingestion", {}).get("enable_wiki_stub", True):
            self._write_wiki_stub(payload, chunks)
            summary["wiki_pages_written"] += 1
        if progress_callback:
            progress_callback(
                {
                    **summary,
                    "current_file": payload.get("name", ""),
                    "last_chunks_written": len(chunks),
                }
            )

    def _prepare_path(self, path: str) -> tuple[dict | None, list[dict]]:
        return self._prepare_payload_chunks(parse_document(path))

    def _prepare_payload_chunks(self, payload: dict | None) -> tuple[dict | None, list[dict]]:
        if not payload or not payload.get("content", "").strip():
            return payload, []
        chunks = [enrich_chunk(chunk) for chunk in segment_parsed_document(payload, self.config)]
        for chunk in chunks:
            metadata = chunk.setdefault("metadata", {})
            metadata.setdefault("stage", "refined")
            metadata["refinement_status"] = "complete"
            metadata.setdefault("source_path", payload.get("path", payload.get("name", "")))
        return payload, chunks

    def _coarse_payload_for_path(self, path: str) -> dict | None:
        item = Path(path)
        if not item.exists() or item.suffix.lower() not in self._supported_extensions():
            return None
        stat = item.stat()
        preview = self._quick_preview(item)
        return {
            "path": str(item.resolve()),
            "name": item.name,
            "ext": item.suffix.lower(),
            "content": preview,
            "size_kb": round(stat.st_size / 1024, 1),
            "mtime": round(stat.st_mtime, 3),
        }

    def _coarse_chunk_for_payload(self, payload: dict) -> dict:
        doc_id = Path(payload["name"]).stem
        source_path = payload.get("path", payload["name"])
        stable = self._stable_doc_key(source_path, payload.get("mtime"), payload.get("size_kb"))
        text = "\n".join(
            [
                f"Document outline: {payload['name']}",
                f"Extension: {payload.get('ext', '')}",
                f"Approx size KB: {payload.get('size_kb', 0)}",
                "Fast preview:",
                payload.get("content", "")[:1800],
            ]
        ).strip()
        return {
            "chunk_id": f"coarse_{stable}",
            "chunk_type": "coarse_outline",
            "text": text,
            "entities": self._filename_keywords(payload["name"]),
            "conditions": [],
            "relations": [{"type": "coarse_index_of", "confidence": 0.55}],
            "source": payload["name"],
            "metadata": {
                "doc_id": doc_id,
                "doc_name": payload["name"],
                "source_path": source_path,
                "page": None,
                "tokens": len(re.findall(r"[\w\u4e00-\u9fff]+", text)),
                "stage": "coarse",
                "refinement_status": "pending",
                "coarse_ready_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "size_kb": payload.get("size_kb", 0),
            },
        }

    def _quick_preview(self, path: Path, max_bytes: int = 65536) -> str:
        ext = path.suffix.lower()
        if ext in {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".html", ".htm", ".xml", ".rst", ".tex"}:
            raw = path.read_bytes()[:max_bytes]
            return self._decode_preview(raw)
        if ext == ".docx":
            try:
                with ZipFile(path) as archive:
                    raw = archive.read("word/document.xml")[:max_bytes]
                return self._strip_xml(self._decode_preview(raw))
            except (KeyError, BadZipFile, OSError):
                return ""
        raw = path.read_bytes()[: min(max_bytes, 131072)]
        return self._decode_preview(raw)

    def _decode_preview(self, raw: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                text = raw.decode(encoding, errors="ignore")
                if text.strip():
                    return self._clean_preview_text(text)
            except LookupError:
                continue
        return ""

    def _strip_xml(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        return self._clean_preview_text(text)

    def _clean_preview_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9][A-Za-z0-9_./:-]{2,}", text)
        return " ".join(tokens[:240])

    def _filename_keywords(self, filename: str) -> list[str]:
        stem = Path(filename).stem
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Z]{2,}[A-Z0-9-]*|[A-Za-z][A-Za-z0-9_-]{2,}", stem)
        return list(dict.fromkeys(tokens[:12]))

    def _stable_doc_key(self, path: str, mtime: object = "", size_kb: object = "") -> str:
        value = f"{path}|{mtime}|{size_kb}"
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]

    def _supported_extensions(self) -> set[str]:
        from core.doc_parser import PARSER_MAP

        return set(PARSER_MAP)

    def _commit_prepared_items(
        self,
        prepared_items,
        summary: dict,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        db_buffer: list[dict] = []
        for payload, chunks in prepared_items:
            if not payload or not chunks:
                continue
            self._write_chunks(chunks)
            db_buffer.extend(chunks)
            if progress_callback or len(db_buffer) >= self.db_batch_size:
                self._insert_chunk_rows(db_buffer)
                db_buffer.clear()

            summary["documents_processed"] += 1
            summary["chunks_written"] += len(chunks)
            if self.config.get("ingestion", {}).get("enable_wiki_stub", True):
                self._write_wiki_stub(payload, chunks)
                summary["wiki_pages_written"] += 1
            if progress_callback:
                progress_callback(
                    {
                        **summary,
                        "current_file": payload.get("name", ""),
                        "last_chunks_written": len(chunks),
                    }
                )

        if db_buffer:
            self._insert_chunk_rows(db_buffer)
        return summary

    def _write_chunk(self, chunk: dict) -> None:
        if not self.write_chunk_json_files:
            return
        path = self.chunk_dir / f"{chunk['chunk_id']}.json"
        path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_chunks(self, chunks: list[dict]) -> None:
        if not self.write_chunk_json_files or not chunks:
            return
        if self.chunk_file_workers <= 1 or len(chunks) < 64:
            for chunk in chunks:
                self._write_chunk(chunk)
            return
        with ThreadPoolExecutor(max_workers=min(self.chunk_file_workers, len(chunks))) as executor:
            list(executor.map(self._write_chunk, chunks))

    def _write_wiki_stub(self, payload: dict, chunks: list[dict]) -> None:
        chunk_types = {}
        for chunk in chunks:
            chunk_types[chunk["chunk_type"]] = chunk_types.get(chunk["chunk_type"], 0) + 1
        lines = [
            f"# {payload['name']}",
            "",
            f"- Chunk count: {len(chunks)}",
            f"- Types: {json.dumps(chunk_types, ensure_ascii=False)}",
            f"- Source: {payload['name']}",
            "",
            "## Summary",
            "",
            (payload.get("content", "")[:1200] + "...") if len(payload.get("content", "")) > 1200 else payload.get("content", ""),
        ]
        path = self.wiki_dir / f"{Path(payload['name']).stem}.md"
        path.write_text("\n".join(lines), encoding="utf-8")

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    entities_json TEXT NOT NULL,
                    conditions_json TEXT NOT NULL,
                    relations_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _insert_chunk_rows(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executemany(
                """
                INSERT OR REPLACE INTO chunks (
                    chunk_id, doc_name, source, chunk_type, text,
                    entities_json, conditions_json, relations_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk["chunk_id"],
                        chunk.get("metadata", {}).get("doc_name", chunk.get("source", "")),
                        chunk.get("source", ""),
                        chunk.get("chunk_type", ""),
                        chunk.get("text", ""),
                        json.dumps(chunk.get("entities", []), ensure_ascii=False),
                        json.dumps(chunk.get("conditions", []), ensure_ascii=False),
                        json.dumps(chunk.get("relations", []), ensure_ascii=False),
                        json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                    )
                    for chunk in chunks
                ],
            )
            conn.commit()

    def _insert_chunk_row(self, chunk: dict) -> None:
        self._insert_chunk_rows([chunk])
