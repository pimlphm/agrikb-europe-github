from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime
from html import unescape
from typing import Any


try:  # Optional open-source package; the local fallback keeps delivery self-contained.
    from rank_bm25 import BM25Okapi as _RankBm25Okapi  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _RankBm25Okapi = None


HEADLINE_KEYWORDS = {
    "policy": ["政策", "补贴", "扶持", "申报", "农业农村局", "新农人", "三农"],
    "market": ["行情", "价格", "收购", "批发", "销售", "电商", "订单"],
    "weather": ["天气", "降雨", "高温", "大风", "预警", "气象", "采收"],
    "logistics": ["冷链", "物流", "配送", "运输", "到货", "仓储"],
    "input": ["肥料", "农机", "种子", "农药", "农资", "尿素", "拖拉机"],
}


def recommend_headlines(
    items: list[dict],
    query: str = "",
    production_name: str = "",
    market_name: str = "",
    limit: int = 12,
) -> list[dict]:
    normalized = [_normalize_item(item) for item in items]
    normalized = [item for item in normalized if item["title"]]
    if not normalized:
        return []
    query_text = _clean(" ".join([query, production_name, market_name, "政策 行情 天气 冷链 收购 农资"]))
    corpus_tokens = [_tokenize(f"{item['title']} {item['snippet']} {item['category']}") for item in normalized]
    query_tokens = _tokenize(query_text)
    bm25_scores = _bm25_scores(corpus_tokens, query_tokens)
    now = datetime.now()
    for index, item in enumerate(normalized):
        text = f"{item['title']} {item['snippet']}"
        item["score"] = round(
            bm25_scores[index]
            + _freshness_score(item.get("date", ""), now)
            + _locality_score(text, production_name, market_name)
            + _urgency_score(text)
            + _category_score(item.get("category", "")),
            4,
        )
        item["reason"] = _reason_for_item(item, production_name, market_name)
    ranked = sorted(normalized, key=lambda item: item["score"], reverse=True)
    return _mmr_diversify(ranked, limit=limit)


def build_headline_items_from_regional_payload(payload: dict, query: str = "") -> list[dict]:
    if not payload:
        return []
    items: list[dict] = []
    groups = [
        ("policy", payload.get("policy_results") or []),
        ("market", payload.get("market_results") or []),
        ("logistics", payload.get("logistics_results") or []),
        ("ecommerce", payload.get("ecommerce_results") or []),
    ]
    for category, group in groups:
        for item in group:
            items.append(
                {
                    "title": item.get("title") or item.get("snippet") or "",
                    "snippet": item.get("snippet") or "",
                    "url": item.get("url") or "",
                    "source": item.get("source") or item.get("source_type") or "",
                    "date": item.get("date") or "",
                    "category": category,
                }
            )
    weather = payload.get("production_weather") or payload.get("weather") or {}
    market_weather = payload.get("market_weather") or {}
    recommendation = payload.get("market_recommendation") or ""
    if weather or recommendation:
        items.append(
            {
                "title": recommendation or "关注两地天气与采收发货窗口",
                "snippet": (
                    f"产地温度{weather.get('temperature_2m')}℃，降水{weather.get('precipitation')}mm；"
                    f"市场降水{market_weather.get('precipitation')}mm。"
                ),
                "url": "https://open-meteo.com/",
                "source": "Open-Meteo",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": "weather",
            }
        )
    for supplier in payload.get("logistics_suppliers") or []:
        items.append(
            {
                "title": f"冷链备选：{supplier.get('name', '')}",
                "snippet": supplier.get("service_scope") or supplier.get("reason") or supplier.get("contact_method") or "",
                "url": supplier.get("url") or "",
                "source": supplier.get("platform") or "冷链来源",
                "date": "",
                "category": "logistics",
            }
        )
    production = payload.get("production_location") or payload.get("region") or {}
    market = payload.get("market_location") or {}
    return recommend_headlines(
        items,
        query=query,
        production_name=production.get("short_name") or production.get("name") or "",
        market_name=market.get("short_name") or market.get("name") or "",
        limit=12,
    )


def _bm25_scores(corpus_tokens: list[list[str]], query_tokens: list[str]) -> list[float]:
    if not corpus_tokens:
        return []
    if _RankBm25Okapi is not None:
        try:
            return [float(score) for score in _RankBm25Okapi(corpus_tokens).get_scores(query_tokens)]
        except Exception:
            pass
    return _FallbackBM25(corpus_tokens).get_scores(query_tokens)


