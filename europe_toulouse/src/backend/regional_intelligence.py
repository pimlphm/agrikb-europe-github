from __future__ import annotations

import json
import ipaddress
import math
import re
import threading
import time
from html import unescape
from pathlib import Path
from urllib.parse import quote_plus

import requests

from src.backend.headline_recommender import build_headline_items_from_regional_payload
from src.backend.web_search import search_web


ROOT = Path(__file__).resolve().parents[2]
LOGISTICS_CACHE_PATH = ROOT / "runtime" / "logistics_supplier_cache.json"
LOGISTICS_CACHE_TTL_SECONDS = 6 * 60 * 60
LOGISTICS_CACHE_VERSION = "20260524-kimi-logistics-v6"
LOGISTICS_KIMI_JOBS: set[str] = set()
LOGISTICS_KIMI_LOCK = threading.Lock()


JURONG = {
    "name": "江苏镇江 / 江苏句容",
    "short_name": "江苏句容",
    "latitude": 31.94869,
    "longitude": 119.1655,
    "timezone": "Asia/Shanghai",
    "source": "preset",
}

MARKET_DEFAULT = {
    "name": "镇江农产品批发市场",
    "short_name": "镇江农产品批发市场",
    "latitude": 32.21086,
    "longitude": 119.45508,
    "timezone": "Asia/Shanghai",
    "source": "preset",
}

LOCATION_PRESETS = {
    "江苏句容": JURONG,
    "句容": JURONG,
    "镇江": MARKET_DEFAULT,
    "镇江农产品批发市场": MARKET_DEFAULT,
    "镇江农副产品批发市场": MARKET_DEFAULT,
    "常州凌家塘农副产品批发市场": {
        "name": "江苏常州 / 凌家塘农副产品批发市场",
        "short_name": "常州凌家塘",
        "latitude": 31.7833,
        "longitude": 119.9167,
        "timezone": "Asia/Shanghai",
        "source": "preset",
    },
    "苏州南环桥市场": {
        "name": "江苏苏州 / 南环桥农副产品市场",
        "short_name": "苏州南环桥",
        "latitude": 31.268,
        "longitude": 120.635,
        "timezone": "Asia/Shanghai",
        "source": "preset",
    },
    "上海西郊国际农产品交易中心": {
        "name": "上海 / 西郊国际农产品交易中心",
        "short_name": "上海西郊国际",
        "latitude": 31.215,
        "longitude": 121.25,
        "timezone": "Asia/Shanghai",
        "source": "preset",
    },
    "杭州农副产品物流中心": {
        "name": "浙江杭州 / 农副产品物流中心",
        "short_name": "杭州农副产品物流中心",
        "latitude": 30.333,
        "longitude": 120.12,
        "timezone": "Asia/Shanghai",
        "source": "preset",
    },
}

GEOCODE_ALIASES = {
    "江苏句容": "Jurong",
    "句容": "Jurong",
    "镇江": "Zhenjiang",
    "常州": "Changzhou",
    "苏州": "Suzhou",
    "无锡": "Wuxi",
    "上海": "Shanghai",
    "杭州": "Hangzhou",
    "合肥": "Hefei",
}

CHANNEL_BASE = [
    {
        "title": "福地云选 / 江苏句容本地农产品电商",
        "url": "https://www.moa.gov.cn/xw/qg/202103/t20210310_6363371.htm",
        "snippet": "农业农村部信息显示，江苏句容以电商平台助农帮销，曾策划茅山长青节、华阳福桃文化节等活动，并计划与江苏句容市农业农村局合作打造本地特色蔬菜品牌。",
    },
    {
        "title": "供销 e 家江苏句容运营中心",
        "url": "https://www.chinacoop.gov.cn/HTML/2019/03/21/150803.html",
        "snippet": "江苏句容供销社搭建电商与物流配送体系，连接新型农业经营主体、批发市场、连锁超市，拓展农产品进城渠道。",
    },
    {
        "title": "江苏句容农产品产地冷藏保鲜整县推进试点",
        "url": "https://www.jsw.com.cn/2022/0710/1707858.shtml",
        "snippet": "江苏句容获批国家级农产品产地冷藏保鲜整县推进试点县，有利于产地仓储保鲜、物流体系和区域公共品牌建设。",
    },
    {
        "title": "镇江农村电商与苏货直播新农人培育",
        "url": "https://www.zhenjiang.gov.cn/",
        "snippet": "镇江及江苏县域持续推进农村电商、直播带货和供应链仓储，适合把本地农产品接入抖音、京东、社区团购等渠道。",
    },
]


def build_regional_intelligence(
    query: str,
    enabled: bool = True,
    production_location: str = "江苏句容",
    market_location: str = "镇江农产品批发市场",
    weather_location: str = "江苏句容",
    production_lat: float | None = None,
    production_lon: float | None = None,
    market_lat: float | None = None,
    market_lon: float | None = None,
    weather_lat: float | None = None,
    weather_lon: float | None = None,
    client_ip: str = "",
    llm_provider=None,
) -> dict:
    if not enabled:
        return {}
    payload = build_location_market_context(
        query=query,
        production_location=production_location,
        market_location=market_location,
        weather_location=weather_location,
        production_lat=production_lat,
        production_lon=production_lon,
        market_lat=market_lat,
        market_lon=market_lon,
        weather_lat=weather_lat,
        weather_lon=weather_lon,
        client_ip=client_ip,
        llm_provider=llm_provider,
        enabled=True,
    )
    payload["region"] = payload.get("production_location") or JURONG
    payload["weather"] = payload.get("weather") or payload.get("production_weather") or {}
    payload["ecommerce_channels"] = CHANNEL_BASE + (payload.get("ecommerce_results") or [])[:2]
    return payload


