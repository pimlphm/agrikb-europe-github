from __future__ import annotations

import re


MECHANICAL_TERMS = [
    "bearing",
    "shaft",
    "rotor",
    "sensor",
    "motor",
    "actuator",
    "轴承",
    "转子",
    "传感器",
    "电机",
    "联轴器",
]


def extract_entities(text: str) -> list[str]:
    found = []
    lowered = text.lower()
    for term in MECHANICAL_TERMS:
        if term.lower() in lowered:
            found.append(term)

    acronyms = re.findall(r"\b[A-Z]{2,}[A-Z0-9-]*\b", text)
    found.extend(acronyms)
    return list(dict.fromkeys(found))


def infer_relations(text: str) -> list[dict]:
    lowered = text.lower()
    relations = []
    if "cause" in lowered or "导致" in text:
        relations.append({"type": "causes", "confidence": 0.7})
    if "mitigate" in lowered or "建议" in text or "检查" in text:
        relations.append({"type": "mitigated_by", "confidence": 0.65})
    return relations


def enrich_chunk(chunk: dict) -> dict:
    updated = dict(chunk)
    updated["entities"] = extract_entities(updated.get("text", ""))
    updated["relations"] = infer_relations(updated.get("text", ""))
    updated.setdefault("metadata", {})
    updated["metadata"]["entity_count"] = len(updated["entities"])
    updated["metadata"]["relation_count"] = len(updated["relations"])
    return updated
