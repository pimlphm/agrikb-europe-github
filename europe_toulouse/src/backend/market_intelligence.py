from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from src.backend.web_search import search_web


PFSC_BASE = "https://pfsc.agri.cn"
PFSC_SOURCE_URL = "https://pfsc.agri.cn/"
MARKET_PRICE_CATEGORIES = [
    {
        "id": "produce",
        "name": "农产品行情",
        "presets": ["草莓", "水蜜桃", "茶叶", "大白菜", "青椒", "番茄", "黄瓜", "土豆", "猪肉(白条猪)", "鸡蛋", "草鱼"],
    },
    {"id": "fertilizer", "name": "肥料农资", "presets": ["尿素", "复合肥", "磷酸二铵", "氯化钾", "有机肥", "水溶肥"]},
    {"id": "machinery", "name": "农机装备", "presets": ["拖拉机", "插秧机", "植保无人机", "收割机", "冷藏车", "烘干机"]},
    {"id": "seed", "name": "种子种苗", "presets": ["草莓苗", "水稻种子", "玉米种子", "蔬菜种苗", "果树苗", "茶苗"]},
    {"id": "pesticide", "name": "农药植保", "presets": ["杀菌剂", "杀虫剂", "除草剂", "生物农药", "绿色防控", "植保服务"]},
    {"id": "feed", "name": "饲料养殖", "presets": ["玉米饲料", "豆粕", "配合饲料", "蛋鸡饲料", "水产饲料", "青贮饲料"]},
]

MARKET_ONTOLOGY_CLASSES = {
    "produce": {
        "class": "agri:ProduceMarketObservation",
        "broader": "agri:AgriculturalProduct",
        "label": "农产品行情",
    },
    "fertilizer": {
        "class": "agri:FertilizerMarketObservation",
        "broader": "agri:AgriculturalInput",
        "label": "肥料农资",
    },
    "machinery": {
        "class": "agri:MachineryMarketObservation",
        "broader": "agri:AgriculturalMachinery",
        "label": "农机装备",
    },
    "seed": {
        "class": "agri:SeedMarketObservation",
        "broader": "agri:SeedAndSeedling",
        "label": "种子种苗",
    },
    "pesticide": {
        "class": "agri:PesticideMarketObservation",
        "broader": "agri:PlantProtectionInput",
        "label": "农药植保",
    },
    "feed": {
        "class": "agri:FeedMarketObservation",
        "broader": "agri:FeedAndBreedingInput",
        "label": "饲料养殖",
    },
}

JURONG_LOCAL_PRICE_KEYWORDS = (
    "草莓",
    "水蜜桃",
    "桃",
    "茶叶",
    "大米",
    "稻米",
    "青菜",
    "大白菜",
    "菠菜",
    "菜花",
    "黄瓜",
    "番茄",
    "南瓜",
    "土豆",
    "白萝卜",
    "生姜",
    "大葱",
    "青椒",
    "鸡蛋",
    "猪肉",
)


def build_market_price_intelligence(
    product: str = "草莓",
    category: str = "produce",
    production_location: str = "江苏句容",
    market_location: str = "镇江农产品批发市场",
    llm_provider=None,
    include_ai: bool = False,
) -> dict:
    category = _normalize_category(category)
    product = _clean(product) or _default_product(category)
    production_location = _clean(production_location) or "江苏句容"
    market_location = _clean(market_location) or "镇江农产品批发市场"
    rows: list[dict] = []
    sources: list[dict] = []
    index_rows: list[dict] = []

    if category == "produce":
        ranking = _fetch_pfsc_growth_ranking()
        index_rows = _fetch_pfsc_index_rows()
        rows.extend(_rows_from_pfsc_ranking(ranking, product))
        sources.extend(_sources_from_pfsc_articles(product, market_location))
        if not rows:
            rows.extend(_rows_from_pfsc_ranking(ranking, "", limit=8))
    else:
        direct_sources = _direct_input_price_sources(category, product)
        sources.extend(direct_sources)
        rows.extend(_rows_from_direct_sources(direct_sources, product, category, market_location))
        sources.extend(_curated_input_sources(category, product))

    sources.extend(_web_sources_for_market_query(category, product, production_location, market_location))
    rows.extend(_rows_from_source_snippets(sources, product, category, market_location))
    rows = _dedupe_rows([_sanitize_price_row(row) for row in rows])[:12]
    local_price_rows = _build_local_price_rows(product, category, rows, production_location, market_location)
    sources = _dedupe_sources(sources)[:8]
    exact_count = sum(1 for row in rows if row.get("match") == "exact")
    decision = _build_price_decision(product, category, rows, exact_count, sources)
    ai_insight = _build_market_ai_insight(
        product=product,
        category=category,
        production_location=production_location,
        market_location=market_location,
        rows=rows,
        sources=sources,
        decision=decision,
        llm_provider=llm_provider,
        include_ai=include_ai,
    )
    payload = {
        "category": category,
        "category_name": _category_name(category),
        "product": product,
        "production_location": production_location,
        "market_location": market_location,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_note": "农产品价格优先读取农业农村部信息中心全国农产品批发市场价格信息系统；农资、农机、肥料等以公开网页实时聚合为准。",
        "price_rows": rows,
        "local_price_rows": local_price_rows,
        "local_price_note": _build_local_price_note(category, production_location, market_location, local_price_rows),
        "source_cards": sources,
        "index_rows": index_rows[:8],
        "decision": decision,
        "ai_insight": ai_insight,
        "ai_enabled": bool(include_ai),
        "category_options": MARKET_PRICE_CATEGORIES,
    }
    payload["ontology_record"] = _persist_market_ontology(payload)
    return payload


