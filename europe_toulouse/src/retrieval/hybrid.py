from __future__ import annotations

from .bm25 import BM25Retriever
from .dense import DenseRetriever
from .reranker import HeuristicReranker


class HybridRetriever:
    def __init__(
        self,
        provider=None,
        dense_weight: float = 0.45,
        sparse_weight: float = 0.55,
        dense_dim: int = 128,
        dense_enabled: bool = True,
        remote_embeddings: bool = False,
        reranker_enabled: bool = True,
        dense_candidate_only: bool = True,
        sparse_candidate_multiplier: int = 10,
    ) -> None:
        self.sparse = BM25Retriever()
        self.dense = DenseRetriever(provider=provider, dim=dense_dim, enabled=dense_enabled, remote_embeddings=remote_embeddings)
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.reranker = HeuristicReranker() if reranker_enabled else None
        self.dense_candidate_only = dense_candidate_only
        self.sparse_candidate_multiplier = max(2, sparse_candidate_multiplier)

    def build(self, chunks: list[dict]) -> None:
        self.sparse.build(chunks)
        self.dense.build(chunks)

    def search(self, query: str, top_k: int = 8, rerank_top_n: int = 12, min_score: float = 0.0) -> list[dict]:
        candidate_top_k = max(top_k, rerank_top_n) * self.sparse_candidate_multiplier
        sparse_results = self.sparse.search(
            query,
            top_k=candidate_top_k,
            min_score=min_score,
            candidate_multiplier=self.sparse_candidate_multiplier,
        )
        candidate_ids = {item["chunk_id"] for item in sparse_results} if self.dense_candidate_only and sparse_results else None
        dense_results = self.dense.search(query, top_k=max(top_k, rerank_top_n), candidate_ids=candidate_ids)

        max_sparse = max((item.get("sparse_score", 0.0) for item in sparse_results), default=1.0)
        max_dense = max((item.get("dense_score", 0.0) for item in dense_results), default=1.0)
        combined: dict[str, dict] = {}

        for item in sparse_results:
            key = item["chunk_id"]
            merged = dict(item)
            merged["dense_score"] = 0.0
            combined[key] = merged

        for item in dense_results:
            key = item["chunk_id"]
            if key not in combined:
                combined[key] = dict(item)
                combined[key]["sparse_score"] = 0.0
            else:
                combined[key]["dense_score"] = item.get("dense_score", 0.0)

        results = []
        for item in combined.values():
            sparse_score = item.get("sparse_score", 0.0) / max(max_sparse, 1e-9)
            dense_score = item.get("dense_score", 0.0) / max(max_dense, 1e-9)
            item["score"] = round(
                self.sparse_weight * sparse_score + self.dense_weight * dense_score,
                6,
            )
            results.append(item)

        results.sort(key=lambda entry: entry["score"], reverse=True)
        if self.reranker:
            return self.reranker.rerank(query, results[:rerank_top_n], top_k=top_k)
        return results[:top_k]
