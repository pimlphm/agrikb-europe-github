from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urlparse

from src.backend.headline_recommender import recommend_headlines
from src.backend.web_search import search_web


COMPETITION_THEME = (
    "2026 江苏句容市 福地青年英才 创业大赛 福地句才 共创容光 "
    "农业 新农人 科技 人才 招商 新媒体 乡村振兴"
)
COMPETITION_CACHE_TTL_SECONDS = 8 * 60
_COMPETITION_CACHE: dict[str, tuple[float, dict]] = {}

COMPETITION_CATEGORIES = [
    {
        "id": "agri_startup",
        "label": "农业创业",
        "focus": "农业项目、新农人、家庭农场、合作社、乡村产业",
        "queries": ["农业创业 新农人 乡村产业 项目", "家庭农场 合作社 青年创业 农产品"],
    },
    {
        "id": "agri_tech",
        "label": "科技农业",
        "focus": "数智农业、设施农业、农机装备、物联网、AI农业",
        "queries": ["农业科技 数智农业 人工智能 农业项目", "设施农业 物联网 农机装备 科技成果"],
    },
    {
        "id": "youth_talent",
        "label": "青年人才",
        "focus": "青年英才、大学生创业、人才政策、创业服务",
        "queries": ["青年英才 创业大赛 人才政策 农业", "大学生返乡创业 新农人 人才服务"],
    },
    {
        "id": "investment",
        "label": "招商孵化",
        "focus": "招商引智、孵化培育、园区载体、项目落地",
        "queries": ["招商引智 孵化培育 农业项目 江苏句容", "园区 产业链 招商 农业科技"],
    },
    {
        "id": "new_media",
        "label": "新媒体助农",
        "focus": "直播电商、短视频、品牌传播、农产品上行",
        "queries": ["新媒体 助农 直播电商 农产品 青年创业", "短视频 农产品品牌 新农人 电商"],
    },
    {
        "id": "policy_funding",
        "label": "政策资金",
        "focus": "补贴、创业扶持、贷款、项目申报、公共服务",
        "queries": ["创业扶持 补贴 项目申报 农业 江苏句容", "人社 农业农村 创业贷款 青年人才"],
    },
]


def build_competition_headline_intelligence(
    location: str = "江苏句容",
    llm_provider=None,
    force_refresh: bool = False,
) -> dict:
    location = _clean(location) or "江苏句容"
    if "句容" not in location:
        location = "江苏句容"
    cache_key = f"competition|{location}"
    now = time.time()
    if not force_refresh:
        cached = _COMPETITION_CACHE.get(cache_key)
        if cached and now - cached[0] < COMPETITION_CACHE_TTL_SECONDS:
            return cached[1]

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_build_category_headlines, category, location): category["id"]
            for category in COMPETITION_CATEGORIES
        }
        category_map = {}
        for future in as_completed(futures):
            category = future.result()
            category_map[category["id"]] = category

    categories = [category_map.get(category["id"]) for category in COMPETITION_CATEGORIES]
    categories = [category for category in categories if category]
    all_items = [item for category in categories for item in category.get("items", [])]
    trend = _build_trend_analysis(categories, all_items, location, llm_provider)
    payload = {
        "theme": "2026年江苏句容市“福地青年英才”创业大赛",
        "location": location,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "UC-style multi-source crawl + BM25/MMR rerank + AI trend analysis",
        "categories": categories,
        "trend": trend,
        "source_note": "围绕江苏句容青年英才创业大赛主题实时聚合；打开来源页后以发布单位原文为准。",
    }
    _COMPETITION_CACHE[cache_key] = (now, payload)
    return payload