def _build_local_price_rows(
    product: str,
    category: str,
    rows: list[dict],
    production_location: str,
    market_location: str,
) -> list[dict]:
    if category != "produce" or not rows:
        return []
    production_name = _clean(production_location) or "江苏句容"
    market_name = _clean(market_location) or "镇江农产品批发市场"
    product_text = _clean(product)
    selected: list[dict] = []
    for row in rows:
        name = _clean(row.get("name"))
        if not name:
            continue
        is_query = bool(product_text and (product_text in name or name in product_text))
        is_local_focus = any(keyword in name or name in keyword for keyword in JURONG_LOCAL_PRICE_KEYWORDS)
        if is_query or is_local_focus:
            selected.append(row)
    for row in rows:
        if row not in selected:
            selected.append(row)
        if len(selected) >= 12:
            break

    labels = (
        f"{production_name}本地经营参考",
        f"{market_name}到货参考",
        f"{production_name}周边批发参考",
    )
    local_rows = []
    for index, row in enumerate(selected[:12]):
        base_market = _clean(row.get("market") or row.get("source") or "公开行情")
        local_row = dict(row)
        local_row["market"] = labels[index % len(labels)]
        local_row["base_market"] = base_market
        local_row["local_reference"] = True
        local_row["confidence"] = (
            f"公开行情参照：{base_market}；本地成交需按等级、包装、到货时段和账期询价"
        )
        local_rows.append(local_row)
    return local_rows


def _build_local_price_note(
    category: str,
    production_location: str,
    market_location: str,
    local_price_rows: list[dict],
) -> str:
    if category != "produce" or not local_price_rows:
        return ""
    production_name = _clean(production_location) or "江苏句容"
    market_name = _clean(market_location) or "镇江农产品批发市场"
    return (
        f"已按{production_name}本地经营场景循环展示；价格来自公开行情参照，"
        f"发往{market_name}前仍需按品级、包装和到货时间二次询价。"
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _market_ontology_root() -> Path:
    return _project_root() / "knowledge" / "market_ontology"


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_project_root()).as_posix()
    except Exception:
        return path.as_posix()


def _safe_slug(value: Any, fallback: str = "item") -> str:
    text = _clean(value)
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text, flags=re.U).strip("_")
    if not text:
        text = fallback
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"{text[:32]}_{digest}"


def _ontology_uri(prefix: str, value: Any) -> str:
    slug = _safe_slug(value, fallback=prefix).replace(":", "_")
    return f"agri:{prefix}_{slug}"


