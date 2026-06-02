from __future__ import annotations

import re

from .bm25 import metadata_text, tokenize


def overlap_score(query: str, text: str) -> float:
    query_terms = set(tokenize(query))
    text_terms = set(tokenize(text))
    if not query_terms or not text_terms:
        return 0.0
    return len(query_terms & text_terms) / len(query_terms)


class HeuristicReranker:
    def rerank(self, query: str, results: list[dict], top_k: int = 8) -> list[dict]:
        reranked = []
        for item in results:
            lexical = overlap_score(query, item.get("text", ""))
            meta_lexical = overlap_score(query, metadata_text(item))
            chunk_type = item.get("chunk_type", "")
            diagnostic_bonus = 0.08 if chunk_type in {"symptom", "cause", "rule", "action"} else 0.0
            combined = item.get("score", 0.0) + lexical * 0.7 + meta_lexical * 1.4 + diagnostic_bonus
            updated = dict(item)
            updated["metadata_match_score"] = round(meta_lexical, 6)
            updated["rerank_score"] = round(combined, 6)
            updated["score"] = round(combined, 6)
            reranked.append(updated)
        reranked.sort(key=lambda entry: entry["score"], reverse=True)
        return reranked[:top_k]