def build_location_market_context(
    query: str = "",
    production_location: str = "江苏句容",
    market_location: str = "镇江农产品批发市场",
    weather_location: str = "江苏句容",
    production_lat: float | None = None,
    production_lon: float | None = None,
    market_lat: float | None = None,
    market_lon: float | None = None,
    weather_lat: float | None = None,
    weather_lon: float | None = None,
    client_ip: str = "",
    llm_provider=None,
    enabled: bool = True,
) -> dict:
    if not enabled:
        return {}

    ip_location = get_ip_location(client_ip)
    production = resolve_location(
        production_location,
        ip_location=ip_location,
        fallback=JURONG,
        coordinates=(production_lat, production_lon),
    )
    market = resolve_location(
        market_location,
        fallback=MARKET_DEFAULT,
        coordinates=(market_lat, market_lon),
    )
    weather_target = resolve_location(
        weather_location or production_location,
        ip_location=ip_location,
        fallback=JURONG,
        coordinates=(weather_lat, weather_lon),
    )
    production_weather = get_weather_snapshot(production)
    weather_snapshot = get_weather_snapshot(weather_target)
    market_weather = get_weather_snapshot(market)
    route = build_route_summary(production, market)
    route["map_url"] = build_route_map_url(production, market)
    route["route_plan"] = build_route_plan(production, market, route, production_weather, market_weather)
    route["sales_advice"] = build_along_route_sales_advice(production, market, route, production_weather, market_weather)

    production_name = production.get("short_name") or production.get("name") or "本地产地"
    market_name = market.get("short_name") or market.get("name") or "目标市场"
    query_tail = str(query or "").strip()
    policy_results = _filter_public_results(search_web(f"{production_name} 农业农村局 产业扶持 新农人 政策 {query_tail}", 4))
    market_results = _filter_public_results(search_web(f"{market_name} 农产品 批发市场 收购 行情 电商 {query_tail}", 4))
    logistics_results = _filter_public_results(search_web(f"{production_name} 到 {market_name} 农产品 冷链物流 配送 货运 {query_tail}", 4))
    ecommerce_results = _filter_public_results(search_web(f"{production_name} 农产品 电商 助农 合作社 直播 {query_tail}", 3))
    logistics_suppliers = aggregate_logistics_suppliers(production_name, market_name, query_tail, llm_provider)
    if not policy_results:
        policy_results = [_search_item(f"{production_name}农业政策与产业扶持", f"{production_name} 农业农村局 产业扶持 新农人 政策")]
    if not market_results:
        market_results = [_search_item(f"{market_name}农产品收购与行情", f"{market_name} 农产品 批发 收购 行情")]
    if not logistics_results:
        logistics_results = []
    if not ecommerce_results:
        ecommerce_results = [_search_item(f"{production_name}电商助农渠道", f"{production_name} 农产品 电商 助农 合作社")]
    route["market_source_url"] = _first_public_url(market_results)
    route["logistics_source_url"] = _first_public_url(logistics_results)

    payload = {
        "ip_location": ip_location,
        "production_location": production,
        "market_location": market,
        "weather_location": weather_target,
        "weather": weather_snapshot,
        "production_weather": production_weather,
        "market_weather": market_weather,
        "route": route,
        "policy_results": policy_results,
        "market_results": market_results,
        "logistics_results": logistics_results,
        "logistics_suppliers": logistics_suppliers,
        "ecommerce_results": ecommerce_results,
        "market_recommendation": build_market_recommendation(production_weather, market_weather, route, market_name),
        "location_presets": list(LOCATION_PRESETS.keys()),
    }
    payload["recommended_headlines"] = build_headline_items_from_regional_payload(payload, query=query_tail)
    return payload


def regional_intelligence_as_chunks(payload: dict) -> list[dict]:
    if not payload:
        return []
    chunks: list[dict] = []
    production = payload.get("production_location") or payload.get("region") or JURONG
    market = payload.get("market_location") or MARKET_DEFAULT
    weather = payload.get("production_weather") or payload.get("weather") or {}
    market_weather = payload.get("market_weather") or {}
    route = payload.get("route") or {}
    if weather:
        horizon_summary = _summarize_weather_horizons(weather.get("weather_horizons") or [])
        chunks.append(
            _chunk(
                f"{production.get('short_name', '江苏句容')}实时气象环境",
                "regional_weather",
                (
                    f"产地: {production.get('name', '江苏句容')}\n"
                    f"当前温度: {_display_value(weather.get('temperature_2m'), '摄氏度')}；相对湿度: {_display_value(weather.get('relative_humidity_2m'), '%')}；"
                    f"降水: {_display_value(weather.get('precipitation'), 'mm')}；风速: {_display_value(weather.get('wind_speed_10m'), 'km/h')}。\n"
                    f"未来最高温: {_format_forecast_series(weather.get('daily_temperature_2m_max'), '摄氏度')}；最低温: {_format_forecast_series(weather.get('daily_temperature_2m_min'), '摄氏度')}；"
                    f"未来降水量: {_format_forecast_series(weather.get('daily_precipitation_sum'), 'mm')}。\n"
                    f"多时间尺度预报: {horizon_summary}\n"
                    "该气象信息来自 Open-Meteo 实时接口，用于生产、采收、物流和病虫害风险提醒。"
                ),
                "https://open-meteo.com/",
                [production.get("short_name", "江苏句容"), "气象", "环境", "气候", "Open-Meteo"],
            )
        )
    if market_weather or route:
        route_plan = route.get("route_plan") or {}
        sales_advice = route.get("sales_advice") or []
        chunks.append(
            _chunk(
                f"{production.get('short_name', '产地')}到{market.get('short_name', '目标市场')}运输与市场态势",
                "regional_route_market",
                (
                    f"产地: {production.get('name', '')}\n"
                    f"目标市场: {market.get('name', '')}\n"
                    f"市场天气: 温度 {_display_value(market_weather.get('temperature_2m'), '摄氏度')}；降水 {_display_value(market_weather.get('precipitation'), 'mm')}；"
                    f"风速 {_display_value(market_weather.get('wind_speed_10m'), 'km/h')}。\n"
                    f"预计运输距离: {_display_value(route.get('distance_km'), 'km')}；预计车程: {_display_value(route.get('duration_minutes'), '分钟')}；"
                    f"路线来源: {route.get('source', '')}。\n"
                    f"经营提示: {payload.get('market_recommendation', '')}\n"
                    f"路线策略: {route_plan.get('depart_window', '')}；{route_plan.get('packing', '')}；{route_plan.get('transport', '')}\n"
                    f"沿途散货建议: {_summarize_route_sales_advice(sales_advice)}"
                ),
                route.get("map_url", ""),
                [production.get("short_name", "产地"), market.get("short_name", "市场"), "物流", "收购", "路线"],
            )
        )
    if payload.get("logistics_suppliers"):
        chunks.append(
            _chunk(
                f"{production.get('short_name', '产地')}到{market.get('short_name', '目标市场')}冷链供应商筛选",
                "regional_logistics_supplier",
                _summarize_suppliers(payload.get("logistics_suppliers") or []),
                _first_public_url(payload.get("logistics_suppliers") or []),
                [production.get("short_name", "产地"), market.get("short_name", "市场"), "冷链", "供应商", "联系方式"],
            )
        )
    for group, chunk_type, label in [
        (payload.get("policy_results") or [], "regional_policy_news", f"{production.get('short_name', '本地')}政策与产业扶持"),
        (payload.get("market_results") or [], "regional_market_signal", f"{market.get('short_name', '目标市场')}市场收购信息"),
        (payload.get("logistics_results") or [], "regional_logistics_signal", "本地物流与冷链渠道"),
        (payload.get("ecommerce_channels") or [], "regional_ecommerce_channel", "本地助农与电商渠道"),
    ]:
        if not group:
            continue
        chunks.append(
            _chunk(
                label,
                chunk_type,
                _summarize_items(group[:5], label),
                group[0].get("url", ""),
                [production.get("short_name", "产地"), market.get("short_name", "市场"), "农业局", "助农", "电商", "政策", "收购"],
            )
        )
    return chunks


def _summarize_route_sales_advice(items: list[dict]) -> str:
    if not items:
        return "暂无沿途散货建议。"
    lines = []
    for item in items[:3]:
        lines.append(f"{item.get('title', '')}: {item.get('where', '')}，{item.get('how', '')}")
    return "；".join(line for line in lines if line.strip(": ，"))