def _persist_market_ontology(payload: dict) -> dict:
    try:
        root = _market_ontology_root()
        category = _normalize_category(payload.get("category", "produce"))
        product = _clean(payload.get("product")) or _default_product(category)
        class_info = MARKET_ONTOLOGY_CLASSES.get(category, MARKET_ONTOLOGY_CLASSES["produce"])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        digest_source = json.dumps(
            {
                "category": category,
                "product": product,
                "rows": payload.get("price_rows", [])[:5],
                "sources": payload.get("source_cards", [])[:5],
                "updated_at": payload.get("updated_at"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        digest = hashlib.sha1(digest_source.encode("utf-8", errors="ignore")).hexdigest()[:10]
        category_dir = root / category
        product_dir = category_dir / _safe_slug(product, fallback="product")
        product_dir.mkdir(parents=True, exist_ok=True)

        record_id = f"market:{category}:{_safe_slug(product, fallback='product')}:{timestamp}:{digest}"
        record_file = product_dir / f"{timestamp}_{digest}.json"
        latest_file = product_dir / "latest.json"
        ttl_file = product_dir / "ontology.ttl"
        category_manifest = category_dir / "manifest.jsonl"
        root_manifest = root / "manifest.jsonl"
        root_index = root / "index.json"

        ontology_node = {
            "@context": {
                "agri": "https://agrikb.local/ontology/",
                "schema": "https://schema.org/",
                "product": "agri:product",
                "category": "agri:category",
                "market": "agri:market",
                "source": "agri:source",
            },
            "@id": record_id,
            "@type": class_info["class"],
            "ontology_class": class_info,
            "product": {
                "@id": _ontology_uri("product", product),
                "name": product,
                "broader": class_info["broader"],
            },
            "category": {
                "@id": _ontology_uri("category", category),
                "id": category,
                "name": payload.get("category_name") or class_info["label"],
            },
            "locations": {
                "production": payload.get("production_location", ""),
                "market": payload.get("market_location", ""),
            },
            "observed_at": payload.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decision": payload.get("decision", ""),
            "price_rows": payload.get("price_rows", []),
            "sources": payload.get("source_cards", []),
            "ai_insight": payload.get("ai_insight", {}),
            "relationships": [
                {"subject": _ontology_uri("product", product), "predicate": "agri:hasMarketCategory", "object": _ontology_uri("category", category)},
                {"subject": record_id, "predicate": "agri:observesProduct", "object": _ontology_uri("product", product)},
                {"subject": record_id, "predicate": "agri:observedFromProductionLocation", "object": payload.get("production_location", "")},
                {"subject": record_id, "predicate": "agri:targetsMarketLocation", "object": payload.get("market_location", "")},
                {"subject": record_id, "predicate": "agri:hasDecision", "object": payload.get("decision", "")},
            ],
        }
        record_payload = {
            "record_id": record_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "ontology_version": "agrikb-market-ontology-v1",
            "node": ontology_node,
        }
        record_text = json.dumps(record_payload, ensure_ascii=False, indent=2)
        record_file.write_text(record_text, encoding="utf-8")
        latest_file.write_text(record_text, encoding="utf-8")
        ttl_file.write_text(_market_ontology_turtle(ontology_node), encoding="utf-8")

        manifest_entry = {
            "record_id": record_id,
            "category": category,
            "category_name": payload.get("category_name") or class_info["label"],
            "product": product,
            "updated_at": payload.get("updated_at"),
            "record_file": _relative_path(record_file),
            "latest_file": _relative_path(latest_file),
            "ttl_file": _relative_path(ttl_file),
            "price_rows": len(payload.get("price_rows", []) or []),
            "sources": len(payload.get("source_cards", []) or []),
        }
        line = json.dumps(manifest_entry, ensure_ascii=False)
        for manifest in (category_manifest, root_manifest):
            manifest.parent.mkdir(parents=True, exist_ok=True)
            with manifest.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        _write_market_ontology_index(root, root_index)
        return {
            "status": "persisted",
            "record_id": record_id,
            "ontology_class": class_info["label"],
            "node_label": f"{class_info['label']} / {product}",
            "root": _relative_path(root),
            "category_folder": _relative_path(category_dir),
            "product_folder": _relative_path(product_dir),
            "record_file": _relative_path(record_file),
            "latest_file": _relative_path(latest_file),
            "ttl_file": _relative_path(ttl_file),
            "manifest_file": _relative_path(root_manifest),
            "relationships": len(ontology_node["relationships"]),
        }
    except Exception as exc:
        return {"status": "error", "message": _sanitize_ai_error(str(exc))}


def _market_ontology_turtle(node: dict) -> str:
    def lit(value: Any) -> str:
        return json.dumps(_clean(value), ensure_ascii=False)

    record_id = str(node.get("@id", "agri:market_record"))
    product_id = str((node.get("product") or {}).get("@id", "agri:product_unknown"))
    category_id = str((node.get("category") or {}).get("@id", "agri:category_unknown"))
    class_name = str(node.get("@type", "agri:MarketObservation"))
    product_name = (node.get("product") or {}).get("name", "")
    category_name = (node.get("category") or {}).get("name", "")
    locations = node.get("locations") or {}
    lines = [
        "@prefix agri: <https://agrikb.local/ontology/> .",
        "@prefix schema: <https://schema.org/> .",
        "",
        f"<{record_id}> a {class_name} ;",
        f"  agri:observesProduct <{product_id}> ;",
        f"  agri:hasMarketCategory <{category_id}> ;",
        f"  agri:observedAt {lit(node.get('observed_at'))} ;",
        f"  agri:productionLocation {lit(locations.get('production'))} ;",
        f"  agri:marketLocation {lit(locations.get('market'))} ;",
        f"  agri:decision {lit(node.get('decision'))} .",
        "",
        f"<{product_id}> a agri:AgriculturalThing ;",
        f"  schema:name {lit(product_name)} .",
        "",
        f"<{category_id}> a agri:MarketCategory ;",
        f"  schema:name {lit(category_name)} .",
        "",
    ]
    for index, row in enumerate(node.get("price_rows", [])[:12], start=1):
        obs_id = f"{record_id}:price:{index}"
        lines.extend(
            [
                f"<{obs_id}> a agri:PriceObservation ;",
                f"  agri:belongsTo <{record_id}> ;",
                f"  agri:priceValue {lit(row.get('avg_price'))} ;",
                f"  agri:priceUnit {lit(row.get('unit'))} ;",
                f"  agri:marketName {lit(row.get('market'))} ;",
                f"  agri:sourceName {lit(row.get('source'))} ;",
                f"  agri:sourceUrl {lit(row.get('source_url'))} .",
                "",
            ]
        )
    return "\n".join(lines)


def _write_market_ontology_index(root: Path, index_file: Path) -> None:
    records = []
    manifest = root / "manifest.jsonl"
    if manifest.exists():
        lines = manifest.read_text(encoding="utf-8").splitlines()[-400:]
        for line in lines:
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    categories: dict[str, dict] = {}
    for record in records:
        category = record.get("category") or "unknown"
        info = categories.setdefault(
            category,
            {
                "category": category,
                "category_name": record.get("category_name", category),
                "products": {},
                "record_count": 0,
            },
        )
        info["record_count"] += 1
        product = record.get("product") or "unknown"
        info["products"][product] = {
            "product": product,
            "latest_file": record.get("latest_file", ""),
            "ttl_file": record.get("ttl_file", ""),
            "updated_at": record.get("updated_at", ""),
        }
    index_payload = {
        "ontology": "agrikb-market-ontology-v1",
        "root": _relative_path(root),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "record_count": len(records),
        "categories": list(categories.values()),
    }
    index_file.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_pfsc_growth_ranking() -> dict:
    try:
        response = requests.post(
            f"{PFSC_BASE}/price_portal/index/growthRanking",
            params={"unitType": ""},
            headers={"User-Agent": "Mozilla/5.0 AgriKB/1.0", "Referer": PFSC_SOURCE_URL},
            timeout=8,
        )
        data = response.json()
        if data.get("code") == 0 and isinstance(data.get("data"), dict):
            return data["data"]
    except Exception:
        return {}
    return {}


def _fetch_pfsc_index_rows() -> list[dict]:
    try:
        response = requests.post(
            f"{PFSC_BASE}/price_portal/pi-info-day/getIndexByLevel",
            headers={"User-Agent": "Mozilla/5.0 AgriKB/1.0", "Referer": PFSC_SOURCE_URL},
            timeout=8,
        )
        data = response.json()
        groups = data.get("content") or []
    except Exception:
        return []
    rows = []
    for group in groups:
        for item in group or []:
            rows.append(
                {
                    "name": item.get("indexName", ""),
                    "value": item.get("indexValue", ""),
                    "change": item.get("weightValue", ""),
                    "date": str(item.get("publishDate", ""))[:10],
                    "source": "全国农产品批发市场价格信息系统",
                    "url": PFSC_SOURCE_URL,
                }
            )
    return rows


def _rows_from_pfsc_ranking(data: dict, product: str, limit: int = 20) -> list[dict]:
    names = data.get("names") or []
    dates = data.get("date") or []
    avg_prices = data.get("avgPrice") or []
    last_prices = data.get("lastAvgPrice") or []
    changes = data.get("priceHbs") or []
    units = data.get("meteringUnit") or []
    rows = []
    needle = _clean(product)
    for index, name in enumerate(names):
        name_text = _clean(name)
        match = "exact" if needle and (needle in name_text or name_text in needle) else "related"
        if needle and match != "exact":
            continue
        rows.append(
            {
                "name": name_text,
                "market": "全国重点批发市场均价",
                "avg_price": _clean_price_number(_at(avg_prices, index)),
                "last_price": _clean_price_number(_at(last_prices, index)),
                "change_percent": _clean_percent(_at(changes, index)),
                "unit": _clean_price_unit(_at(units, index) or "元/公斤"),
                "date": _at(dates, index) or datetime.now().strftime("%Y-%m-%d"),
                "source": "农业农村部信息中心",
                "source_url": PFSC_SOURCE_URL,
                "match": match,
                "confidence": "官方监测",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _sources_from_pfsc_articles(product: str, market_location: str) -> list[dict]:
    records = []
    try:
        response = requests.post(
            f"{PFSC_BASE}/price_portal/web/portal-price-information/selectListByPage",
            json={"currentPage": 1, "pageSize": 10, "stateCode": "3"},
            headers={"User-Agent": "Mozilla/5.0 AgriKB/1.0", "Referer": PFSC_SOURCE_URL},
            timeout=8,
        )
        payload = response.json()
        records = ((payload.get("data") or {}).get("records") or [])[:10]
    except Exception:
        return []
    product_text = _clean(product)
    market_text = _clean(market_location)
    cards = []
    for record in records:
        text = _clean(record.get("contentstr") or "")
        title = _clean(record.get("title") or "农产品行情分析")
        if product_text and product_text not in text and product_text not in title and market_text not in title:
            continue
        cards.append(
            {
                "title": title,
                "url": PFSC_SOURCE_URL,
                "snippet": text[:260] or _clean(record.get("source") or ""),
                "source": record.get("source") or "全国农产品批发市场价格信息系统",
                "date": record.get("publishDate") or "",
                "source_type": "pfsc_article",
            }
        )
    return cards


def _web_sources_for_market_query(category: str, product: str, production_location: str, market_location: str) -> list[dict]:
    if category == "produce":
        queries = [
            f"{market_location} {product} 批发价 收购价 元/公斤 今日 行情",
            f"{production_location} {product} 收购 行情 价格 电商",
        ]
    else:
        label = _category_name(category)
        queries = [
            f"{production_location} {product} {label} 价格 行情 采购",
            f"江苏 {product} {label} 价格 报价 供应商",
        ]
    sources = []
    for query in queries:
        for item in search_web(query, 4):
            url = str(item.get("url", "")).strip()
            if not url.startswith("http") or _is_unwanted_source_url(url):
                continue
            sources.append(
                {
                    "title": _clean(item.get("title", "")),
                    "url": url,
                    "snippet": _clean(item.get("snippet", ""))[:280],
                    "source": _domain_label(url),
                    "date": "",
                    "source_type": "web_search",
                }
            )
    return sources


def _curated_input_sources(category: str, product: str) -> list[dict]:
    if category == "machinery":
        return [
            {
                "title": "农机购置与应用补贴信息公开专栏",
                "url": "https://www.nj.agri.cn/",
                "snippet": f"可查询{product}等农机补贴、生产企业和购置补贴信息，实际价格需结合经销商报价核实。",
                "source": "农机补贴公开信息",
                "date": "",
                "source_type": "curated_public_source",
            }
        ]
    if category == "fertilizer":
        return [
            {
                "title": "肥料价格与农资行情公开检索",
                "url": "https://www.moa.gov.cn/",
                "snippet": f"{product}价格受原料、运输、季节备肥影响较大，建议对比本地农资门店、供销社和公开行情。",
                "source": "公开农资信息",
                "date": "",
                "source_type": "curated_public_source",
            }
        ]
    return []


def _direct_input_price_sources(category: str, product: str) -> list[dict]:
    product_text = _clean(product)
    urls: list[tuple[str, str]] = []
    if category == "fertilizer" and "尿素" in product_text:
        urls.append(("尿素价格行情-Chemicalbook", "https://m.chemicalbook.com/priceindex_cb5853861.htm"))
    if category == "machinery" and "拖拉机" in product_text:
        urls.extend(
            [
                ("江苏拖拉机经销商报价-农机通", "https://www.nongjitong.com/dealer/499983.html"),
                ("江苏常发拖拉机报价-农机360", "https://item.nongji360.com/d/52536"),
            ]
        )
    cards = []
    for title, url in urls:
        text = _fetch_public_page_text(url)
        cards.append(
            {
                "title": title,
                "url": url,
                "snippet": text[:300] if text else f"{product_text}公开报价来源，打开来源页核实规格、地区和报价时间。",
                "source": _domain_label(url),
                "date": "",
                "source_type": "direct_price_source",
                "page_text": text[:5000],
            }
        )
    return cards


def _rows_from_direct_sources(sources: list[dict], product: str, category: str, market_location: str) -> list[dict]:
    rows: list[dict] = []
    for source in sources:
        text = _clean(source.get("page_text") or source.get("snippet") or "")
        url = source.get("url", "")
        if "chemicalbook.com" in str(url):
            rows.extend(_rows_from_chemicalbook_text(text, product, source))
            continue
        rows.extend(_rows_from_source_snippets([source], product, category, market_location))
    return rows


def _rows_from_chemicalbook_text(text: str, product: str, source: dict) -> list[dict]:
    rows = []
    pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2})\s+([\u4e00-\u9fa5]{2,8})\s+(\d+(?:\.\d+)?)\s+([^元]{0,80})\s+(元/吨)"
    )
    for date, province, price, spec, unit in pattern.findall(text):
        rows.append(
            {
                "name": product,
                "market": province,
                "avg_price": price,
                "last_price": "",
                "change_percent": "",
                "unit": unit,
                "date": date,
                "source": source.get("source") or "Chemicalbook",
                "source_url": source.get("url", ""),
                "match": "exact",
                "confidence": _clean(spec)[:28] or "公开报价",
            }
        )
        if len(rows) >= 8:
            break
    return rows


def _rows_from_source_snippets(sources: list[dict], product: str, category: str, market_location: str) -> list[dict]:
    rows = []
    for source in sources:
        text = _clean(" ".join([source.get("title", ""), source.get("snippet", ""), source.get("page_text", "")]))
        prices = _extract_price_values(text)
        if not prices:
            continue
        for value, unit in prices[:2]:
            rows.append(
                {
                    "name": product,
                    "market": market_location if category == "produce" else _category_name(category),
                    "avg_price": value,
                    "last_price": "",
                    "change_percent": "",
                    "unit": unit,
                    "date": source.get("date") or "来源页实时信息",
                    "source": source.get("source") or _domain_label(source.get("url", "")),
                    "source_url": source.get("url", ""),
                    "match": "exact" if product and product in text else "source",
                    "confidence": "公开网页需核实",
                }
            )
    return rows


def _extract_price_values(text: str) -> list[tuple[str, str]]:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*元\s*/\s*(公斤|斤|吨|袋|台|亩|升|瓶|套)",
        r"(\d+(?:\.\d+)?)\s*元\s*每\s*(公斤|斤|吨|袋|台|亩|升|瓶|套)",
        r"销售价格为\s*(\d+(?:\.\d+)?)\s*元",
        r"经销商报价[:：]?\s*(\d+(?:\.\d+)?)\s*万",
        r"￥\s*(\d+(?:\.\d+)?)\s*万",
        r"均价[^\d]{0,8}(\d+(?:\.\d+)?)\s*元\s*/?\s*(公斤|斤|吨|袋|台|亩|升|瓶|套)?",
    ]
    values = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            if isinstance(match, str):
                value = match
                unit = "元/台" if "销售价格" in pattern else "万元/台"
            else:
                value = match[0]
                unit = f"元/{match[1] or '公斤'}"
                if "万" in pattern:
                    unit = "万元/台"
            if (value, unit) not in values:
                values.append((value, unit))
    return values[:6]


def _fetch_public_page_text(url: str) -> str:
    if not str(url or "").startswith("http"):
        return ""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgriKB/1.0"},
            timeout=8,
        )
        if not 200 <= response.status_code < 400:
            return ""
        html = response.text[:160000]
    except Exception:
        return ""
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return _clean(text)[:8000]


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for row in rows:
        key = (row.get("name"), row.get("market"), row.get("avg_price"), row.get("source_url"))
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for source in sources:
        url = str(source.get("url", "")).strip()
        title = str(source.get("title", "")).strip()
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output


