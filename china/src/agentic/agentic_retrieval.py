from __future__ import annotations

import re

from src.backend.service import KnowledgeBaseService


class AgenticRetrievalEngine:
    def __init__(self, service: KnowledgeBaseService) -> None:
        self.service = service

    def run(self, query: str, max_steps: int = 3) -> dict:
        steps = []
        current_query = query
        final_retrieval = None

        for step_id in range(1, max_steps + 1):
            retrieval = self.service.retrieve(current_query)
            sufficient = self._is_evidence_sufficient(query, retrieval)
            steps.append(
                {
                    "step": step_id,
                    "query": current_query,
                    "result_count": len(retrieval["retrieval_results"]),
                    "route": retrieval["route"],
                    "evidence_sufficient": sufficient,
                }
            )
            final_retrieval = retrieval
            if sufficient:
                break
            current_query = self._rewrite_query(current_query, retrieval)

        generated = self.service.generator.generate(
            query,
            final_retrieval["retrieval_results"] if final_retrieval else [],
            use_llm=False,
        )
        return {
            "query": query,
            "steps": steps,
            "final_query": current_query,
            "retrieval_results": final_retrieval["retrieval_results"] if final_retrieval else [],
            "answer": generated["answer"],
            "citations": generated["citations"],
            "evidence_chain": generated.get("evidence_chain", []),
            "evidence": generated.get("evidence", []),
            "evidence_graph": generated.get("evidence_graph", {"nodes": [], "edges": []}),
            "self_check": self._self_check(final_retrieval or {"retrieval_results": []}, generated),
        }

    def _rewrite_query(self, query: str, retrieval: dict) -> str:
        if not retrieval["retrieval_results"]:
            return query + " certification requirements architecture"
        top = retrieval["retrieval_results"][0]
        additions = []
        additions.append(top.get("doc_name", ""))
        additions.extend(top.get("entities", [])[:2])
        additions.extend(top.get("conditions", [])[:1])
        if top.get("chunk_type"):
            additions.append(top["chunk_type"])
        additions = [item for item in additions if item]
        if not additions:
            return query + " evidence source"
        return query + " " + " ".join(additions)

    def _is_evidence_sufficient(self, query: str, retrieval: dict) -> bool:
        docs = {item.get("doc_name", "") for item in retrieval["retrieval_results"] if item.get("doc_name")}
        requires_multi_doc = self._requires_multi_document_evidence(query)
        if requires_multi_doc:
            return len(retrieval["retrieval_results"]) >= 2 and len(docs) >= 2
        return len(retrieval["retrieval_results"]) >= 2 and len(docs) >= 1

    def _requires_multi_document_evidence(self, query: str) -> bool:
        lowered = query.lower()
        markers = [
            "which files together",
            "which sources",
            "compare",
            "contrast",
            "versus",
            "both",
            " and which ",
            "paired",
            "two files",
        ]
        return any(marker in lowered for marker in markers)

    def _self_check(self, retrieval: dict, generated: dict) -> dict:
        citations = generated.get("citations", [])
        answer = generated.get("answer", "")
        evidence_complete = len(retrieval.get("retrieval_results", [])) > 0
        citation_complete = bool(citations)
        distinct_docs = {item.get("doc_name", "") for item in retrieval.get("retrieval_results", []) if item.get("doc_name")}
        multi_doc_complete = len(distinct_docs) >= 2
        return {
            "evidence_complete": evidence_complete,
            "citation_complete": citation_complete,
            "multi_doc_complete": multi_doc_complete,
            "score": round(
                (0.45 if evidence_complete else 0.0)
                + (0.35 if citation_complete else 0.0)
                + (0.20 if multi_doc_complete else 0.0),
                2,
            ),
        }