def _build_category_headlines(category: dict, location: str) -> dict:
    candidates: list[dict] = []
    for query_tail in category.get("queries", []):
        query = f"{COMPETITION_THEME} {location} {category['focus']} {query_tail}"
        for item in search_web(query, 8):
            normalized = _normalize_competition_item(item, category, location)
            if normalized and _is_theme_related(normalized, category, location):
                candidates.append(normalized)
    candidates.extend(_curated_competition_items(category, location))
    candidates = _dedupe_items(candidates)
    ranked = recommend_headlines(
        candidates,
        query=f"{COMPETITION_THEME} {category['focus']} {location}",
        production_name=location,
        market_name="江苏句容农业创业与人才项目",
        limit=14,
    )
    ranked = [_normalize_competition_item(item, category, location) for item in ranked]
    ranked = [item for item in ranked if item][:10]
    return {
        "id": category["id"],
        "label": category["label"],
        "focus": category["focus"],
        "hot_score": round(sum(float(item.get("score", 0.7)) for item in ranked) / max(1, len(ranked)), 2),
        "items": ranked,
    }


def _normalize_competition_item(item: dict, category: dict, location: str) -> dict:
    title = _clean(item.get("title") or item.get("name") or item.get("snippet") or "")
    snippet = _clean(item.get("snippet") or item.get("summary") or item.get("description") or "")
    if not title:
        return {}
    url = str(item.get("url") or item.get("source_url") or "").strip()
    text = f"{title} {snippet}"
    return {
        "title": title[:88],
        "snippet": snippet[:220],
        "url": url,
        "source": _source_label(url, item.get("source") or item.get("source_type") or ""),
        "category": category["label"],
        "reason": _reason_for_competition_item(text, category, location),
        "score": _competition_score(text, category, location),
        "published_at": _clean(item.get("date") or item.get("published_at") or item.get("time") or ""),
    }


def _is_theme_related(item: dict, category: dict, location: str) -> bool:
    text = f"{item.get('title', '')} {item.get('snippet', '')}"
    core_hits = _count_hits(text, ["句容", "福地", "青年", "英才", "创业", "大赛", "农业", "新农人", "乡村", "人才"])
    category_hits = _count_hits(text, re.split(r"[、,，\s]+", category.get("focus", "")))
    location_hit = location in text or "句容" in text or "镇江" in text or "江苏" in text
    return location_hit and (core_hits >= 2 or category_hits >= 1)


def _competition_score(text: str, category: dict, location: str) -> float:
    score = 0.8
    score += _count_hits(text, ["句容", "福地青年英才", "创业大赛", "青年英才", "福地"]) * 0.42
    score += _count_hits(text, ["农业", "新农人", "农产品", "乡村振兴", "合作社", "家庭农场"]) * 0.28
    score += _count_hits(text, re.split(r"[、,，\s]+", category.get("focus", ""))) * 0.24
    score += _count_hits(text, ["2026", "申报", "报名", "扶持", "补贴", "项目", "孵化", "科技", "电商"]) * 0.14
    if location and location in text:
        score += 0.35
    return round(min(score, 5.0), 3)


def _reason_for_competition_item(text: str, category: dict, location: str) -> str:
    if "申报" in text or "报名" in text or "通知" in text:
        return "申报窗口"
    if "科技" in text or "数智" in text or "人工智能" in text:
        return "科技项目"
    if "电商" in text or "直播" in text or "短视频" in text:
        return "新媒体助农"
    if "招商" in text or "孵化" in text or "园区" in text:
        return "招商孵化"
    if "人才" in text or "青年" in text:
        return "青年人才"
    if "农业" in text or "新农人" in text:
        return "农业创业"
    return category["label"]


