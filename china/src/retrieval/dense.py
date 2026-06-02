from __future__ import annotations

import hashlib
import math
import re

from .bm25 import metadata_text


def dense_tokenize(text: str) -> list[str]:
    lowered = text.lower()
    split_text = re.sub(r"[_./\\-]+", " ", lowered)
    return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", split_text)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


class DenseRetriever:
    def __init__(self, provider=None, dim: int = 128, enabled: bool = True, remote_embeddings: bool = False) -> None:
        self.provider = provider
        self.dim = dim
        self.enabled = enabled
        self.remote_embeddings = remote_embeddings
        self.chunks: list[dict] = []
        self.chunk_by_id: dict[str, dict] = {}
        self.embedding_cache: dict[str, list[float]] = {}

    def build(self, chunks: list[dict]) -> None:
        self.chunks = [dict(chunk) for chunk in chunks]
        self.chunk_by_id = {}
        texts = [self._index_text(item) for item in self.chunks]
        embeddings = []
        if self.enabled and self.remote_embeddings and self.provider:
            try:
                embeddings = self.provider.embed_texts(texts)
            except Exception:
                embeddings = []
        if not embeddings or len(embeddings) != len(self.chunks):
            embeddings = [self._cached_fallback_embed(text) for text in texts]
        for chunk, embedding in zip(self.chunks, embeddings):
            chunk["_embedding"] = embedding
            self.chunk_by_id[str(chunk.get("chunk_id", ""))] = chunk

    def search(self, query: str, top_k: int = 8, candidate_ids: set[str] | None = None) -> list[dict]:
        if not self.chunks:
            return []

        if self.enabled and self.remote_embeddings and self.provider:
            try:
                query_embedding = self.provider.embed_texts([query])[0]
            except Exception:
                query_embedding = self._fallback_embed(query)
        else:
            query_embedding = self._fallback_embed(query)

        results = []
        if candidate_ids:
            candidates = [self.chunk_by_id[item] for item in candidate_ids if item in self.chunk_by_id]
        else:
            candidates = self.chunks

        for chunk in candidates:
            score = cosine_similarity(query_embedding, chunk["_embedding"])
            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_type": chunk.get("chunk_type", "evidence"),
                    "doc_name": chunk.get("metadata", {}).get("doc_name", chunk.get("source", "")),
                    "source": chunk.get("source", ""),
                    "text": chunk.get("text", ""),
                    "metadata": chunk.get("metadata", {}),
                    "entities": chunk.get("entities", []),
                    "conditions": chunk.get("conditions", []),
                    "dense_score": round(score, 6),
                    "score": round(score, 6),
                }
            )

        results.sort(key=lambda item: item["dense_score"], reverse=True)
        return results[:top_k]

    def _cached_fallback_embed(self, text: str) -> list[float]:
        key = hashlib.sha1(f"{self.dim}\0{text}".encode("utf-8", errors="ignore")).hexdigest()
        cached = self.embedding_cache.get(key)
        if cached is not None:
            return cached
        embedding = self._fallback_embed(text)
        self.embedding_cache[key] = embedding
        return embedding

    def _fallback_embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in dense_tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.dim
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _index_text(self, chunk: dict) -> str:
        return f"{chunk.get('text', '')}\n{metadata_text(chunk)}"
