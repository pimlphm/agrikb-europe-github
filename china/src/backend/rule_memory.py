from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


SOURCE_WEIGHT = {
    "document": 1.0,
    "inferred": 0.86,
    "web_search": 0.72,
    "model_prior": 0.36,
    "unsupported": 0.0,
}

MEMORY_KIND_LABELS = {
    "mental_model": "心智模型",
    "decision_heuristic": "决策启发",
    "principle": "知识原则",
    "anti_pattern": "反模式",
    "expression_pattern": "表达范式",
    "boundary": "诚实边界",
}

BOILERPLATE_PATTERNS = [
    r"当前知识库.*召回",
    r"不能替代.*结论",
    r"建议.*人工复核",
    r"^针对[“\"].*",
    r"conference on",
    r"journal of",
    r"proceedings of",
    r"article no",
    r"返回目录",
    r"历史项目主体名称",
    r"证据链",
    r"Primary evidence",
    r"retrieval_results",
    r"閽堝",
    r"\b[Ee]\d+\b",
]


class RuleMemoryStore:
    """Gbrain-style local rule memory with Nuwa-inspired consolidation.

    The store accepts candidate claims or rule-like chunks, filters weak text,
    then merges similar rules instead of appending noisy one-off fragments.
    It records distilled mental models, decision heuristics, anti-patterns,
    transfer scope, and evidence boundaries for each durable rule.
    """

    def __init__(self, path: Path, max_rules: int = 80) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_rules = max_rules
        if not self.path.exists():
            self._write({"version": 2, "updated_at": _now(), "rules": [], "stats": {}})

    def as_payload(self, query: str = "", limit: int = 80) -> dict[str, Any]:
        payload = self._read()
        rules = list(payload.get("rules", []))
        query_tokens = set(_tokens(query))
        if query_tokens:
            rules = [
                rule
                for rule in rules
                if query_tokens & set(rule.get("keywords", [])) or any(token in rule.get("text", "").lower() for token in query_tokens)
            ]
        rules.sort(key=lambda item: (item.get("quality", 0), item.get("support_count", 0), item.get("updated_at", "")), reverse=True)
        rules = rules[: max(1, int(limit or 80))]
        kind_counts: dict[str, int] = {}
        for rule in payload.get("rules", []):
            kind = str(rule.get("memory_kind") or "principle")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        return {
            "mode": "gbrain_nuwa_consolidated_experience",
            "method": {
                "name": "nuwa_inspired_experience_extraction",
                "description": "从文档证据和问答结论中提炼心智模型、决策启发、反模式和诚实边界，并持续合并相似规则。",
                "rule": "只保留有证据或推理支撑的可迁移规则；模型常识和未支持内容不写入长期规则库。",
            },
            "updated_at": payload.get("updated_at", ""),
            "count": len(rules),
            "total_count": len(payload.get("rules", [])),
            "stats": {**(payload.get("stats", {}) or {}), "memory_kinds": kind_counts},
            "memory_kind_labels": MEMORY_KIND_LABELS,
            "rules": rules,
        }

    def clear(self) -> dict[str, Any]:
        payload = {"version": 2, "updated_at": _now(), "rules": [], "stats": {"cleared": True}}
        self._write(payload)
        return self.as_payload()

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        target = str(rule_id or "").strip()
        if not target:
            return None
        for rule in self._read().get("rules", []):
            if isinstance(rule, dict) and str(rule.get("id") or "") == target:
                return dict(rule)
        return None

    def save_interpretation(self, rule_id: str, interpretation: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        rules = [dict(rule) for rule in payload.get("rules", []) if isinstance(rule, dict)]
        target = None
        for rule in rules:
            if str(rule.get("id") or "") == str(rule_id or ""):
                target = rule
                break
        if target is None:
            raise KeyError(f"Rule not found: {rule_id}")
        clean_interpretation = _clean_interpretation_payload(interpretation)
        now = _now()
        clean_interpretation["sedimented_at"] = now
        history = [item for item in target.get("ai_interpretations", []) if isinstance(item, dict)]
        history.insert(0, clean_interpretation)
        target["ai_interpretations"] = history[:5]
        target["latest_ai_interpretation"] = clean_interpretation
        target["sediment_count"] = int(target.get("sediment_count") or 0) + 1
        target["updated_at"] = now
        payload["rules"] = rules
        payload["updated_at"] = now
        payload["stats"] = {**(payload.get("stats", {}) or {}), "last_sedimented_rule": target.get("id"), "last_sedimented_at": now}
        self._write(payload)
        return self.as_payload()

    def update_from_query(self, query: str, result: dict[str, Any]) -> dict[str, Any]:
        candidates = []
        evidence_by_id = {item.get("evidence_id") or item.get("id"): item for item in result.get("evidence", []) if isinstance(item, dict)}
        for claim in result.get("answer_claims", []) or []:
            candidate = self._candidate_from_claim(query, claim, evidence_by_id)
            if candidate:
                candidates.append(candidate)
        for evidence in result.get("evidence", []) or []:
            candidate = self._candidate_from_evidence(query, evidence)
            if candidate:
                candidates.append(candidate)
        return self._merge_candidates(candidates)

    def refresh_from_chunks(self, chunks: list[dict[str, Any]], reset: bool = False, limit: int = 600) -> dict[str, Any]:
        if reset:
            self.clear()
        candidates = []
        for chunk in chunks[: max(1, int(limit or 600))]:
            chunk_type = str(chunk.get("chunk_type") or "").lower()
            text = str(chunk.get("text") or "")
            if chunk_type != "rule":
                continue
            metadata = chunk.get("metadata", {}) or {}
            evidence = {
                "evidence_id": chunk.get("chunk_id"),
                "doc_name": metadata.get("doc_name") or chunk.get("source"),
                "chunk_id": chunk.get("chunk_id"),
                "evidence_type": chunk.get("chunk_type"),
                "snippet": text,
                "entities": chunk.get("entities", []),
                "source_type": "document",
                "score": 1.0,
            }
            candidate = self._candidate_from_evidence("", evidence)
            if candidate:
                candidates.append(candidate)
        return self._merge_candidates(candidates)

    def _candidate_from_claim(self, query: str, claim: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        source_type = str(claim.get("source_type") or "")
        if source_type in {"unsupported", "model_prior"}:
            return None
        evidence_ids = [str(item) for item in claim.get("supporting_evidence_ids", []) if str(item).strip()]
        linked_evidence = [evidence_by_id.get(item) for item in evidence_ids if evidence_by_id.get(item)]
        text = _refine_rule_text(str(claim.get("text") or ""))
        if not _is_quality_rule(text):
            return None
        keywords = _unique(_tokens(" ".join([query, text, _evidence_words(linked_evidence)])))[:16]
        if len(keywords) < 2:
            return None
        confidence = float(claim.get("confidence") or 0.5) * SOURCE_WEIGHT.get(source_type, 0.5)
        confidence = round(min(0.98, confidence), 3)
        doc_names = _unique(_repair_mojibake(str(item.get("doc_name") or item.get("file_name") or "")) for item in linked_evidence if item)
        return {
            "text": text,
            "source_type": source_type,
            "confidence": confidence,
            "evidence_ids": evidence_ids[:10],
            "doc_names": doc_names,
            "keywords": keywords,
            "experience": _experience_frame(
                text=text,
                query=query,
                source_type=source_type,
                evidence_count=len(linked_evidence) or len(evidence_ids),
                keywords=keywords,
                doc_names=doc_names,
                confidence=confidence,
            ),
        }

    def _candidate_from_evidence(self, query: str, evidence: dict[str, Any]) -> dict[str, Any] | None:
        snippet = str(evidence.get("snippet") or evidence.get("raw_text") or evidence.get("text") or "")
        text = _best_rule_sentence(snippet)
        if not _is_quality_rule(text):
            return None
        source_type = str(evidence.get("source_type") or "document")
        if source_type in {"unsupported", "model_prior"}:
            return None
        evidence_id = str(evidence.get("evidence_id") or evidence.get("id") or evidence.get("chunk_id") or "")
        keywords = _unique(_tokens(" ".join([query, text, " ".join(map(str, evidence.get("entities", []) or []))])))[:16]
        if len(keywords) < 2:
            return None
        confidence = round(0.7 * SOURCE_WEIGHT.get(source_type, 0.5), 3)
        doc_names = (
            [_repair_mojibake(str(evidence.get("doc_name") or evidence.get("file_name") or ""))]
            if evidence.get("doc_name") or evidence.get("file_name")
            else []
        )
        return {
            "text": text,
            "source_type": source_type,
            "confidence": confidence,
            "evidence_ids": [evidence_id] if evidence_id else [],
            "doc_names": doc_names,
            "keywords": keywords,
            "experience": _experience_frame(
                text=text,
                query=query,
                source_type=source_type,
                evidence_count=1 if evidence_id else 0,
                keywords=keywords,
                doc_names=doc_names,
                confidence=confidence,
            ),
        }

    def _merge_candidates(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        payload = self._read()
        rules = [dict(rule) for rule in payload.get("rules", []) if isinstance(rule, dict)]
        added = merged = skipped = 0
        now = _now()

        for candidate in candidates:
            if not candidate or not _is_quality_rule(candidate.get("text", "")):
                skipped += 1
                continue
            target = self._find_merge_target(rules, candidate)
            if target is None:
                rule = self._new_rule(candidate, now)
                rules.append(rule)
                added += 1
            else:
                self._merge_rule(target, candidate, now)
                merged += 1

        rules.sort(key=lambda item: (item.get("quality", 0), item.get("support_count", 0), item.get("updated_at", "")), reverse=True)
        rules = rules[: self.max_rules]
        payload = {
            "version": 2,
            "updated_at": now,
            "rules": rules,
            "stats": {
                "added": added,
                "merged": merged,
                "skipped": skipped,
                "max_rules": self.max_rules,
            },
        }
        self._write(payload)
        return self.as_payload()

    def _find_merge_target(self, rules: list[dict[str, Any]], candidate: dict[str, Any]) -> dict[str, Any] | None:
        candidate_tokens = set(candidate.get("keywords", [])) or set(_tokens(candidate.get("text", "")))
        best_rule = None
        best_score = 0.0
        for rule in rules:
            rule_tokens = set(rule.get("keywords", [])) or set(_tokens(rule.get("text", "")))
            if not rule_tokens or not candidate_tokens:
                continue
            score = len(rule_tokens & candidate_tokens) / max(1, len(rule_tokens | candidate_tokens))
            if _normalized(rule.get("text", "")) in _normalized(candidate.get("text", "")) or _normalized(candidate.get("text", "")) in _normalized(rule.get("text", "")):
                score = max(score, 0.78)
            if score > best_score:
                best_score = score
                best_rule = rule
        return best_rule if best_score >= 0.42 else None

    def _new_rule(self, candidate: dict[str, Any], now: str) -> dict[str, Any]:
        text = candidate["text"]
        support_count = 1
        confidence = float(candidate.get("confidence") or 0.5)
        experience = candidate.get("experience") or _experience_frame(
            text=text,
            query="",
            source_type=str(candidate.get("source_type") or "document"),
            evidence_count=len(candidate.get("evidence_ids") or []),
            keywords=candidate.get("keywords") or [],
            doc_names=candidate.get("doc_names") or [],
            confidence=confidence,
        )
        return {
            "id": f"rule_{hashlib.sha1(_normalized(text).encode('utf-8')).hexdigest()[:12]}",
            "text": text,
            "source_type": candidate.get("source_type", "document"),
            "source_types": [candidate.get("source_type", "document")],
            "memory_kind": experience.get("memory_kind", "principle"),
            "memory_kind_label": MEMORY_KIND_LABELS.get(experience.get("memory_kind", "principle"), "知识原则"),
            "plain_explanation": experience.get("plain_explanation", ""),
            "action_steps": experience.get("action_steps", []),
            "applicable_conditions": experience.get("applicable_conditions", ""),
            "risk_warning": experience.get("risk_warning", ""),
            "decision_trigger": experience.get("decision_trigger", ""),
            "heuristic": experience.get("heuristic", text),
            "anti_pattern": experience.get("anti_pattern", ""),
            "boundary": experience.get("boundary", ""),
            "transfer_scope": experience.get("transfer_scope", ""),
            "validation": experience.get("validation", {}),
            "support_count": support_count,
            "confidence": round(confidence, 3),
            "quality": _quality_score(text, support_count, confidence),
            "keywords": _unique(candidate.get("keywords", []))[:16],
            "evidence_ids": _unique(candidate.get("evidence_ids", []))[:12],
            "doc_names": _unique(candidate.get("doc_names", []))[:8],
            "created_at": now,
            "updated_at": now,
        }

    def _merge_rule(self, rule: dict[str, Any], candidate: dict[str, Any], now: str) -> None:
        old_text = str(rule.get("text") or "")
        new_text = str(candidate.get("text") or "")
        rule["text"] = _pick_crisper_text(old_text, new_text)
        rule["support_count"] = int(rule.get("support_count") or 0) + 1
        source_type = str(candidate.get("source_type") or "document")
        rule["source_types"] = _unique([*(rule.get("source_types") or []), source_type])[:5]
        if rule.get("source_type") != "document" and source_type == "document":
            rule["source_type"] = "document"
        rule["confidence"] = round(max(float(rule.get("confidence") or 0), float(candidate.get("confidence") or 0)), 3)
        rule["keywords"] = _unique([*(rule.get("keywords") or []), *(candidate.get("keywords") or [])])[:16]
        rule["evidence_ids"] = _unique([*(rule.get("evidence_ids") or []), *(candidate.get("evidence_ids") or [])])[:12]
        rule["doc_names"] = _unique([*(rule.get("doc_names") or []), *(candidate.get("doc_names") or [])])[:8]
        _merge_experience_fields(rule, candidate)
        rule["quality"] = _quality_score(rule["text"], rule["support_count"], rule["confidence"])
        rule["updated_at"] = now

    def _read(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("rules", [])
                return payload
        except (OSError, json.JSONDecodeError):
            pass
        return {"version": 1, "updated_at": _now(), "rules": [], "stats": {}}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _clean_interpretation_payload(interpretation: dict[str, Any]) -> dict[str, Any]:
    payload = dict(interpretation or {})
    allowed = {
        "summary",
        "why",
        "when_to_use",
        "action_steps",
        "policy_market_weather_links",
        "risk_boundary",
        "next_data_to_collect",
        "farmer_action",
        "generated_at",
        "provider",
        "rule_id",
    }
    clean = {key: payload.get(key) for key in allowed if key in payload}
    for key in ["summary", "why", "when_to_use", "risk_boundary", "farmer_action", "generated_at", "provider", "rule_id"]:
        if key in clean:
            clean[key] = str(clean.get(key) or "").strip()[:1200]
    for key in ["action_steps", "policy_market_weather_links", "next_data_to_collect"]:
        values = clean.get(key)
        if not isinstance(values, list):
            values = [values] if values else []
        clean[key] = [str(item or "").strip()[:360] for item in values if str(item or "").strip()][:8]
    return clean


def _unique(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = str(value or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _tokens(text: str) -> list[str]:
    text = _repair_mojibake(text)
    values = re.findall(r"\b[A-Z]{2,}[A-Z0-9-]*\b|[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9_/-]{2,24}", text or "")
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "可以",
        "进行",
        "相关",
        "当前",
        "知识库",
        "回答",
        "证据",
        "建议",
        "人工",
        "复核",
    }
    return [item.lower() for item in values if item and item.lower() not in stop]


def _evidence_words(items: list[dict[str, Any] | None]) -> str:
    values = []
    for item in items:
        if not item:
            continue
        values.extend([str(item.get("doc_name") or ""), str(item.get("snippet") or "")[:160]])
        values.extend(map(str, item.get("entities", []) or []))
    return " ".join(values)


def _refine_rule_text(text: str) -> str:
    value = _repair_mojibake(str(text or ""))
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\[[Ee]\d+\]|【[Ee]\d+】|\([Ee]\d+\)", "", value)
    value = re.sub(r"^(因此|所以|综上|基于上述证据)[，,：:\s]*", "", value)
    value = value.strip(" -;；。")
    if len(value) > 180:
        value = value[:180].rstrip("，,；;、 ") + "。"
    if value and not re.search(r"[。.!?？]$", value):
        value += "。"
    return value


def _best_rule_sentence(text: str) -> str:
    compact = re.sub(r"\s+", " ", _repair_mojibake(str(text or ""))).strip()
    sentences = [item.strip() for item in re.split(r"(?<=[。！？.!?])\s*|[；;]\s*", compact) if item.strip()]
    if not sentences and compact:
        sentences = [compact]
    rule_like = [item for item in sentences if _looks_rule_like(item)]
    choice = rule_like[0] if rule_like else (sentences[0] if sentences else "")
    return _refine_rule_text(choice)


def _looks_rule_like(text: str) -> bool:
    value = _repair_mojibake(str(text or ""))
    return bool(
        re.search(
            r"若|如果|应当|应该|应在|应由|应按|需要|必须|不得|可通过|用于|"
            r"当(?!时).{2,50}(时|后|下)|发生原因|根本原因|原因[:：]|处置措施|防治措施|管理措施|检查措施|措施[:：]|规则|要求|判据|条件|"
            r"^(cause|action|rule|symptom)\s*:|\bwhen\b|\bif\b|\bmust\b|\bshould\b|\bshall\b|\brequires?\b",
            value,
            re.I,
        )
    )


def _is_quality_rule(text: str) -> bool:
    value = str(text or "").strip()
    if len(value) < 12 or len(value) > 190:
        return False
    if _corruption_ratio(value) > 0.18:
        return False
    if len(_tokens(value)) < 2:
        return False
    if not _looks_rule_like(value):
        return False
    if any(re.search(pattern, value, re.I) for pattern in BOILERPLATE_PATTERNS):
        return False
    if value.count("，") + value.count(",") > 8:
        return False
    return True


def _normalized(text: str) -> str:
    return "".join(_tokens(text))[:160]


def _repair_mojibake(text: str) -> str:
    value = str(text or "")
    if not value or _corruption_ratio(value) < 0.08:
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if _text_health(repaired) > _text_health(value) else value


def _corruption_ratio(text: str) -> float:
    value = str(text or "")
    if not value:
        return 0.0
    suspicious = len(re.findall(r"[\u0080-\u009f\u00c0-\u00ff]", value))
    return suspicious / max(1, len(value))


def _text_health(text: str) -> int:
    value = str(text or "")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", value))
    suspicious = len(re.findall(r"[\u0080-\u009f\u00c0-\u00ff]", value))
    return cjk * 3 - suspicious * 2


def _pick_crisper_text(old: str, new: str) -> str:
    old_quality = _text_crispness(old)
    new_quality = _text_crispness(new)
    return new if new_quality > old_quality else old


def _experience_frame(
    text: str,
    query: str,
    source_type: str,
    evidence_count: int,
    keywords: list[str],
    doc_names: list[str],
    confidence: float,
) -> dict[str, Any]:
    """Build a Nuwa-inspired operating frame for a durable memory rule."""

    clean_text = _refine_rule_text(text)
    kind = _classify_memory_kind(clean_text)
    validation = _validation_profile(source_type, evidence_count, confidence)
    return {
        "memory_kind": kind,
        "plain_explanation": _plain_explanation(clean_text, keywords, source_type),
        "action_steps": _action_steps(clean_text, keywords),
        "applicable_conditions": _applicable_conditions(clean_text, keywords, doc_names),
        "risk_warning": _risk_warning(clean_text, source_type, validation),
        "decision_trigger": _decision_trigger(clean_text, query, keywords),
        "heuristic": _heuristic_from_text(clean_text, kind),
        "anti_pattern": _anti_pattern_from_text(clean_text, kind),
        "boundary": _boundary_from_source(source_type, evidence_count, validation["status"]),
        "transfer_scope": _transfer_scope(keywords, doc_names),
        "validation": validation,
    }


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _plain_explanation(text: str, keywords: list[str], source_type: str) -> str:
    value = _repair_mojibake(str(text or ""))
    joined = " ".join([value, " ".join(keywords or [])])
    if _contains_any(joined, ("降雨", "暴雨", "湿度", "霜冻", "高温", "气象", "天气", "防汛", "抗旱")):
        return "这条规则说明：天气不是单独看的提醒，而是会同时影响采收时点、病虫害、运输和损耗，必须和作物成熟度、道路条件、冷链能力一起判断。"
    if _contains_any(joined, ("价格", "行情", "收购", "批发", "电商", "销售", "市场", "订单", "渠道")):
        return "这条规则说明：卖不卖、卖给谁，要同时看本地价格、目标市场价格、等级包装和物流成本，不能只看一个报价就下决定。"
    if _contains_any(joined, ("补贴", "申报", "政策", "扶持", "项目", "奖补", "农业农村局")):
        return "这条规则说明：政策扶持先看主体资格、产业方向、申报时间和佐证材料，再判断能不能报、报哪一类、需要补哪些材料。"
    if _contains_any(joined, ("葡萄", "草莓", "茶", "福桃", "水稻", "玉米", "蔬菜", "农机", "肥料")):
        return "这条规则说明：特色产业要把品种、技术服务、标准化生产、品牌销售和风险防控连起来看，单独增加产量不一定等于增收。"
    if _contains_any(joined, ("高标准农田", "土壤", "水利", "农田", "生态", "循环", "病虫")):
        return "这条规则说明：田块、水利、土壤、病虫害和投入品会互相影响，经营建议要先判断基础条件，再安排种植和投入。"
    if source_type == "web_search":
        return "这条规则来自联网信息，适合做实时线索；落地执行前还要核对来源、发布时间、适用地区和联系方式。"
    return "这条规则说明：遇到相似农业经营问题时，要把生产条件、政策依据、市场渠道和风险边界放在一起判断，再给出可执行动作。"


def _action_steps(text: str, keywords: list[str]) -> list[str]:
    value = _repair_mojibake(" ".join([str(text or ""), " ".join(keywords or [])]))
    if _contains_any(value, ("降雨", "暴雨", "湿度", "霜冻", "高温", "气象", "天气", "防汛", "抗旱")):
        return [
            "先看未来24到72小时天气和田间湿度。",
            "把成熟、怕损耗的果蔬优先采收或加固防护。",
            "运输前确认道路、包装、防潮和冷链安排。",
            "把异常天气后的病虫害巡查排进第二天任务。",
        ]
    if _contains_any(value, ("价格", "行情", "收购", "批发", "电商", "销售", "市场", "订单", "渠道")):
        return [
            "先查本地市场和目标市场同品类价格。",
            "按等级、规格、包装把货分开报价。",
            "把运输、冷链、平台服务费算进净收益。",
            "优先联系有稳定订单和可追溯记录的渠道。",
        ]
    if _contains_any(value, ("补贴", "申报", "政策", "扶持", "项目", "奖补", "农业农村局")):
        return [
            "先确认申报主体、经营规模和产业类别。",
            "核对通知里的截止时间、材料清单和主管部门。",
            "准备营业执照、地块/订单/票据/照片等佐证。",
            "不确定时先走预审或电话核验，避免错过窗口期。",
        ]
    if _contains_any(value, ("葡萄", "草莓", "茶", "福桃", "水稻", "玉米", "蔬菜")):
        return [
            "先确定作物生育期和当前主要风险。",
            "按技术意见安排水肥、病虫害和采收节点。",
            "同步规划分级包装、品牌露出和销售渠道。",
            "把技术服务、检测记录和销售数据留档。",
        ]
    return [
        "先确认问题属于生产、销售、政策还是风险。",
        "再核对本地资料、实时数据和证据来源。",
        "最后给出当天能执行的一到三项动作。",
    ]


def _applicable_conditions(text: str, keywords: list[str], doc_names: list[str]) -> str:
    joined = " ".join([_repair_mojibake(str(text or "")), " ".join(keywords or []), " ".join(doc_names or [])])
    if _contains_any(joined, ("江苏句容", "句容", "镇江", "茅山", "丁庄", "白兔", "华阳", "天王", "边城", "戴庄")):
        return "优先适用于江苏句容及镇江周边相近产业、相近季节和相近市场半径的场景。"
    if _contains_any(joined, ("台湾", "有机", "认证", "经营者")):
        return "适用于使用台湾开放农业数据做样板对照、主体信息整理和标准字段映射的场景。"
    if _contains_any(joined, ("public_agriculture_standard", "remote_sensing_catalog")):
        return "适用于跨数据源标准化、作物概念对齐、遥感环境分析和通用农业知识解释。"
    return "适用于作物、地区、季节、市场渠道相近，并且有本地证据或实时数据可核验的场景。"


def _risk_warning(text: str, source_type: str, validation: dict[str, Any]) -> str:
    value = _repair_mojibake(str(text or ""))
    if _contains_any(value, ("农药", "病虫", "保险", "补贴", "申报", "合同", "出口", "检疫")):
        return "涉及用药、保险、补贴、合同、出口或检疫时，必须以主管部门通知、检测要求和正式合同为准。"
    if source_type == "web_search":
        return "联网线索可能会过期，执行前要打开来源核验时间、地点、联系人和覆盖范围。"
    if (validation or {}).get("status") in {"weak", "provisional"}:
        return "当前证据可作为候选建议，关键投入或大额交易前还需要再核对一条本地证据。"
    return "执行时仍需结合当天田间情况、实际价格、交通物流和主体资质做最后判断。"


def _classify_memory_kind(text: str) -> str:
    value = _repair_mojibake(str(text or "")).lower()
    if re.search(r"不得|不要|避免|禁止|风险|失效|failure|avoid|never|do not|should not|must not", value, re.I):
        return "anti_pattern"
    if re.search(r"边界|不足|无法|不能|需人工|复核|limitation|insufficient|unknown|manual review", value, re.I):
        return "boundary"
    if re.search(r"表达|叙述|说明|术语|格式|报告|口径|wording|style|report", value, re.I):
        return "expression_pattern"
    if re.search(r"当|如果|若|when|if|should|must|shall|requires?|条件|触发|判据", value, re.I):
        return "decision_heuristic"
    if re.search(r"框架|模型|机理|机制|体系|架构|原则|规律|model|framework|mechanism|principle", value, re.I):
        return "mental_model"
    return "principle"


def _decision_trigger(text: str, query: str, keywords: list[str]) -> str:
    source = _repair_mojibake(" ".join([query, text])).strip()
    match = re.search(r"(当|如果|若|when|if)\s*([^。；;,.，]{2,60})", source, re.I)
    if match:
        return _trim_sentence(match.group(0), 64)
    if query and len(query.strip()) >= 4:
        return _trim_sentence(f"当问题涉及{query.strip()}时", 64)
    if keywords:
        return f"当问题涉及{', '.join(keywords[:3])}时"
    return "当出现相同证据模式或相似业务场景时"


def _heuristic_from_text(text: str, kind: str) -> str:
    value = _trim_sentence(_repair_mojibake(text), 110)
    if kind == "anti_pattern":
        return f"先识别并规避该风险模式，再给出结论：{value}"
    if kind == "boundary":
        return f"先说明证据边界，再回答：{value}"
    if kind == "mental_model":
        return f"用该框架先判断结构、机制和约束，再映射到具体问题：{value}"
    if kind == "expression_pattern":
        return f"回答时保持术语、层级和依据口径一致：{value}"
    if re.search(r"^(应|需|必须|不得|should|must|shall)", value, re.I):
        return value
    return f"优先按这条规则处理：{value}"


def _anti_pattern_from_text(text: str, kind: str) -> str:
    value = _trim_sentence(_repair_mojibake(text), 96)
    if kind == "anti_pattern":
        return value
    if re.search(r"不得|不要|避免|禁止|风险|avoid|never|should not|must not", value, re.I):
        return value
    return "避免把单条片段直接泛化为结论；证据不足时不得伪装成文档依据。"


def _boundary_from_source(source_type: str, evidence_count: int, validation_status: str) -> str:
    source_type = str(source_type or "document")
    if source_type == "document":
        if evidence_count >= 2:
            return "已由多个文档证据片段支撑，但仍需保留原始来源追溯。"
        return "来自单个文档证据片段；可用作候选规则，遇到关键决策需继续复核。"
    if source_type == "inferred":
        return "由多个证据综合推理得到；必须保留推理路径，不能当成原文直接引用。"
    if source_type == "web_search":
        return "来自联网结果；需保留 URL、时间和来源质量，不能混作本地文档证据。"
    if validation_status == "excluded":
        return "未进入长期记忆；缺少可靠证据支撑。"
    return "来源可靠性有限；仅作为临时启发，不作为文档事实。"


def _transfer_scope(keywords: list[str], doc_names: list[str]) -> str:
    key_part = ", ".join(_unique(keywords)[:5])
    doc_part = ", ".join(short for short in (_short_name(name, 30) for name in _unique(doc_names)[:2]) if short)
    if key_part and doc_part:
        return f"适用于关键词 {key_part} 及相关文档场景（{doc_part}）。"
    if key_part:
        return f"适用于关键词 {key_part} 相关问题。"
    if doc_part:
        return f"适用于相关文档场景（{doc_part}）。"
    return "适用于与当前证据模式相似的问题。"


def _validation_profile(source_type: str, evidence_count: int, confidence: float) -> dict[str, Any]:
    weighted = SOURCE_WEIGHT.get(str(source_type or ""), 0.5)
    if source_type in {"unsupported", "model_prior"}:
        status = "excluded"
    elif evidence_count >= 2 and confidence >= 0.62:
        status = "validated"
    elif evidence_count >= 1:
        status = "provisional"
    else:
        status = "weak"
    return {
        "status": status,
        "source_type": source_type,
        "evidence_count": int(evidence_count or 0),
        "source_weight": weighted,
        "confidence": round(float(confidence or 0), 3),
        "checks": {
            "cross_context": evidence_count >= 2,
            "generative": status in {"validated", "provisional"},
            "exclusive": confidence >= 0.6,
        },
    }


def _merge_experience_fields(rule: dict[str, Any], candidate: dict[str, Any]) -> None:
    experience = candidate.get("experience") or {}
    if not experience:
        experience = _experience_frame(
            text=str(candidate.get("text") or rule.get("text") or ""),
            query="",
            source_type=str(candidate.get("source_type") or rule.get("source_type") or "document"),
            evidence_count=len(candidate.get("evidence_ids") or []),
            keywords=candidate.get("keywords") or rule.get("keywords") or [],
            doc_names=candidate.get("doc_names") or rule.get("doc_names") or [],
            confidence=float(candidate.get("confidence") or rule.get("confidence") or 0.5),
        )
    current_kind = str(rule.get("memory_kind") or "principle")
    new_kind = str(experience.get("memory_kind") or current_kind)
    if current_kind == "principle" or new_kind in {"mental_model", "decision_heuristic"}:
        rule["memory_kind"] = new_kind
        rule["memory_kind_label"] = MEMORY_KIND_LABELS.get(new_kind, "知识原则")
    for field in ("plain_explanation", "applicable_conditions", "risk_warning"):
        merged = _pick_crisper_text(str(rule.get(field) or ""), str(experience.get(field) or ""))
        if merged:
            rule[field] = merged
    merged_steps = _unique([*(rule.get("action_steps") or []), *(experience.get("action_steps") or [])])[:5]
    if merged_steps:
        rule["action_steps"] = merged_steps
    for field in ("decision_trigger", "heuristic", "anti_pattern", "boundary", "transfer_scope"):
        merged = _pick_crisper_text(str(rule.get(field) or ""), str(experience.get(field) or ""))
        if merged:
            rule[field] = merged
    validation = dict(rule.get("validation") or {})
    incoming = dict(experience.get("validation") or {})
    evidence_count = max(int(validation.get("evidence_count") or 0), int(incoming.get("evidence_count") or 0))
    confidence = max(float(validation.get("confidence") or 0), float(incoming.get("confidence") or 0))
    validation.update(incoming)
    validation["evidence_count"] = evidence_count
    validation["confidence"] = round(confidence, 3)
    validation["status"] = "validated" if evidence_count >= 2 and confidence >= 0.62 else validation.get("status", "provisional")
    rule["validation"] = validation


def _trim_sentence(text: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip(" ,，;；。") + "…"


def _short_name(text: str, limit: int) -> str:
    value = Path(str(text or "")).name.strip()
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _text_crispness(text: str) -> float:
    value = str(text or "")
    length_score = 1.0 - min(abs(len(value) - 72) / 130, 0.8)
    rule_score = 0.2 if _looks_rule_like(value) else 0.0
    penalty = 0.25 if any(re.search(pattern, value, re.I) for pattern in BOILERPLATE_PATTERNS) else 0.0
    return length_score + rule_score - penalty


def _quality_score(text: str, support_count: int, confidence: float) -> float:
    crispness = max(0.0, _text_crispness(text))
    support = min(0.28, max(0, support_count - 1) * 0.04)
    return round(min(1.0, 0.36 + crispness * 0.28 + min(confidence, 1.0) * 0.28 + support), 3)