def get_ip_location(client_ip: str = "") -> dict:
    ip = str(client_ip or "").strip()
    if _is_private_or_local_ip(ip):
        ip = ""
    url = f"http://ip-api.com/json/{ip}" if ip else "http://ip-api.com/json/"
    params = {
        "fields": "status,country,regionName,city,lat,lon,query,isp",
        "lang": "zh-CN",
    }
    try:
        data = requests.get(url, params=params, timeout=8, headers={"User-Agent": "AgriKB/1.0"}).json()
    except Exception:
        return {}
    if data.get("status") != "success":
        return {}
    city = data.get("city") or ""
    region = data.get("regionName") or ""
    country = data.get("country") or ""
    name = " / ".join([part for part in [country, region, city] if part])
    return {
        "name": name or "IP定位位置",
        "short_name": city or region or country or "IP定位位置",
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "ip": data.get("query"),
        "isp": data.get("isp"),
        "source": "ip",
    }


def resolve_location(
    value: str,
    ip_location: dict | None = None,
    fallback: dict | None = None,
    coordinates: tuple[float | None, float | None] | None = None,
) -> dict:
    fallback = fallback or JURONG
    raw = str(value or "").strip()
    coordinate_location = _location_from_coordinates(raw, coordinates, fallback)
    if coordinate_location:
        return coordinate_location
    parsed_location = _location_from_text_coordinates(raw, fallback)
    if parsed_location:
        return parsed_location
    if raw.lower() in {"auto", "ip", "current", "当前位置", "当前ip"} and ip_location:
        return _normalize_location(ip_location, fallback=fallback)
    if not raw:
        return _normalize_location(fallback, fallback=fallback)
    if raw in LOCATION_PRESETS:
        return _normalize_location(LOCATION_PRESETS[raw], fallback=fallback)

    geocode_query = raw
    for key, alias in GEOCODE_ALIASES.items():
        if key in raw:
            geocode_query = alias
            break
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": geocode_query, "count": 5, "language": "zh", "format": "json"},
            timeout=10,
            headers={"User-Agent": "AgriKB/1.0"},
        )
        results = response.json().get("results") or []
    except Exception:
        results = []
    if results:
        result = _pick_china_result(results) or results[0]
        country = result.get("country") or ""
        admin1 = result.get("admin1") or ""
        admin2 = result.get("admin2") or ""
        name = result.get("name") or raw
        full_name = " / ".join([part for part in [country, admin1, admin2, name] if part])
        return {
            "name": full_name or raw,
            "short_name": raw,
            "latitude": result.get("latitude"),
            "longitude": result.get("longitude"),
            "timezone": result.get("timezone") or "Asia/Shanghai",
            "source": "geocoding",
        }
    loc = dict(fallback)
    loc["short_name"] = raw
    loc["name"] = f"{raw}（坐标暂用{fallback.get('short_name', '默认地区')}）"
    loc["source"] = "fallback"
    return loc


def _location_from_coordinates(
    label: str,
    coordinates: tuple[float | None, float | None] | None,
    fallback: dict,
) -> dict | None:
    if not coordinates:
        return None
    try:
        lat = float(coordinates[0]) if coordinates[0] is not None else None
        lon = float(coordinates[1]) if coordinates[1] is not None else None
    except (TypeError, ValueError):
        return None
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    short_name = _clean_map_location_label(label) or "地图选点"
    name = f"{short_name}（地图选点 {lat:.5f}, {lon:.5f}）"
    return {
        "name": name,
        "short_name": short_name,
        "latitude": lat,
        "longitude": lon,
        "timezone": fallback.get("timezone") or "Asia/Shanghai",
        "source": "map",
    }


def _location_from_text_coordinates(raw: str, fallback: dict) -> dict | None:
    match = re.search(r"(-?\d{1,2}(?:\.\d+)?)\s*[,，]\s*(-?\d{1,3}(?:\.\d+)?)", raw or "")
    if not match:
        return None
    label = re.sub(r"[\s（(]*-?\d{1,2}(?:\.\d+)?\s*[,，]\s*-?\d{1,3}(?:\.\d+)?[\s）)]*", "", raw).strip()
    return _location_from_coordinates(label or "地图选点", (match.group(1), match.group(2)), fallback)


def _clean_map_location_label(label: str) -> str:
    value = _clean_text(label)
    value = re.sub(r"地图选点[:：]?", "", value).strip()
    value = re.sub(r"[\s（(]*-?\d{1,2}(?:\.\d+)?\s*[,，]\s*-?\d{1,3}(?:\.\d+)?[\s）)]*", "", value).strip()
    if value.lower() in {"auto", "ip", "current"}:
        return ""
    return value[:32]


def get_weather_snapshot(location: dict | None = None) -> dict:
    location = location or JURONG
    lat = location.get("latitude")
    lon = location.get("longitude")
    if lat is None or lon is None:
        return {}
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,precipitation_probability_max,weather_code",
        "timezone": location.get("timezone") or "Asia/Shanghai",
        "forecast_days": 16,
    }
    try:
        data = requests.get(url, params=params, timeout=18, headers={"User-Agent": "AgriKB/1.0"}).json()
    except Exception:
        return {}
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    daily_time = (daily.get("time") or [])[:16]
    daily_max = (daily.get("temperature_2m_max") or [])[:16]
    daily_min = (daily.get("temperature_2m_min") or [])[:16]
    daily_rain = (daily.get("precipitation_sum") or [])[:16]
    daily_wind = (daily.get("wind_speed_10m_max") or [])[:16]
    daily_rain_probability = (daily.get("precipitation_probability_max") or [])[:16]
    daily_weather_code = (daily.get("weather_code") or [])[:16]
    return {
        "temperature_2m": current.get("temperature_2m"),
        "relative_humidity_2m": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "wind_speed_10m": current.get("wind_speed_10m"),
        "daily_time": daily_time,
        "daily_temperature_2m_max": daily_max,
        "daily_temperature_2m_min": daily_min,
        "daily_precipitation_sum": daily_rain,
        "daily_wind_speed_10m_max": daily_wind,
        "daily_precipitation_probability_max": daily_rain_probability,
        "daily_weather_code": daily_weather_code,
        "forecast_days": len(daily_time),
        "forecast_source": "Open-Meteo",
        "forecast_timezone": data.get("timezone") or location.get("timezone") or "Asia/Shanghai",
        "weather_horizons": _build_weather_horizons(
            daily_time,
            daily_max,
            daily_min,
            daily_rain,
            daily_wind,
            daily_rain_probability,
            daily_weather_code,
        ),
    }


def _build_weather_horizons(
    dates: list,
    max_temps: list,
    min_temps: list,
    rains: list,
    winds: list,
    rain_probs: list,
    weather_codes: list,
) -> list[dict]:
    bands = [
        ("today", "今天", 0, 1, "当天预报"),
        ("tomorrow", "明天", 1, 2, "次日预报"),
        ("next3", "未来3天", 0, 3, "短期预报"),
        ("day5_10", "5-10天", 4, 10, "中期预报"),
        ("day15", "15天", 0, 15, "延伸预报"),
        ("week3", "3周趋势", 10, 16, "趋势参考"),
    ]
    horizons: list[dict] = []
    for horizon_id, label, start, end, confidence in bands:
        horizon = _build_weather_horizon(
            horizon_id,
            label,
            start,
            end,
            confidence,
            dates,
            max_temps,
            min_temps,
            rains,
            winds,
            rain_probs,
            weather_codes,
        )
        if horizon:
            horizons.append(horizon)
    return horizons


