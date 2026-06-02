from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup


SEARCH_TIMEOUT_SECONDS = 3


def search_web(query: str, max_results: int = 5) -> list[dict]:
    query = str(query or "").strip()
    if not query:
        return []
    limit = max(1, min(int(max_results or 5), 8))
    try:
        results = _duckduckgo_html_search(query, max_results=limit)
        if results:
            return results
    except Exception:
        pass
    try:
        results = _yahoo_html_search(query, max_results=limit)
        if results:
            return results
    except Exception:
        pass
    return _curated_public_agri_results(query, max_results=limit)


def web_results_as_chunks(results: list[dict]) -> list[dict]:
    chunks = []
    for index, item in enumerate(results or [], start=1):
        title = _clean(item.get("title", "联网资料"))
        url = str(item.get("url", "")).strip()
        snippet = _clean(item.get("snippet", ""))
        chunks.append(
            {
                "chunk_id": f"web_search_{index}_{abs(hash(url or title))}",
                "doc_name": title,
                "source": url,
                "chunk_type": "web_search",
                "source_type": "web_search",
                "text": f"联网搜索结果: {title}\n链接: {url}\n摘要: {snippet}",
                "score": 0.62,
                "entities": ["联网搜索", "web_search"],
                "metadata": {
                    "doc_name": title,
                    "source_path": url,
                    "source_type": "web_search",
                    "url": url,
                },
            }
        )
    return chunks


def _duckduckgo_html_search(query: str, max_results: int) -> list[dict]:
    response = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            )
        },
        timeout=SEARCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result"):
        title_node = item.select_one(".result__a")
        if not title_node:
            continue
        title = _clean(title_node.get_text(" ", strip=True))
        url = _normalize_url(title_node.get("href") or "")
        snippet_node = item.select_one(".result__snippet")
        snippet = _clean(snippet_node.get_text(" ", strip=True) if snippet_node else "")
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet, "source_type": "web_search"})
        if len(results) >= max_results:
            break
    if results:
        return results
    response = requests.post(
        "https://lite.duckduckgo.com/lite/",
        data={"q": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=SEARCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.select("a.result-link"):
        title = _clean(link.get_text(" ", strip=True))
        url = _normalize_url(link.get("href") or "")
        if title and url:
            results.append({"title": title, "url": url, "snippet": "", "source_type": "web_search"})
        if len(results) >= max_results:
            break
    return results


def _yahoo_html_search(query: str, max_results: int) -> list[dict]:
    response = requests.get(
        "https://search.yahoo.com/search",
        params={"q": query},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            )
        },
        timeout=SEARCH_TIMEOUT_SECONDS + 4,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    seen = set()
    for item in soup.select("div.algo, div.dd.algo"):
        link = item.select_one("h3 a") or item.select_one("a")
        if not link:
            continue
        title = _clean_result_title(link.get_text(" ", strip=True))
        url = _normalize_url(link.get("href") or "")
        if not title or not url or _is_search_or_blocked_url(url):
            continue
        snippet_node = item.select_one(".compText, .fc-falcon, .lh-18")
        snippet = _clean_result_snippet(snippet_node.get_text(" ", strip=True) if snippet_node else "")
        key = url.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        results.append({"title": title, "url": url, "snippet": snippet[:360], "source_type": "web_search"})
        if len(results) >= max_results:
            break
    return results


def _curated_public_agri_results(query: str, max_results: int) -> list[dict]:
    text = str(query or "").lower()
    agri_markers = (
        "农业",
        "农产品",
        "批发市场",
        "价格",
        "行情",
        "种植",
        "农机",
        "肥料",
        "农资",
        "政策",
        "agri",
        "crop",
        "farm",
    )
    if not any(marker in text for marker in agri_markers):
        return []
    candidates = [
        {
            "title": "全国农产品批发市场价格信息系统",
            "url": "http://pfsc.agri.cn/",
            "snippet": "农业农村部相关公开价格入口，可查询全国农产品批发市场价格信息。",
        },
        {
            "title": "重点农产品市场信息平台",
            "url": "https://ncpscxx.moa.gov.cn/",
            "snippet": "农业农村部重点农产品市场信息公开平台，适合核验行情和市场数据。",
        },
        {
            "title": "中国价格信息网-农产品",
            "url": "https://jgjc.ndrc.gov.cn/ncp/index.jhtml",
            "snippet": "国家发展改革委价格监测相关公开信息入口，提供农产品价格参考。",
        },
        {
            "title": "农业农村部市场与信息化司",
            "url": "http://www.moa.gov.cn/govpublic/SCYJJXXS/",
            "snippet": "农业农村部市场与信息化司公开信息，适合查询市场、信息化和产业政策。",
        },
        {
            "title": "中国农业信息网",
            "url": "http://www.agri.cn/",
            "snippet": "农业农村部主管农业信息服务入口，覆盖农业资讯、市场和生产信息。",
        },
        {
            "title": "江苏省农业农村厅",
            "url": "https://nynct.jiangsu.gov.cn/",
            "snippet": "江苏省农业农村厅公开信息入口，适合查询江苏本地农业政策和产业动态。",
        },
    ]
    return [
        {**item, "source_type": "web_search", "fallback": "official_public_source"}
        for item in candidates[:max(1, max_results)]
    ]


def _normalize_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    if "r.search.yahoo.com" in href:
        match = re.search(r"/RU=([^/]+)", href)
        if match:
            return unquote(match.group(1))
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        return unquote(parse_qs(parsed.query).get("uddg", [""])[0])
    return href


def _is_search_or_blocked_url(url: str) -> bool:
    value = str(url or "").lower()
    blocked = (
        "search.yahoo.com/search",
        "r.search.yahoo.com",
        "duckduckgo.com",
        "google.com/search",
        "bing.com/search",
        "baidu.com",
        "m.baidu.com",
    )
    return any(marker in value for marker in blocked)


def _clean_result_title(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b(?:www\.)?[\w.-]+\.(?:com|cn|gov|org|net|edu)(?:/[^\s]*)?", " ", text, flags=re.I)
    if "›" in text or ">" in text:
        parts = [part.strip() for part in re.split(r"\s*[›>]\s*", text) if part.strip()]
        if parts:
            text = parts[-1]
    text = re.sub(r"\b[a-z]{2,24}\s*[-–]\s*", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -–|·")
    return text or _clean(value)[:120]


def _clean_result_snippet(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b(?:www\.)?[\w.-]+\.(?:com|cn|gov|org|net|edu)(?:/[^\s]*)?", " ", text, flags=re.I)
    text = re.sub(r"\s*[›>]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip(" -–|·")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()
