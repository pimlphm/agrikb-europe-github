from __future__ import annotations

from dataclasses import asdict, dataclass


COMPLEX_MARKERS = {
    "compare",
    "difference",
    "timeline",
    "why",
    "root cause",
    "multi-hop",
    "contrast",
    "which files together",
    "对比",
    "原因",
    "多跳",
    "时间线",
}

RLM_MARKERS = {
    "所有文档",
    "全部证据",
    "综合分析",
    "跨文档",
    "对比所有",
    "cross-document",
    "aggregate",
    "comprehensive",
    "所有来源",
    "遍历",
    "全面分析",
}


@dataclass
class RouteDecision:
    mode: str
    complexity: str
    use_agentic: bool
    use_rlm: bool
    use_graph: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


class QueryRouter:
    def __init__(self, config: dict) -> None:
        flags = config.get("feature_flags", {})
        self.agentic_enabled = bool(flags.get("ENABLE_AGENTIC", False))
        self.rlm_enabled = bool(flags.get("ENABLE_RLM", False))
        self.graph_enabled = bool(flags.get("ENABLE_GRAPH_LAYER", False))
        rlm_cfg = config.get("rlm", {}).get("trigger", {})
        self.rlm_keywords = set(rlm_cfg.get("keywords", RLM_MARKERS))
        self.rlm_min_complexity = rlm_cfg.get("min_query_complexity", "complex")

    def route(self, query: str) -> RouteDecision:
        lowered = query.lower()
        complex_hit = any(marker in lowered for marker in COMPLEX_MARKERS)
        long_query = len(query.split()) >= 18 or len(query) >= 80
        complexity = "complex" if complex_hit or long_query else "simple"
        use_graph = self.graph_enabled and ("entity" in lowered or "ontology" in lowered or "graph" in lowered)

        rlm_keyword_hit = any(kw in lowered for kw in self.rlm_keywords)
        complexity_met = (
            self.rlm_min_complexity == "simple"
            or (self.rlm_min_complexity == "complex" and complexity == "complex")
        )
        use_rlm = (
            self.rlm_enabled
            and (rlm_keyword_hit or (complexity_met and long_query))
        )

        use_agentic = self.agentic_enabled and complexity == "complex" and not use_rlm

        if use_rlm:
            mode = "rlm"
            reason = "RLM recursive retrieval triggered"
            if rlm_keyword_hit:
                reason += " (keyword match)"
        elif use_agentic:
            mode = "agentic"
            reason = "complexity markers detected"
        else:
            mode = "baseline"
            reason = "baseline retrieval is sufficient"

        return RouteDecision(
            mode=mode,
            complexity=complexity,
            use_agentic=use_agentic,
            use_rlm=use_rlm,
            use_graph=use_graph,
            reason=reason,
        )