def _build_trend_analysis(categories: list[dict], items: list[dict], location: str, llm_provider=None) -> dict:
    fallback = _fallback_trend(categories, items, location)
    if not llm_provider or not hasattr(llm_provider, "structured_output") or not items:
        return fallback
    item_text = "\n".join(
        f"- [{item.get('category')}] {item.get('title')} | {item.get('snippet')[:90]}"
        for item in items[:30]
    )
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "signals": {"type": "array", "items": {"type": "string"}},
            "opportunity": {"type": "string"},
            "action": {"type": "string"},
            "risk": {"type": "string"},
        },
        "required": ["summary", "signals", "opportunity", "action", "risk"],
    }
    prompt = f"""请围绕2026年江苏句容市“福地青年英才”创业大赛，分析以下实时聚合头条的趋势。
要求：
1. 只讨论农业、新农人、科技、人才、招商、新媒体助农相关内容。
2. 输出面向参赛项目和县域农业服务平台的趋势判断。
3. 不使用Markdown标题，不要写后台技术词。

地区：{location}
头条：
{item_text}
"""
    old_timeout = getattr(llm_provider, "timeout", None)
    try:
        if old_timeout:
            llm_provider.timeout = min(int(old_timeout), 35)
        data = llm_provider.structured_output(
            prompt,
            schema=schema,
            system="你是农业创业大赛路演情报分析师，只根据给定头条做趋势归纳和经营建议。",
        )
        if not isinstance(data, dict):
            return fallback
        signals = data.get("signals")
        if isinstance(signals, str):
            signals = [item.strip() for item in re.split(r"[；;\n]", signals) if item.strip()]
        if not isinstance(signals, list):
            signals = fallback["signals"]
        return {
            "summary": _clean(data.get("summary"))[:160] or fallback["summary"],
            "signals": [_clean(item)[:64] for item in signals if _clean(item)][:4] or fallback["signals"],
            "opportunity": _clean(data.get("opportunity"))[:140] or fallback["opportunity"],
            "action": _clean(data.get("action"))[:120] or fallback["action"],
            "risk": _clean(data.get("risk"))[:140] or fallback["risk"],
            "provider": "新农人助手趋势分析",
        }
    except Exception:
        return fallback
    finally:
        if old_timeout is not None:
            llm_provider.timeout = old_timeout


def _fallback_trend(categories: list[dict], items: list[dict], location: str) -> dict:
    category_counts = {category["label"]: len(category.get("items", [])) for category in categories}
    leading = sorted(category_counts.items(), key=lambda item: item[1], reverse=True)[:2]
    leading_text = "、".join(label for label, _ in leading) or "农业创业、科技农业"
    source_count = len({item.get("url") or item.get("title") for item in items})
    return {
        "summary": f"{location}创业大赛相关热度集中在{leading_text}，农业项目需要把人才、技术、渠道和政策申报放在同一套方案里讲清楚。",
        "signals": [
            "农业项目更看重可落地的场景和订单闭环",
            "科技农业需要同时证明降本、提质和可复制",
            "青年人才项目要把团队能力和本地产业链结合起来",
            "新媒体助农正在从单次带货转向品牌和渠道运营",
        ],
        "opportunity": f"可把{location}草莓、茶叶、福桃、蔬菜等特色产业作为样板，组合数智服务、直播电商和产销对接。",
        "action": "参赛材料优先准备项目场景、客户对象、收入模型、政策匹配和三个月落地计划。",
        "risk": f"已聚合{source_count}条公开线索，正式申报仍要以江苏句容市人社、人才和农业农村等部门原文为准。",
        "provider": "新农人助手趋势分析",
    }