def _build_weather_horizon(
    horizon_id: str,
    label: str,
    start: int,
    end: int,
    confidence: str,
    dates: list,
    max_temps: list,
    min_temps: list,
    rains: list,
    winds: list,
    rain_probs: list,
    weather_codes: list,
) -> dict | None:
    date_window = [str(item) for item in dates[start:end] if item]
    if not date_window:
        return None
    temp_max_values = _numeric_window(max_temps, start, end)
    temp_min_values = _numeric_window(min_temps, start, end)
    rain_values = _numeric_window(rains, start, end)
    wind_values = _numeric_window(winds, start, end)
    rain_prob_values = _numeric_window(rain_probs, start, end)
    code_values = _numeric_window(weather_codes, start, end)
    temp_max = max(temp_max_values) if temp_max_values else None
    temp_min = min(temp_min_values) if temp_min_values else None
    rain_sum = round(sum(rain_values), 1) if rain_values else 0
    rain_max = max(rain_values) if rain_values else 0
    wind_max = max(wind_values) if wind_values else 0
    rain_prob_max = max(rain_prob_values) if rain_prob_values else None
    risk_level, risk, action = _weather_horizon_decision(
        label=label,
        rain_sum=rain_sum,
        rain_max=rain_max,
        temp_min=temp_min,
        temp_max=temp_max,
        wind_max=wind_max,
        rain_probability=rain_prob_max,
    )
    if horizon_id == "week3":
        action = f"{action}；第三周按趋势参考处理，每天刷新一次。"
    return {
        "id": horizon_id,
        "label": label,
        "date_range": _date_range_label(date_window),
        "days": len(date_window),
        "temperature_max": _round_or_none(temp_max),
        "temperature_min": _round_or_none(temp_min),
        "rain_sum": _round_or_none(rain_sum) or 0,
        "rain_max": _round_or_none(rain_max) or 0,
        "wind_max": _round_or_none(wind_max) or 0,
        "rain_probability_max": _round_or_none(rain_prob_max),
        "weather_code_main": int(code_values[0]) if code_values else None,
        "risk_level": risk_level,
        "risk": risk,
        "action": action,
        "confidence": confidence,
    }


def _weather_horizon_decision(
    label: str,
    rain_sum: float,
    rain_max: float,
    temp_min: float | None,
    temp_max: float | None,
    wind_max: float,
    rain_probability: float | None,
) -> tuple[str, str, str]:
    if rain_max >= 25 or rain_sum >= 50:
        return (
            "high",
            f"{label}有强降雨风险，田间积水和运输延误概率高。",
            "成熟果菜提前采收，沟渠先排水，发货包装做好防潮。",
        )
    if rain_max >= 10 or rain_sum >= 20 or (rain_probability is not None and rain_probability >= 75):
        return (
            "medium",
            f"{label}降雨偏多，露天采收和施药要避开雨段。",
            "先排采收顺序，易损品优先，农资和成品垫高存放。",
        )
    if temp_max is not None and temp_max >= 35:
        return (
            "high",
            f"{label}高温明显，中午作业、采后保鲜和运输损耗风险高。",
            "采收放在清晨或傍晚，及时预冷补水，运输避开午后高温。",
        )
    if temp_max is not None and temp_max >= 32:
        return (
            "medium",
            f"{label}气温偏高，采收和装车要注意保鲜。",
            "避开中午采收，分级后尽快入库或对接冷链。",
        )
    if temp_min is not None and temp_min <= 3:
        return (
            "medium",
            f"{label}夜间低温，幼苗、花果期和棚室要关注冷害。",
            "夜间覆盖保温，棚室提前检查通风和保温设备。",
        )
    if wind_max >= 30:
        return (
            "medium",
            f"{label}风力偏大，棚膜、支架和运输装载需检查。",
            "加固棚室和覆盖物，延后喷药和高空作业。",
        )
    return (
        "low",
        f"{label}天气整体平稳，适合按订单组织采收和发货。",
        "保持巡田，按市场订单分批采收，继续关注每日更新。",
    )


def _numeric_window(values: list, start: int, end: int) -> list[float]:
    window: list[float] = []
    for item in values[start:end]:
        number = _to_float(item)
        if number is not None:
            window.append(number)
    return window


def _to_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _round_or_none(value, digits: int = 1):
    number = _to_float(value)
    if number is None:
        return None
    return round(number, digits)


def _date_range_label(dates: list[str]) -> str:
    if not dates:
        return ""
    if len(dates) == 1:
        return dates[0]
    return f"{dates[0]} 至 {dates[-1]}"


def _display_value(value, unit: str = "") -> str:
    number = _to_float(value)
    if number is None:
        return "暂无数据"
    if float(number).is_integer():
        text = str(int(number))
    else:
        text = str(round(number, 1))
    return f"{text}{unit}"


def _format_forecast_series(values, unit: str = "", limit: int = 6) -> str:
    if not isinstance(values, list):
        return "暂无数据"
    cleaned = [_display_value(value, unit) for value in values if _to_float(value) is not None]
    if not cleaned:
        return "暂无数据"
    shown = "、".join(cleaned[:limit])
    if len(cleaned) > limit:
        shown += "等"
    return shown


def _summarize_weather_horizons(horizons: list[dict]) -> str:
    if not horizons:
        return "多日预报暂未返回，请稍后刷新。"
    summary_parts = []
    for horizon in horizons:
        label = horizon.get("label") or "预报"
        date_range = horizon.get("date_range") or ""
        risk = horizon.get("risk") or ""
        action = horizon.get("action") or ""
        summary_parts.append(f"{label}（{date_range}）：{risk}{action}")
    return "；".join(summary_parts)


def build_route_summary(origin: dict, destination: dict) -> dict:
    origin_lon = origin.get("longitude")
    origin_lat = origin.get("latitude")
    dest_lon = destination.get("longitude")
    dest_lat = destination.get("latitude")
    try:
        origin_lat = float(origin_lat)
        origin_lon = float(origin_lon)
        dest_lat = float(dest_lat)
        dest_lon = float(dest_lon)
    except (TypeError, ValueError):
        return {
            "distance_km": None,
            "duration_minutes": None,
            "source": "坐标不足",
            "route_grade": "需补坐标",
            "confidence": "缺少有效经纬度，先补全地图点位。",
            "corridor": f"{origin.get('short_name', '产地')} → {destination.get('short_name', '目标市场')}",
            "waypoints": [],
        }
    url = f"https://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    try:
        data = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            timeout=10,
            headers={"User-Agent": "AgriKB/1.0"},
        ).json()
        route = (data.get("routes") or [])[0]
        distance_km = round(float(route.get("distance", 0)) / 1000, 1)
        duration_minutes = int(round(float(route.get("duration", 0)) / 60))
        if distance_km > 0:
            geometry = ((route.get("geometry") or {}).get("coordinates") or [])[:80]
            waypoints = _route_waypoints_from_geometry(geometry, origin, destination)
            return {
                "distance_km": distance_km,
                "duration_minutes": duration_minutes,
                "source": "OSRM实时路线估算",
                "route_grade": _route_grade(distance_km, duration_minutes),
                "confidence": "已读取公开路径服务；实际通行以当天道路、限行和装车条件为准。",
                "corridor": _route_corridor_label(origin, destination, waypoints),
                "waypoints": waypoints,
            }
    except Exception:
        pass
    straight_km = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    factor = _road_factor(straight_km)
    distance_km = round(max(0.1, straight_km * factor), 1)
    speed = _planning_speed_kmh(distance_km)
    duration_minutes = max(1, int(round(distance_km / speed * 60)))
    waypoints = _fallback_route_waypoints(origin, destination, distance_km)
    return {
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "source": "本地路线规划估算",
        "route_grade": _route_grade(distance_km, duration_minutes),
        "confidence": "外部路径服务暂不可用时，按两点坐标、道路绕行系数和农产品运输速度本地估算。",
        "corridor": _route_corridor_label(origin, destination, waypoints),
        "waypoints": waypoints,
    }