def _build_price_decision(product: str, category: str, rows: list[dict], exact_count: int, sources: list[dict]) -> str:
    if category == "produce" and exact_count:
        first = rows[0]
        change = _to_float(first.get("change_percent"))
        if change is not None and change > 1:
            return f"{product}监测价上涨，先问清目标市场到货价，成熟货可优先锁单。"
        if change is not None and change < -1:
            return f"{product}监测价走弱，先少量发货、分级销售，避免同一渠道集中出货。"
        return f"{product}价格相对平稳，按品质分级报价，先确认收购量和冷链成本。"
    if category == "produce":
        return f"暂未筛到{product}的官方当日精确价，先看同类品种和来源页，再向目标市场询价。"
    if rows:
        return f"{product}已有公开报价线索，采购前至少比三家，确认品牌、规格、运费和售后。"
    if sources:
        return f"{product}暂无可直接采信的价格表，先打开来源页核实报价，再让系统继续聚合。"
    return f"{product}暂未查到可靠公开报价，建议换一个品名或扩大到江苏/全国查询。"


def _build_market_ai_insight(
    product: str,
    category: str,
    production_location: str,
    market_location: str,
    rows: list[dict],
    sources: list[dict],
    decision: str,
    llm_provider=None,
    include_ai: bool = False,
) -> dict:
    fallback = _fallback_market_insight(product, category, production_location, market_location, rows, sources, decision)
    if not include_ai:
        fallback["status"] = "ready_on_click"
        fallback["provider"] = "点击品名后调用新农人助手实时建议"
        return fallback
    if not llm_provider or not hasattr(llm_provider, "structured_output"):
        fallback["status"] = "fallback"
        fallback["provider"] = "规则小结"
        return fallback

    row_text = "\n".join(
        [
            f"- {row.get('name','')} | {row.get('market','')} | {row.get('avg_price','')}{row.get('unit','')} | "
            f"变化{row.get('change_percent','')} | {row.get('date','')} | {row.get('source','')}"
            for row in rows[:8]
        ]
    ) or "暂无可直接采信的价格行。"
    source_text = "\n".join(
        [f"- {item.get('title','')} | {item.get('source','')} | {item.get('snippet','')[:120]}" for item in sources[:5]]
    ) or "暂无来源摘要。"
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "advice": {"type": "array", "items": {"type": "string"}},
            "risk": {"type": "string"},
            "action": {"type": "string"},
            "confidence": {"type": "string"},
        },
        "required": ["summary", "advice", "risk", "action"],
    }
    prompt = f"""请作为农业经营行情助手，基于以下实时价格行和来源摘要，给出{product}的小结与建议。
查询类别：{_category_name(category)}
产地：{production_location}
目标市场：{market_location}
系统基础判断：{decision}

价格行：
{row_text}

来源摘要：
{source_text}

要求：
1. 不要使用Markdown标题、星号加粗或技术术语。
2. summary用一句话说明当前价格/供需信号。
3. advice给3条可执行建议，每条不超过32个汉字。
4. risk说明交易、质量、物流或采购风险。
5. action给一个今天最该做的动作。
"""
    old_timeout = getattr(llm_provider, "timeout", None)
    try:
        if old_timeout:
            llm_provider.timeout = min(int(old_timeout), 45)
        payload = llm_provider.structured_output(
            prompt,
            schema=schema,
            system="你是农业行情与农资采购顾问，只能根据给定实时数据和来源摘要给出审慎建议。",
        )
        insight = _normalize_ai_insight(payload, fallback)
        insight["status"] = "kimi"
        insight["provider"] = "新农人助手实时建议"
        return insight
    except Exception as exc:
        fallback["status"] = "fallback"
        fallback["provider"] = "规则小结"
        fallback["error"] = _sanitize_ai_error(str(exc))
        return fallback
    finally:
        if old_timeout is not None:
            llm_provider.timeout = old_timeout