def _curated_competition_items(category: dict, location: str) -> list[dict]:
    dedicated = _category_curated_sources(category, location)
    if dedicated:
        return [_normalize_competition_item(item, category, location) for item in dedicated]

    base = [
        ("江苏句容市人民政府", "https://www.jurong.gov.cn/", "江苏句容本地政务公告、人才政策、创业大赛和产业动态入口。"),
        ("江苏句容政府部门入口", "https://www.jurong.gov.cn/jurong/zqdh/zqdh.shtml", "用于核验人社、农业农村、园区和镇街部门公开信息。"),
        ("江苏省农业农村厅", "https://nynct.jiangsu.gov.cn/index.html", "江苏省农业产业、乡村振兴、农业科技和新农人政策入口。"),
        ("镇江市人民政府", "https://www.zhenjiang.gov.cn/", "镇江市产业政策、人才项目和区域发展动态入口。"),
        ("江苏政务服务", "https://www.jszwfw.gov.cn/", "创业、补贴、项目申报和政策服务入口。"),
        ("江苏省人力资源和社会保障厅", "https://jshrss.jiangsu.gov.cn/", "青年人才、创业就业、创业担保贷款和人社服务公开入口。"),
        ("江苏省科学技术厅", "https://std.jiangsu.gov.cn/", "科技项目、成果转化、创新平台和科技人才政策入口。"),
        ("江苏省商务厅", "https://swt.jiangsu.gov.cn/", "电商、商贸流通、招商合作和农产品上行相关政策入口。"),
        ("国家人力资源和社会保障部", "https://www.mohrss.gov.cn/", "国家创业就业、人才服务和职业能力建设政策入口。"),
        ("中国政府网政策库", "https://www.gov.cn/zhengce/", "国家政策原文和跨部门政策核验入口。"),
        ("农业农村部", "https://www.moa.gov.cn/", "农业产业、乡村振兴、科技推广和市场信息官方入口。"),
        ("全国农产品批发市场价格信息系统", "http://pfsc.agri.cn/", "农业项目商业测算、农产品行情和销售判断参考入口。"),
    ]
    items = []
    for title, url, snippet in base:
        items.append(
            {
                "title": f"{category['label']}线索：{title}",
                "url": url,
                "snippet": f"{location}{category['focus']}相关信息可从该公开入口核验。{snippet}",
                "source": "官方公开入口",
                "source_type": "curated_public_source",
            }
        )
    return [_normalize_competition_item(item, category, location) for item in items]