def _road_factor(distance_km: float) -> float:
    if distance_km < 8:
        return 1.55
    if distance_km < 35:
        return 1.38
    if distance_km < 120:
        return 1.25
    return 1.18


def _planning_speed_kmh(distance_km: float) -> float:
    if distance_km < 8:
        return 28
    if distance_km < 35:
        return 42
    if distance_km < 120:
        return 58
    return 68


def _route_grade(distance_km: float | None, duration_minutes: int | None) -> str:
    if not distance_km or not duration_minutes:
        return "待补全"
    if distance_km <= 15 and duration_minutes <= 35:
        return "短途快销"
    if distance_km <= 80 and duration_minutes <= 120:
        return "半日达"
    if distance_km <= 180:
        return "当日达"
    return "长途冷链"


def _route_waypoints_from_geometry(geometry: list, origin: dict, destination: dict) -> list[dict]:
    if not geometry:
        return _fallback_route_waypoints(origin, destination, None)
    picks = [0, len(geometry) // 2, len(geometry) - 1]
    labels = ["产地装车点", "中途补给/散货试销点", "目标市场交货点"]
    waypoints = []
    for index, pick in enumerate(picks):
        try:
            lon, lat = geometry[pick]
        except Exception:
            continue
        if index == 0:
            name = origin.get("short_name") or labels[index]
        elif index == 2:
            name = destination.get("short_name") or labels[index]
        else:
            name = labels[index]
        waypoints.append({"name": name, "lat": round(float(lat), 6), "lon": round(float(lon), 6), "role": labels[index]})
    return waypoints


def _fallback_route_waypoints(origin: dict, destination: dict, distance_km: float | None) -> list[dict]:
    try:
        origin_lat = float(origin.get("latitude"))
        origin_lon = float(origin.get("longitude"))
        dest_lat = float(destination.get("latitude"))
        dest_lon = float(destination.get("longitude"))
    except (TypeError, ValueError):
        return []
    mid_lat = (origin_lat + dest_lat) / 2
    mid_lon = (origin_lon + dest_lon) / 2
    return [
        {"name": origin.get("short_name") or "产地装车点", "lat": round(origin_lat, 6), "lon": round(origin_lon, 6), "role": "产地装车点"},
        {"name": _midpoint_sales_label(origin, destination, distance_km), "lat": round(mid_lat, 6), "lon": round(mid_lon, 6), "role": "中途补给/散货试销点"},
        {"name": destination.get("short_name") or "目标市场交货点", "lat": round(dest_lat, 6), "lon": round(dest_lon, 6), "role": "目标市场交货点"},
    ]


def _midpoint_sales_label(origin: dict, destination: dict, distance_km: float | None) -> str:
    origin_name = origin.get("short_name") or "产地"
    dest_name = destination.get("short_name") or "目标市场"
    if distance_km and distance_km < 25:
        return f"{origin_name}周边社区/团购试销点"
    if distance_km and distance_km < 120:
        return "沿途乡镇集配点"
    return f"{origin_name}到{dest_name}中途服务区/县城集配点"


def _route_corridor_label(origin: dict, destination: dict, waypoints: list[dict]) -> str:
    origin_name = origin.get("short_name") or "产地"
    dest_name = destination.get("short_name") or "目标市场"
    middle = ""
    if len(waypoints) >= 3:
        middle = waypoints[1].get("name") or ""
    return " → ".join([part for part in [origin_name, middle, dest_name] if part])


def build_route_plan(origin: dict, destination: dict, route: dict, production_weather: dict, market_weather: dict) -> dict:
    distance = route.get("distance_km")
    duration = route.get("duration_minutes")
    grade = route.get("route_grade") or _route_grade(distance, duration)
    rain_origin = _near_term_rain(production_weather)
    rain_market = _near_term_rain(market_weather)
    depart = "采后2小时内装车"
    packing = "按等级分箱，外箱贴批次和到货市场"
    transport = "普通厢货即可，但要遮阳防压"
    if rain_origin >= 8 or rain_market >= 8:
        depart = "雨前抢采，避开强降雨装车"
        packing = "加防潮内衬，箱底垫高，减少露水入箱"
        transport = "优先冷链或保温车，装车前拍照留证"
    elif distance and distance > 120:
        depart = "凌晨或傍晚发车，避开高温和拥堵"
        packing = "精品货走冷链箱，普通货分级防压"
        transport = "冷链整车或拼车，先锁定到货时段"
    elif distance and distance < 25:
        depart = "上午采上午卖，保留机动小批量"
        packing = "散货用周转筐，礼盒只装精品"
        transport = "短驳车或同城配送，先跑近场订单"
    return {
        "grade": grade,
        "depart_window": depart,
        "packing": packing,
        "transport": transport,
        "checkpoint": "出发前确认收购价、联系人、到货时段、退货规则和付款方式。",
        "quality_control": "装车前做分级、称重、拍照和批次记录；到货后保留签收或对账凭证。",
    }


def build_along_route_sales_advice(
    origin: dict,
    destination: dict,
    route: dict,
    production_weather: dict,
    market_weather: dict,
) -> list[dict]:
    distance = route.get("distance_km") or 0
    duration = route.get("duration_minutes") or 0
    rain_origin = _near_term_rain(production_weather)
    rain_market = _near_term_rain(market_weather)
    origin_name = origin.get("short_name") or "产地"
    market_name = destination.get("short_name") or "目标市场"
    base_ratio = "10%-15%"
    if distance < 25:
        base_ratio = "20%-30%"
    elif distance > 120:
        base_ratio = "5%-10%"
    weather_note = "雨天少摆摊，多走预售和固定收货点。" if rain_origin >= 8 or rain_market >= 8 else "天气可控，可做小批量试销。"
    return [
        {
            "title": "产地周边先试价",
            "where": f"{origin_name}周边社区、合作社门口、乡镇集市",
            "what": "成熟度高、耐压一般的散货先就近消化",
            "how": f"控制在总货量{base_ratio}，用低损耗周转筐，现场只卖散货不拆精品箱。",
            "risk": "不要影响已锁定的目标市场订单。",
        },
        {
            "title": "中途只做预约取货",
            "where": route.get("corridor") or "两地中途集配点",
            "what": "适合单位团购、小店补货、社区团长取货",
            "how": "出车前发图片、等级、箱规和价格，到点即取，停留不超过20分钟。",
            "risk": "中途临停过久会升温、压货和误点。",
        },
        {
            "title": "到市场前再分流",
            "where": f"{market_name}周边批发档口、社区团购仓、电商前置仓",
            "what": "精品走议价，普通货走快销，尾货走加工或团购",
            "how": f"车程约{duration}分钟，到货前30分钟二次确认档口价和卸货口。",
            "risk": weather_note,
        },
    ]


def build_route_map_url(origin: dict, destination: dict) -> str:
    origin_lat = origin.get("latitude")
    origin_lon = origin.get("longitude")
    dest_lat = destination.get("latitude")
    dest_lon = destination.get("longitude")
    if None in {origin_lat, origin_lon, dest_lat, dest_lon}:
        return build_search_url(f"{origin.get('short_name', '')} 到 {destination.get('short_name', '')} 农产品 物流 路线")
    return (
        "https://www.openstreetmap.org/directions"
        f"?engine=fossgis_osrm_car&route={origin_lat}%2C{origin_lon}%3B{dest_lat}%2C{dest_lon}"
    )


def build_search_url(query: str) -> str:
    return ""


def _search_item(title: str, query: str) -> dict:
    return {
        "title": title,
        "url": build_search_url(query),
        "snippet": "实时信息暂未返回公开来源，后台会在下一次刷新时继续聚合。",
        "source_type": "search_entry",
    }


def aggregate_logistics_suppliers(production_name: str, market_name: str, query_tail: str, llm_provider=None) -> list[dict]:
    cache_key = _cache_key(production_name, market_name, query_tail)
    cached = _read_logistics_cache().get(cache_key)
    if cached and time.time() - float(cached.get("saved_at", 0)) < LOGISTICS_CACHE_TTL_SECONDS:
        return cached.get("suppliers", [])[:6]
    queries = [
        f"{production_name} {market_name} 农产品 冷链物流 公司 联系电话",
        f"site:1688.com {production_name} 冷链物流 农产品 配送",
        f"site:alibaba.com Jiangsu cold chain logistics agricultural products",
    ]
    if query_tail:
        queries.append(f"{production_name} {market_name} {query_tail} 冷链物流 供应商")
    seen: set[str] = set()
    candidates: list[dict] = []
    for item in _curated_logistics_sources(production_name, market_name):
        url = str(item.get("url", "")).strip()
        if url and url not in seen:
            seen.add(url)
            candidates.append(_enrich_supplier_candidate(item, production_name, market_name))
    for query in queries:
        for item in _filter_public_results(search_web(query, 2)):
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            key = url or title
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(_enrich_supplier_candidate(item, production_name, market_name))
            if len(candidates) >= 10:
                break
        if len(candidates) >= 10:
            break
    if not candidates:
        return []
    selected = _fallback_select_logistics_suppliers(candidates)[:6]
    if llm_provider:
        _start_logistics_kimi_job(cache_key, candidates, production_name, market_name, llm_provider)
        for item in selected:
            item["selected_by"] = "kimi_pending"
            item["reliability"] = item.get("reliability") or "待核实"
            item["action"] = item.get("action") or "先打开来源页询价，新农人助手完成后会更新筛选结果"
    _write_logistics_cache(cache_key, selected, pending_kimi=bool(llm_provider))
    return selected


def _curated_logistics_sources(production_name: str, market_name: str) -> list[dict]:
    local_query = quote_plus(f"{production_name} {market_name} 农产品 冷链物流 配送")
    china_query = quote_plus("江苏 农产品 冷链物流 配送 冷藏车")
    alibaba_query = quote_plus("Jiangsu agricultural products cold chain logistics")
    return [
        {
            "title": "江苏苏豪冷链物流有限公司",
            "url": "http://www.hhcold.com/",
            "snippet": "镇江本地冷链企业公开网站，适合核实低温仓储、保鲜仓储、农产品冷链和长三角配送能力；联系方式以来源页公开信息为准。",
            "source_type": "curated_public_source",
        },
        {
            "title": "苏豪冷链：链接全球锁定鲜市场",
            "url": "https://www.jsw.com.cn/2026/0403/1954742.shtml",
            "snippet": "金山网公开报道，介绍江苏苏豪冷链物流有限公司位于镇江综合保税区的冷库与冷链通道能力，适合作为本地冷链能力核验来源。",
            "source_type": "curated_public_source",
        },
        {
            "title": "冷运侠冷链物流平台",
            "url": "https://www.lengyunxia.com/",
            "snippet": "公开网站显示提供农产品运输、恒温保鲜、冷藏鲜运输和普通物流货运服务，可用于农产品冷链询价和线路核实。",
            "source_type": "curated_public_source",
        },
        {
            "title": "鲜生活冷链物流有限公司",
            "url": "https://www.fresh-scm.cn/",
            "snippet": "全国冷链履约网络公开网站，覆盖生鲜、农牧、食材和园区运营等场景，可作为跨区域备选冷链服务商来源。",
            "source_type": "curated_public_source",
        },
        {
            "title": "宏鸿农产品集团冷链物流",
            "url": "https://www.szhonghong.com/Product/chain.html",
            "snippet": "农产品集团公开冷链板块，强调生鲜冷链、仓配一体和全程可视，可作为规模化农产品冷链服务参考。",
            "source_type": "curated_public_source",
        },
        {
            "title": "1688冷链物流服务商公开检索",
            "url": f"https://s.1688.com/selloffer/offer_search.htm?keywords={local_query}",
            "snippet": "阿里巴巴1688站内检索入口，可按本地路线筛选冷链物流、冷藏车、保温箱、农产品配送服务商，并通过平台在线联系或询价。",
            "source_type": "curated_platform_entry",
        },
        {
            "title": "1688江苏农产品冷链服务商检索",
            "url": f"https://s.1688.com/selloffer/offer_search.htm?keywords={china_query}",
            "snippet": "阿里巴巴1688公开检索入口，适合比价江苏冷链物流、农产品配送、冷藏车与包装保温服务；联系方式以平台店铺公开信息为准。",
            "source_type": "curated_platform_entry",
        },
        {
            "title": "Alibaba国际站冷链物流服务商检索",
            "url": f"https://www.alibaba.com/trade/search?SearchText={alibaba_query}",
            "snippet": "阿里巴巴国际站公开检索入口，可筛选cold chain logistics、refrigerated transport等服务商并在线询价，适合作为外贸或跨区域备选。",
            "source_type": "curated_platform_entry",
        },
    ]


def _enrich_supplier_candidate(item: dict, production_name: str, market_name: str) -> dict:
    title = _clean_text(item.get("title", "冷链物流供应商"))
    url = str(item.get("url", "")).strip()
    snippet = _clean_text(item.get("snippet", ""))
    platform = _platform_label(url, title)
    source_type = str(item.get("source_type", "web_search"))
    page_text = _fetch_public_page_text(url) if _should_fetch_supplier_page(url, source_type) else ""
    contact = _extract_public_contact(" ".join([snippet, page_text]))
    contact_method = contact or ("平台在线联系/询价" if platform in {"1688", "阿里巴巴国际站"} else "公开联系方式待核实")
    service_tags = _service_tags(" ".join([title, snippet, page_text]))
    return {
        "name": title[:80] or "冷链物流供应商",
        "platform": platform,
        "url": url,
        "snippet": snippet[:220],
        "contact": contact,
        "contact_method": contact_method,
        "service_scope": _guess_service_scope(title, snippet, production_name, market_name, service_tags),
        "service_tags": service_tags,
        "source_type": source_type,
    }


def _start_logistics_kimi_job(cache_key: str, candidates: list[dict], production_name: str, market_name: str, llm_provider) -> None:
    with LOGISTICS_KIMI_LOCK:
        if cache_key in LOGISTICS_KIMI_JOBS:
            return
        LOGISTICS_KIMI_JOBS.add(cache_key)
    worker = threading.Thread(
        target=_run_logistics_kimi_job,
        args=(cache_key, candidates[:10], production_name, market_name, llm_provider),
        daemon=True,
        name="agrikb-logistics-kimi",
    )
    worker.start()


def _run_logistics_kimi_job(cache_key: str, candidates: list[dict], production_name: str, market_name: str, llm_provider) -> None:
    try:
        selected = _kimi_select_logistics_suppliers(
            candidates,
            production_name,
            market_name,
            llm_provider,
            timeout_cap=90,
        )
        if selected:
            _write_logistics_cache(cache_key, selected[:6], pending_kimi=False)
    finally:
        with LOGISTICS_KIMI_LOCK:
            LOGISTICS_KIMI_JOBS.discard(cache_key)


def _kimi_select_logistics_suppliers(
    candidates: list[dict],
    production_name: str,
    market_name: str,
    llm_provider=None,
    timeout_cap: int = 25,
) -> list[dict]:
    if not llm_provider or not hasattr(llm_provider, "structured_output"):
        return []
    compact = [
        {
            "name": item.get("name", ""),
            "platform": item.get("platform", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
            "contact": item.get("contact", ""),
            "contact_method": item.get("contact_method", ""),
            "service_scope": item.get("service_scope", ""),
            "service_tags": item.get("service_tags", []),
        }
        for item in candidates[:10]
    ]
    schema = {
        "suppliers": [
            {
                "name": "供应商或平台名称，只能来自候选项",
                "platform": "平台或来源",
                "url": "来源链接，只能来自候选项",
                "contact": "公开电话/邮箱/平台联系入口。没有公开电话就写平台在线联系/询价",
                "service_scope": "适合承接的路线或服务",
                "reliability": "高/中/待核实",
                "reason": "为什么适合农产品冷链，20字以内",
                "action": "下一步怎么联系或询价",
            }
        ],
        "summary": "总体建议，80字以内",
    }
    prompt = (
        f"你是AgriKB后台物流筛选助手。请从候选公开网页中筛选{production_name}到{market_name}农产品冷链/同城配送/干线货运供应商。\n"
        "要求：只使用候选项里的名称和URL；不要编造电话；没有公开电话时写“平台在线联系/询价”；优先1688/阿里巴巴等可在线询价平台、政府/供销/市场公开信息、明确有冷链或农产品配送能力的供应商；剔除明显无关广告。\n"
        f"候选项JSON：\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
    )
    try:
        old_timeout = getattr(llm_provider, "timeout", None)
        if isinstance(old_timeout, (int, float)) and old_timeout > timeout_cap:
            llm_provider.timeout = timeout_cap
        payload = llm_provider.structured_output(
            prompt,
            schema=schema,
            system="只返回JSON，不要输出解释。所有供应商必须来自候选项，不得编造联系方式。",
        )
    except Exception:
        return []
    finally:
        if "old_timeout" in locals() and isinstance(old_timeout, (int, float)):
            try:
                llm_provider.timeout = old_timeout
            except Exception:
                pass
    candidate_by_url = {item.get("url", ""): item for item in candidates}
    selected: list[dict] = []
    for item in payload.get("suppliers", []) if isinstance(payload, dict) else []:
        url = str(item.get("url", "")).strip()
        if not url or url not in candidate_by_url:
            continue
        base = dict(candidate_by_url[url])
        base.update(
            {
                "name": _clean_text(item.get("name") or base.get("name", ""))[:80],
                "platform": _clean_text(item.get("platform") or base.get("platform", ""))[:30],
                "contact_method": _clean_text(item.get("contact") or base.get("contact_method", ""))[:80],
                "service_scope": _clean_text(item.get("service_scope") or base.get("service_scope", ""))[:100],
                "reliability": _clean_text(item.get("reliability") or "待核实")[:12],
                "reason": _clean_text(item.get("reason") or "")[:60],
                "action": _clean_text(item.get("action") or "打开来源页核实后询价")[:80],
                "selected_by": "kimi",
            }
        )
        selected.append(base)
    return selected


def _fallback_select_logistics_suppliers(candidates: list[dict]) -> list[dict]:
    scored = sorted(candidates, key=_supplier_score, reverse=True)
    selected = []
    for item in scored:
        item = dict(item)
        item.setdefault("reliability", "中" if _supplier_score(item) >= 4 else "待核实")
        item.setdefault("reason", "公开来源匹配冷链或配送关键词")
        item.setdefault("action", "打开来源页核实资质、线路、温控和报价")
        item["selected_by"] = "rule_fallback"
        selected.append(item)
    return selected


def _supplier_score(item: dict) -> int:
    text = " ".join([str(item.get("name", "")), str(item.get("snippet", "")), " ".join(item.get("service_tags", []))]).lower()
    url = str(item.get("url", "")).lower()
    score = 0
    if "1688" in url or "alibaba" in url:
        score += 4
    if "冷链" in text or "cold chain" in text:
        score += 4
    if "农产品" in text or "生鲜" in text or "冷藏" in text or "冷冻" in text:
        score += 3
    if item.get("contact"):
        score += 2
    if "物流" in text or "配送" in text:
        score += 2
    if str(item.get("source_type", "")).startswith("curated_"):
        score += 2
    return score


def _platform_label(url: str, title: str) -> str:
    value = f"{url} {title}".lower()
    if "1688.com" in value:
        return "1688"
    if "alibaba.com" in value:
        return "阿里巴巴国际站"
    if "chinacoop" in value or "供销" in title:
        return "供销公开信息"
    if ".gov.cn" in value or "政府" in title:
        return "政府公开信息"
    if any(host in value for host in ["hhcold.com", "lengyunxia.com", "fresh-scm.cn", "szhonghong.com"]):
        return "企业官网"
    return "公开网页"


def _should_fetch_supplier_page(url: str, source_type: str) -> bool:
    value = str(url or "").lower()
    if source_type == "curated_platform_entry":
        return False
    if any(host in value for host in ["1688.com", "alibaba.com", "tmall.com", "taobao.com"]):
        return False
    return source_type == "curated_public_source" or any(
        host in value for host in ["hhcold.com", "lengyunxia.com", "fresh-scm.cn", "szhonghong.com"]
    )


def _fetch_public_page_text(url: str) -> str:
    if not url.startswith("http"):
        return ""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgriKB/1.0"},
            timeout=3,
        )
        if not 200 <= response.status_code < 400:
            return ""
        text = response.text[:80000]
    except Exception:
        return ""
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return _clean_text(unescape(text))[:6000]


def _extract_public_contact(text: str) -> str:
    cleaned = _clean_text(text)
    phone_patterns = [
        r"(?<!\d)1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)",
        r"(?<!\d)400[\-\s]?\d{3}[\-\s]?\d{4}(?!\d)",
        r"(?<!\d)0(?:25|511|512|519|510|513|514|515|516|517|518|523|527|21|571|575)[\-\s]?\d{7,8}(?!\d)",
        r"(?<!\d)(?:025|0511|0512|0519|0510|0513|0514|0515|0516|0517|0518|0523|0527|021|0571|0575)[\-\s]\d{7,8}(?!\d)",
    ]
    contacts: list[str] = []
    for pattern in phone_patterns:
        for match in re.findall(pattern, cleaned):
            value = re.sub(r"\s+", "", match)
            if value not in contacts:
                contacts.append(value)
    for match in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cleaned):
        if match not in contacts:
            contacts.append(match)
    return " / ".join(contacts[:3])