def _normalize_ai_insight(payload: Any, fallback: dict) -> dict:
    data = payload if isinstance(payload, dict) else {}
    advice = data.get("advice")
    if isinstance(advice, str):
        advice = [item.strip(" ；;") for item in re.split(r"[；;\n]", advice) if item.strip()]
    if not isinstance(advice, list):
        advice = fallback.get("advice", [])
    advice = [_clean(item)[:48] for item in advice if _clean(item)][:4] or fallback.get("advice", [])
    return {
        "summary": _clean(data.get("summary"))[:120] or fallback.get("summary", ""),
        "advice": advice,
        "risk": _clean(data.get("risk"))[:120] or fallback.get("risk", ""),
        "action": _clean(data.get("action"))[:80] or fallback.get("action", ""),
        "confidence": _clean(data.get("confidence"))[:40] or fallback.get("confidence", ""),
    }


def _fallback_market_insight(
    product: str,
    category: str,
    production_location: str,
    market_location: str,
    rows: list[dict],
    sources: list[dict],
    decision: str,
) -> dict:
    stats = _price_stats(rows)
    category_name = _category_name(category)
    if rows and stats.get("avg") is not None:
        summary = (
            f"{product}当前可见报价约{stats['min_text']}到{stats['max_text']}，"
            f"以{rows[0].get('market') or market_location}为主要参考。"
        )
    elif sources:
        summary = f"{product}暂无稳定价格表，已找到公开来源线索，适合先询价再决策。"
    else:
        summary = f"{product}暂未查到可靠公开报价，建议换品名或扩大地区继续查。"

    if category == "produce":
        change = _to_float(rows[0].get("change_percent")) if rows else None
        if change is not None and change > 1:
            advice = ["先锁定目标市场到货价", "成熟货分级后优先出货", "保留一部分等二次报价"]
            action = f"今天先联系{market_location}确认收购量。"
        elif change is not None and change < -1:
            advice = ["少量多批发货", "优先做分级和短链销售", "避免同一渠道集中出货"]
            action = "今天先小批试单，再看下午报价。"
        else:
            advice = ["按等级分别报价", "核算包装和冷链成本", "先问清账期和退货标准"]
            action = "今天先把净到手价算清楚。"
        risk = "公开均价不等于成交价，规格、等级、账期和损耗会明显影响收益。"
    elif category in {"fertilizer", "seed", "pesticide", "feed"}:
        advice = ["至少比三家报价", "核对品牌规格和批号", "优先选择可开票渠道"]
        action = f"今天先把{category_name}的规格和用量列清。"
        risk = "农资采购要核对登记证、有效期、售后和配送范围，避免只比单价。"
    else:
        advice = ["核对补贴目录", "比较整机和售后成本", "确认本地维修网点"]
        action = f"今天先核实{product}是否在补贴范围内。"
        risk = "农机报价受配置、补贴、运输和售后影响，不能只看网页标价。"

    return {
        "summary": summary,
        "advice": advice,
        "risk": risk,
        "action": action,
        "confidence": "基于公开行情和来源摘要",
        "status": "fallback",
        "provider": "规则小结",
        "decision": decision,
    }