def _category_curated_sources(category: dict, location: str) -> list[dict]:
    category_id = str(category.get("id") or "")
    label = str(category.get("label") or "专题")
    focus = str(category.get("focus") or "")
    by_category = {
        "agri_startup": [
            ("新农人项目申报入口", "https://www.jurong.gov.cn/", "看江苏句容本地创业大赛、乡村产业、家庭农场和合作社项目公告，先核验报名窗口与主管部门。", "农业创业"),
            ("家庭农场与合作社政策", "https://nynct.jiangsu.gov.cn/index.html", "核对省级家庭农场、农民合作社、乡村产业和农业经营主体培育政策，判断能不能申报。", "农业创业"),
            ("创业服务与补贴办理", "https://www.jszwfw.gov.cn/", "查创业补贴、项目申报、证照办理和政务服务材料清单，适合做申报前准备。", "申报窗口"),
            ("农产品行情测算", "http://pfsc.agri.cn/", "用批发市场价格做商业测算，判断草莓、蔬菜、茶叶等产品走批发还是订单渠道。", "市场测算"),
            ("镇江产业政策动态", "https://www.zhenjiang.gov.cn/", "核验镇江市产业政策、青年创业服务和区域农业产业动态，辅助做项目落地判断。", "产业政策"),
        ],
        "agri_tech": [
            ("设施农业与数智农业政策", "https://nynct.jiangsu.gov.cn/index.html", "查设施农业、智慧农业、农业物联网、农机装备和绿色高效生产相关政策。", "科技农业"),
            ("科技项目与成果转化", "https://std.jiangsu.gov.cn/", "核验科技项目、成果转化、创新平台、科技人才和农业科技企业申报入口。", "科技项目"),
            ("农业农村部科技推广", "https://www.moa.gov.cn/", "查看农业科技推广、农机装备、农技服务和乡村产业发展国家层面政策。", "科技推广"),
            ("江苏句容本地产业入口", "https://www.jurong.gov.cn/jurong/zqdh/zqdh.shtml", "从部门入口进入农业农村、科技、人社和园区栏目，核验本地数智农业落地对接部门。", "江苏句容官方"),
            ("电商与供应链数字化", "https://swt.jiangsu.gov.cn/", "查看电商、商贸流通、农产品上行和供应链数字化相关支持方向。", "新媒体助农"),
        ],
        "youth_talent": [
            ("福地青年英才与人才政策", "https://www.jurong.gov.cn/", "聚焦江苏句容青年英才、大学生创业、人才政策和创业大赛公告，先看时间、对象和材料。", "青年人才"),
            ("江苏人社创业就业服务", "https://jshrss.jiangsu.gov.cn/", "核验青年人才、创业就业、创业担保贷款、培训补贴和就业创业服务政策。", "青年人才"),
            ("国家人社人才服务入口", "https://www.mohrss.gov.cn/", "查创业就业、技能培训、人才服务和职业能力建设政策，辅助判断团队资质。", "人才服务"),
            ("江苏政务服务创业事项", "https://www.jszwfw.gov.cn/", "办理创业、补贴、项目申报、证照和公共服务事项，适合作为申报操作入口。", "申报窗口"),
            ("镇江青年创业与产业动态", "https://www.zhenjiang.gov.cn/", "查看镇江市青年创业、人才项目和区域产业信息，判断项目能否对接上级资源。", "镇江官方"),
        ],
        "investment": [
            ("江苏句容招商与园区信息", "https://www.jurong.gov.cn/", "核验园区载体、产业链招商、项目落地和农业科技招商线索。", "招商孵化"),
            ("镇江产业链与平台招商", "https://www.zhenjiang.gov.cn/", "查看镇江产业政策、平台招商和区域协同机会，评估项目落地空间。", "招商孵化"),
            ("江苏商务流通与招商", "https://swt.jiangsu.gov.cn/", "查商贸流通、电商供应链、招商合作和农产品上行相关政策。", "招商渠道"),
            ("江苏政务项目申报", "https://www.jszwfw.gov.cn/", "梳理项目申报、企业服务和政务办理事项。", "申报窗口"),
        ],
        "new_media": [
            ("农产品上行与电商政策", "https://swt.jiangsu.gov.cn/", "查看直播电商、商贸流通、品牌传播和农产品上行政策。", "新媒体助农"),
            ("江苏句容品牌与节庆活动", "https://www.jurong.gov.cn/", "关注本地节庆、农产品品牌、助农活动和创业大赛传播窗口。", "江苏句容官方"),
            ("农业农村部市场信息", "https://www.moa.gov.cn/", "核验农产品市场、品牌农业和乡村产业政策方向。", "农业品牌"),
            ("全国批发市场行情", "http://pfsc.agri.cn/", "用价格数据辅助直播、电商和批发渠道定价。", "行情支撑"),
        ],
        "policy_funding": [
            ("江苏政务服务申报窗口", "https://www.jszwfw.gov.cn/", "查补贴、创业扶持、贷款、项目申报和公共服务事项。", "申报窗口"),
            ("江苏农业农村政策", "https://nynct.jiangsu.gov.cn/index.html", "核验农业产业、乡村振兴、经营主体和农业项目扶持政策。", "政策资金"),
            ("江苏人社创业担保贷款", "https://jshrss.jiangsu.gov.cn/", "核对青年创业、就业创业补贴、创业担保贷款和培训政策。", "创业资金"),
            ("中国政府网政策库", "https://www.gov.cn/zhengce/", "复核国家政策原文和跨部门政策依据。", "政策原文"),
        ],
    }
    rows = by_category.get(category_id, [])
    return [
        {
            "title": f"{label}线索：{title}",
            "url": url,
            "snippet": f"{location}{focus}相关信息可从该入口核验。{snippet}",
            "source": reason,
            "source_type": "curated_public_source",
        }
        for title, url, snippet, reason in rows
    ]


def _dedupe_items(items: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for item in items:
        key = (str(item.get("url") or "").lower().rstrip("/"), str(item.get("title") or "").strip())
        if not key[0] and not key[1]:
            continue
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _count_hits(text: str, words: list[str]) -> int:
    value = text or ""
    hits = 0
    for word in words:
        word = _clean(word)
        if word and word in value:
            hits += 1
    return hits


def _source_label(url: str, fallback: Any = "") -> str:
    try:
        host = re.sub(r"^www\.", "", urlparse(url).netloc)
    except Exception:
        host = ""
    if "jurong.gov.cn" in host:
        return "江苏句容官方"
    if "zhenjiang.gov.cn" in host:
        return "镇江官方"
    if "jiangsu.gov.cn" in host or "jszwfw.gov.cn" in host:
        return "江苏官方"
    if host:
        return host
    return _clean(fallback) or "公开来源"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()