def _service_tags(text: str) -> list[str]:
    tags = []
    mapping = [
        ("冷链", "冷链"),
        ("冷藏", "冷藏"),
        ("冷冻", "冷冻"),
        ("生鲜", "生鲜"),
        ("农产品", "农产品"),
        ("同城", "同城配送"),
        ("配送", "配送"),
        ("干线", "干线运输"),
        ("仓储", "仓储"),
        ("cold chain", "冷链"),
    ]
    lower = text.lower()
    for key, label in mapping:
        if key.lower() in lower and label not in tags:
            tags.append(label)
    return tags[:5]


def _guess_service_scope(title: str, snippet: str, production_name: str, market_name: str, tags: list[str]) -> str:
    tag_text = "、".join(tags) if tags else "物流配送"
    text = f"{title} {snippet}"
    if production_name in text or market_name in text:
        return f"{production_name}至{market_name}相关{tag_text}"
    return f"需核实是否覆盖{production_name}至{market_name}，服务关键词：{tag_text}"


def _summarize_suppliers(items: list[dict]) -> str:
    lines = ["冷链物流供应商筛选结果"]
    for index, item in enumerate(items[:6], start=1):
        lines.extend(
            [
                f"{index}. {item.get('name', '供应商')}",
                f"平台: {item.get('platform', '')}；联系方式: {item.get('contact_method') or item.get('contact') or '平台在线联系/询价'}",
                f"服务: {item.get('service_scope', '')}",
                f"来源: {item.get('url', '')}",
            ]
        )
    return "\n".join(lines)