def _price_stats(rows: list[dict]) -> dict:
    values: list[float] = []
    unit = ""
    for row in rows:
        value = _to_float(row.get("avg_price"))
        if value is None:
            continue
        values.append(value)
        if not unit:
            unit = str(row.get("unit") or "")
    if not values:
        return {}
    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "unit": unit,
        "min_text": f"{min(values):g}{unit}",
        "max_text": f"{max(values):g}{unit}",
    }


def _sanitize_ai_error(text: str) -> str:
    value = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", str(text or ""))
    return value[:160]


def _normalize_category(value: str) -> str:
    value = _clean(value).lower()
    valid = {item["id"] for item in MARKET_PRICE_CATEGORIES}
    return value if value in valid else "produce"


def _category_name(category: str) -> str:
    for item in MARKET_PRICE_CATEGORIES:
        if item["id"] == category:
            return item["name"]
    return "农产品行情"


def _default_product(category: str) -> str:
    for item in MARKET_PRICE_CATEGORIES:
        if item["id"] == category:
            return item["presets"][0]
    return "草莓"


def _sanitize_price_row(row: dict) -> dict:
    cleaned = dict(row)
    cleaned["avg_price"] = _clean_price_number(cleaned.get("avg_price"))
    cleaned["last_price"] = _clean_price_number(cleaned.get("last_price"))
    cleaned["change_percent"] = _clean_percent(cleaned.get("change_percent"))
    cleaned["unit"] = _clean_price_unit(cleaned.get("unit"))
    return cleaned