class _FallbackBM25:
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.avgdl = sum(len(doc) for doc in corpus) / max(1, len(corpus))
        self.doc_freq: Counter[str] = Counter()
        for doc in corpus:
            self.doc_freq.update(set(doc))
        self.n_docs = len(corpus)

    def get_scores(self, query: list[str]) -> list[float]:
        query_terms = Counter(query)
        scores = []
        for doc in self.corpus:
            tf = Counter(doc)
            dl = len(doc) or 1
            score = 0.0
            for term, qf in query_terms.items():
                if term not in tf:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
                denom = tf[term] + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-6))
                score += idf * (tf[term] * (self.k1 + 1) / denom) * min(qf, 2)
            scores.append(score)
        return scores


def _mmr_diversify(items: list[dict], limit: int = 12, diversity: float = 0.32) -> list[dict]:
    selected: list[dict] = []
    candidates = list(items)
    while candidates and len(selected) < limit:
        best_index = 0
        best_score = -1e9
        for index, item in enumerate(candidates):
            similarity = max((_jaccard(item.get("tokens", []), chosen.get("tokens", [])) for chosen in selected), default=0.0)
            mmr = (1 - diversity) * float(item.get("score", 0)) - diversity * similarity
            if mmr > best_score:
                best_score = mmr
                best_index = index
        selected.append(candidates.pop(best_index))
    return [{key: value for key, value in item.items() if key != "tokens"} for item in selected]


def _normalize_item(item: dict) -> dict:
    title = _clean(item.get("title") or item.get("name") or item.get("snippet") or "")
    snippet = _clean(item.get("snippet") or item.get("text") or "")
    category = _clean(item.get("category") or item.get("source_type") or "news")
    tokens = _tokenize(f"{title} {snippet} {category}")
    return {
        "title": title[:90],
        "snippet": snippet[:220],
        "url": str(item.get("url") or item.get("source_url") or "").strip(),
        "source": _clean(item.get("source") or item.get("platform") or item.get("source_type") or ""),
        "date": _clean(item.get("date") or item.get("publishDate") or item.get("updated_at") or ""),
        "category": category,
        "tokens": tokens,
    }


def _tokenize(text: str) -> list[str]:
    value = _clean(text).lower()
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", value)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    for segment in chinese:
        tokens.extend(segment[index : index + 2] for index in range(max(0, len(segment) - 1)))
        tokens.extend(segment[index : index + 3] for index in range(max(0, len(segment) - 2)))
    return [token for token in tokens if token.strip()]


def _freshness_score(date_text: str, now: datetime) -> float:
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", date_text or "")
    if not match:
        return 0.2
    try:
        date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return 0.2
    days = max(0, (now - date).days)
    if days <= 1:
        return 2.2
    if days <= 7:
        return 1.5
    if days <= 30:
        return 0.8
    return 0.15


def _locality_score(text: str, production_name: str, market_name: str) -> float:
    score = 0.0
    value = text or ""
    for name in [production_name, market_name, "江苏", "镇江", "句容"]:
        name = _clean(name)
        if name and name in value:
            score += 0.55
    return min(score, 2.2)


def _urgency_score(text: str) -> float:
    value = text or ""
    score = 0.0
    for word in ["今日", "实时", "预警", "申报", "收购", "价格", "补贴", "降雨", "冷链", "行情"]:
        if word in value:
            score += 0.28
    return min(score, 1.8)


def _category_score(category: str) -> float:
    value = category or ""
    if "weather" in value:
        return 1.6
    if "market" in value:
        return 1.35
    if "policy" in value:
        return 1.2
    if "logistics" in value:
        return 1.05
    return 0.65


def _reason_for_item(item: dict, production_name: str, market_name: str) -> str:
    text = f"{item.get('title', '')} {item.get('snippet', '')}"
    for label, words in HEADLINE_KEYWORDS.items():
        if any(word in text for word in words):
            mapping = {
                "policy": "政策/补贴相关",
                "market": "行情/收购相关",
                "weather": "天气/生产风险",
                "logistics": "物流/冷链相关",
                "input": "农资/农机相关",
            }
            return mapping[label]
    if production_name and production_name in text:
        return "本地信息"
    if market_name and market_name in text:
        return "目标市场信息"
    return "综合推荐"


def _jaccard(left: list[str], right: list[str]) -> float:
    a = set(left)
    b = set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()
