from __future__ import annotations

import math
import re
from collections import Counter
from collections import defaultdict


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    cjk = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]+", lowered)
    cjk_tokens: list[str] = []
    for segment in cjk:
        cjk_tokens.extend(list(segment))
        cjk_tokens.extend(segment[i : i + 2] for i in range(len(segment) - 1))
    preserved_tokens = re.findall(r"[a-z0-9][\w\-.]*[a-z0-9]|[a-z0-9]", lowered)
    split_text = re.sub(r"[_./\\-]+", " ", lowered)
    split_tokens = re.findall(r"[a-z0-9]+", split_text)
    return preserved_tokens + split_tokens + cjk_tokens


def metadata_text(chunk: dict) -> str:
    metadata = chunk.get("metadata", {}) or {}
    values: list[str] = [
        chunk.get("chunk_id", ""),
        chunk.get("source", ""),
        metadata.get("doc_name", ""),
        metadata.get("doc_id", ""),
        metadata.get("path", ""),
        " ".join(chunk.get("entities", []) or []),
        " ".join(chunk.get("conditions", []) or []),
    ]
    doc_name = metadata.get("doc_name") or chunk.get("source", "")
    if doc_name:
        stem = re.sub(r"\.[a-z0-9]+$", "", str(doc_name).lower())
        values.append(stem.replace("_", " ").replace("-", " "))
    return " ".join(str(value) for value in values if value)


class BM25Retriever:
    def __init__(self) -> None:
        self.chunks: list[dict] = []
        self.df: Counter[str] = Counter()
        self.avg_dl = 0.0
        self.postings: dict[str, list[int]] = defaultdict(list)
        self.idf_cache: dict[str, float] = {}

    def build(self, chunks: list[dict]) -> None:
        self.chunks = []
        self.df = Counter()
        self.avg_dl = 0.0
        self.postings = defaultdict(list)
        self.idf_cache = {}
        total_token_count = 0
        for idx, chunk in enumerate(chunks):
            body_tokens = tokenize(chunk.get("text", ""))
            meta_tokens = tokenize(metadata_text(chunk))
            tokens = body_tokens + meta_tokens * 4
            token_set = set(tokens)
            indexed = dict(chunk)
            indexed["_tokens"] = tokens
            indexed["_tf"] = Counter(tokens)
            indexed["_token_len"] = len(tokens)
            self.chunks.append(indexed)
            total_token_count += len(tokens)
            for token in token_set:
                self.df[token] += 1
                self.postings[token].append(idx)
        total = len(self.chunks)
        self.avg_dl = total_token_count / max(total, 1)
        for token, df in self.df.items():
            self.idf_cache[token] = math.log((total - df + 0.5) / (df + 0.5) + 1.0)

    def search(
        self,
        query: str,
        top_k: int = 8,
        min_score: float = 0.0,
        candidate_multiplier: int = 8,
    ) -> list[dict]:
        query_tokens = list(dict.fromkeys(tokenize(query)))
        if not query_tokens or not self.chunks:
            return []

        k1, b = 1.5, 0.75
        results = []
        candidate_indices: set[int] = set()
        for token in query_tokens:
            candidate_indices.update(self.postings.get(token, ()))
        if not candidate_indices:
            return []

        # Score only documents that contain at least one query token. This is
        # the main latency win for large knowledge bases.
        max_candidates = max(top_k * max(candidate_multiplier, 1), top_k)
        sorted_candidates = sorted(candidate_indices)
        if len(sorted_candidates) > max_candidates * 12:
            # For extremely broad CJK/common-token queries, prefer candidates
            # with more unique query-token hits before BM25 scoring.
            candidate_hits = []
            for idx in sorted_candidates:
                tf = self.chunks[idx]["_tf"]
                hit_count = sum(1 for token in query_tokens if tf.get(token, 0))
                candidate_hits.append((hit_count, idx))
            candidate_hits.sort(reverse=True)
            sorted_candidates = [idx for _, idx in candidate_hits[: max_candidates * 12]]

        for idx in sorted_candidates:
            chunk = self.chunks[idx]
            score = 0.0
            dl = chunk.get("_token_len", len(chunk["_tokens"]))
            for token in query_tokens:
                tf = chunk["_tf"].get(token, 0)
                if tf == 0:
                    continue
                idf = self.idf_cache.get(token, 0.0)
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(self.avg_dl, 1)))
                score += idf * tf_norm
            if score >= min_score:
                results.append(self._format_result(chunk, score))

        results.sort(key=lambda item: item["sparse_score"], reverse=True)
        return results[:top_k]

    def _format_result(self, chunk: dict, score: float) -> dict:
        return {
            "chunk_id": chunk["chunk_id"],
            "chunk_type": chunk.get("chunk_type", "evidence"),
            "doc_name": chunk.get("metadata", {}).get("doc_name", chunk.get("source", "")),
            "source": chunk.get("source", ""),
            "text": chunk.get("text", ""),
            "metadata": chunk.get("metadata", {}),
            "entities": chunk.get("entities", []),
            "conditions": chunk.get("conditions", []),
            "sparse_score": round(score, 6),
            "score": round(score, 6),
        }