def _first_public_url(items: list[dict]) -> str:
    for item in items or []:
        url = str(item.get("url", "")).strip()
        if url.startswith("http") and not _is_unwanted_source_url(url):
            return url
    return ""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()


def _filter_public_results(items: list[dict]) -> list[dict]:
    filtered = []
    for item in items or []:
        url = str(item.get("url", "")).strip()
        if _is_unwanted_source_url(url):
            continue
        filtered.append(item)
    return filtered


def _is_unwanted_source_url(url: str) -> bool:
    value = str(url or "").lower()
    blocked = ("bai" + "du.com", "m." + "bai" + "du.com", "duckduckgo.com/y.js", "google.com/search", "bing.com/search")
    return any(marker in value for marker in blocked)


def _cache_key(production_name: str, market_name: str, query_tail: str) -> str:
    compact_query = re.sub(r"\s+", " ", query_tail or "").strip()[:80]
    return f"{LOGISTICS_CACHE_VERSION}|{production_name}|{market_name}|{compact_query}"


def _read_logistics_cache() -> dict:
    try:
        if LOGISTICS_CACHE_PATH.exists():
            return json.loads(LOGISTICS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def _write_logistics_cache(key: str, suppliers: list[dict], pending_kimi: bool = False) -> None:
    try:
        LOGISTICS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        cache = _read_logistics_cache()
        cache[key] = {"saved_at": time.time(), "suppliers": suppliers[:6], "pending_kimi": pending_kimi}
        LOGISTICS_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def build_market_recommendation(production_weather: dict, market_weather: dict, route: dict, market_name: str) -> str:
    rain_origin = _near_term_rain(production_weather)
    rain_market = _near_term_rain(market_weather)
    duration = route.get("duration_minutes")
    if rain_origin >= 8:
        return f"产地有明显降雨，优先抢采耐损耗低的成熟果菜，发往{market_name}前先做分级和防潮包装。"
    if rain_market >= 8:
        return f"目标市场有降雨，先联系档口确认到货时段，包装要防潮，必要时改走电商预售或冷链暂存。"
    if duration and duration > 180:
        return f"车程较长，建议走冷链或凌晨发车，先锁定{market_name}收购价再组织采收。"
    return f"两地天气相对平稳，可先询价锁单，再按{market_name}到货时段安排采收和装车。"


def _chunk(doc_name: str, chunk_type: str, text: str, source: str, entities: list[str]) -> dict:
    return {
        "chunk_id": f"{chunk_type}_{abs(hash(doc_name + source))}",
        "doc_name": doc_name,
        "source": source,
        "chunk_type": chunk_type,
        "source_type": "web_search" if source.startswith("http") else "document",
        "text": text,
        "score": 0.64,
        "entities": entities,
        "metadata": {
            "doc_name": doc_name,
            "source_path": source,
            "source_type": "web_search" if source.startswith("http") else "document",
        },
    }


def _summarize_items(items: list[dict], label: str) -> str:
    lines = [label]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. {item.get('title', label)}",
                f"链接: {item.get('url', '')}",
                f"摘要: {item.get('snippet', '')}",
            ]
        )
    return "\n".join(lines)


def _normalize_location(location: dict, fallback: dict) -> dict:
    loc = dict(fallback)
    loc.update({key: value for key, value in dict(location or {}).items() if value is not None and value != ""})
    loc.setdefault("short_name", loc.get("name", "位置"))
    return loc


def _pick_china_result(results: list[dict]) -> dict | None:
    for result in results:
        if result.get("country_code") == "CN":
            return result
    return None


def _is_private_or_local_ip(value: str) -> bool:
    if not value:
        return True
    try:
        ip = ipaddress.ip_address(value)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return True


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _max_rain(weather: dict) -> float:
    rains = [_to_float(weather.get("precipitation")) or 0]
    rains.extend((_to_float(item) or 0) for item in (weather.get("daily_precipitation_sum") or []))
    return max(rains or [0])


def _near_term_rain(weather: dict) -> float:
    for horizon in weather.get("weather_horizons") or []:
        if horizon.get("id") == "next3":
            return max(_to_float(horizon.get("rain_max")) or 0, (_to_float(horizon.get("rain_sum")) or 0) / 3)
    rains = [_to_float(weather.get("precipitation")) or 0]
    rains.extend((_to_float(item) or 0) for item in (weather.get("daily_precipitation_sum") or [])[:3])
    return max(rains or [0])