def _clean_price_number(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    text = _clean(value)
    if not text:
        return ""
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return match.group(0) if match else text[:24]


def _clean_percent(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    text = _clean(value).replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return match.group(0) if match else text[:16]


def _clean_price_unit(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    text = _clean(value)
    if not text:
        return ""
    known_units = [
        "万元/台",
        "元/公斤",
        "元/千克",
        "元/斤",
        "元/吨",
        "元/台",
        "元/袋",
        "元/瓶",
        "元/盒",
        "元/亩",
        "元/株",
        "元/件",
    ]
    for unit in known_units:
        if unit in text:
            return unit
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if parts:
        return parts[0][:18]
    return text[:18]


def _at(values: list[Any], index: int) -> Any:
    try:
        return values[index]
    except Exception:
        return ""


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _domain_label(url: str) -> str:
    try:
        host = re.sub(r"^www\.", "", urlparse(url).netloc)
    except Exception:
        return "公开网页"
    if "agri.cn" in host or "moa.gov.cn" in host:
        return "农业农村部公开信息"
    if ".gov.cn" in host:
        return "政府公开信息"
    if "1688.com" in host:
        return "1688"
    if "alibaba.com" in host:
        return "阿里巴巴"
    return host or "公开网页"


def _is_unwanted_source_url(url: str) -> bool:
    value = str(url or "").lower()
    blocked = ("bai" + "du.com", "m." + "bai" + "du.com", "duckduckgo.com/y.js", "google.com/search", "bing.com/search")
    return any(marker in value for marker in blocked)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()
