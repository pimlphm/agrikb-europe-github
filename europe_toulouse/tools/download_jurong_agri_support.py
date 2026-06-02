from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources"
INGEST_DOCS = RAW_ROOT / "docs_for_ingest"
SUPPORT_ROOT = RAW_ROOT / "jurong_local_agri_support"
BOOK_DIR = SUPPORT_ROOT / "monographs"
REPORT_DIR = SUPPORT_ROOT / "reports"
HISTORY_DIR = SUPPORT_ROOT / "historical_data"
PAGE_DIR = SUPPORT_ROOT / "source_pages"
MANIFEST_PATH = SUPPORT_ROOT / "jurong_support_manifest.json"
CSV_MANIFEST_PATH = SUPPORT_ROOT / "jurong_support_manifest.csv"

USER_AGENT = "AgriKB/2026.05 public-agriculture-source-ingest"

BOOKS = [
    {
        "id": "fao_climate_smart_agriculture_sourcebook",
        "title": "Climate-Smart Agriculture Sourcebook",
        "url": "https://www.fao.org/4/i3325e/i3325e.pdf",
        "source": "FAO",
        "relevance": "适合江苏句容做气候风险、节水灌溉、绿色生产和政策决策支撑。",
    },
    {
        "id": "fao_save_and_grow_maize_rice_wheat",
        "title": "Save and Grow in practice: maize, rice, wheat",
        "url": "https://www.fao.org/3/a-i4009e.pdf",
        "source": "FAO",
        "relevance": "适合支撑江苏句容水稻、粮食安全、绿色高产和节本增效问答。",
    },
    {
        "id": "fao_greenhouse_vegetable_gap",
        "title": "Good Agricultural Practices for greenhouse vegetable crops",
        "url": "https://www.fao.org/3/i3284e/i3284e.pdf",
        "source": "FAO",
        "relevance": "适合支撑草莓、设施蔬菜、棚室水肥管理和质量安全。",
    },
    {
        "id": "fao_small_scale_aquaponic_food_production",
        "title": "Small-scale aquaponic food production",
        "url": "https://www.fao.org/3/i4021e/i4021e.pdf",
        "source": "FAO",
        "relevance": "适合支撑鱼菜共生、水产和设施农业融合场景。",
    },
    {
        "id": "fao_land_water_resources_solaw",
        "title": "The State of the World's Land and Water Resources for Food and Agriculture",
        "url": "https://www.fao.org/4/i1688e/i1688e.pdf",
        "source": "FAO",
        "relevance": "适合支撑耕地、水资源、土壤退化、高标准农田和生态农业判断。",
    },
    {
        "id": "fao_future_food_agriculture_trends",
        "title": "The future of food and agriculture: trends and challenges",
        "url": "https://www.fao.org/3/i6583e/i6583e.pdf",
        "source": "FAO",
        "relevance": "适合支撑农业产业趋势、经营风险、市场与政策研判。",
    },
]

LOCAL_CHANNELS = [
    ("今日句容", "https://www.jurong.gov.cn/jurong/jrjr/list.shtml", "/jurong/jrjr/"),
    ("乡镇动态", "https://www.jurong.gov.cn/jurong/xzdt/list.shtml", "/jurong/xzdt/"),
    ("部门动态", "https://www.jurong.gov.cn/jurong/bmdt/list.shtml", "/jurong/bmdt/"),
]

AGRI_KEYWORDS = {
    "农业": 6,
    "现代农业": 9,
    "农业强市": 8,
    "农业产业": 8,
    "农业农村": 7,
    "农产品": 7,
    "农文旅": 8,
    "农旅": 6,
    "乡村振兴": 7,
    "富民": 4,
    "强村": 4,
    "粮食": 7,
    "水稻": 8,
    "稻米": 8,
    "稻": 4,
    "高标准农田": 8,
    "草莓": 9,
    "葡萄": 9,
    "茶": 5,
    "茶叶": 8,
    "福桃": 8,
    "桃": 5,
    "桑": 5,
    "葛根": 6,
    "蔬菜": 6,
    "水产": 6,
    "渔": 4,
    "养殖": 5,
    "种植": 5,
    "合作社": 7,
    "家庭农场": 7,
    "龙头企业": 5,
    "产业园": 7,
    "农机": 5,
    "农技": 5,
    "农户": 5,
    "戴庄": 8,
    "丁庄": 8,
    "白兔": 6,
    "茅山": 4,
    "后白": 4,
    "天王": 4,
    "郭庄": 4,
    "边城": 4,
}

HISTORY_KEYWORDS = (
    "农林牧渔",
    "农业",
    "林业",
    "牧业",
    "渔业",
    "粮食",
    "播种",
    "农村居民",
    "农民",
    "高标准农田",
    "农产品",
)


def ensure_dirs() -> None:
    for path in (SUPPORT_ROOT, BOOK_DIR, REPORT_DIR, HISTORY_DIR, PAGE_DIR, INGEST_DOCS):
        path.mkdir(parents=True, exist_ok=True)


def request(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        html.unescape(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def textify(value: str) -> str:
    value = re.sub(r"<(script|style).*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s+", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def slugify(value: str, limit: int = 54) -> str:
    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", value)
    slug = "_".join(tokens)[:limit].strip("_")
    return slug or hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def extract_title(page: str) -> str:
    patterns = [
        r"<h1[^>]*class=[\"'][^\"']*article-title[^\"']*[\"'][^>]*>(.*?)</h1>",
        r"<UCAPTITLE>(.*?)</UCAPTITLE>",
        r"<meta[^>]+name=[\"']ArticleTitle[\"'][^>]+content=[\"']([^\"']+)[\"']",
        r"<title[^>]*>(.*?)</title>",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.I | re.S)
        if match:
            return textify(match.group(1)).replace("| 句容市人民政府", "").strip()
    return ""


def extract_date(page: str) -> str:
    patterns = [
        r"<PUBLISHTIME>\s*([^<]+)\s*</PUBLISHTIME>",
        r"发布日期[:：]\s*<b>\s*([^<]+)\s*</b>",
        r"发布时间[:：]?\s*([0-9]{4}[-年][0-9]{1,2}[-月][0-9]{1,2})",
        r"([0-9]{4}-[0-9]{2}-[0-9]{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.I | re.S)
        if match:
            return textify(match.group(1)).replace("年", "-").replace("月", "-").replace("日", "")[:16].strip()
    return ""


def extract_source(page: str) -> str:
    match = re.search(r"来源[:：]\s*<b>\s*(.*?)\s*</b>", page, flags=re.I | re.S)
    return textify(match.group(1)) if match else "句容市人民政府公开信息"


def extract_article_body(page: str) -> str:
    patterns = [
        r"<UCAPCONTENT>(.*?)</UCAPCONTENT>",
        r"<div[^>]+id=[\"']zoomcon[\"'][^>]*>(.*?)</div>\s*<div class=[\"']article-reldocuments",
        r"<div[^>]+class=[\"'][^\"']*article-content[^\"']*[\"'][^>]*>(.*?)</div>\s*<div class=[\"']article-reldocuments",
        r"<body[^>]*>(.*?)</body>",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.I | re.S)
        if match:
            body = textify(match.group(1))
            if len(body) > 160:
                return body
    return textify(page)


def download_books(manifest: list[dict]) -> list[dict]:
    records: list[dict] = []
    for book in BOOKS:
        path = BOOK_DIR / f"{book['id']}.pdf"
        record = {
            "kind": "open_monograph",
            "title": book["title"],
            "url": book["url"],
            "source": book["source"],
            "file": str(path.relative_to(ROOT)),
            "relevance": book["relevance"],
            "ok": False,
            "error": "",
        }
        try:
            if not path.exists() or path.stat().st_size < 1024:
                path.write_bytes(request(book["url"], timeout=180))
            record.update({"ok": True, "bytes": path.stat().st_size, "sha256": sha256(path)})
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
        manifest.append(record)
    return records


def discover_channel_links(channel_name: str, list_url: str, path_marker: str) -> list[dict]:
    first_page = decode_text(request(list_url, timeout=60))
    page_count_match = re.search(r"createPageHTML\('page_div',\s*(\d+),", first_page)
    page_count = int(page_count_match.group(1)) if page_count_match else 1
    pages = [list_url] + [
        urllib.parse.urljoin(list_url, f"list_{index}.shtml") for index in range(2, page_count + 1)
    ]
    links: list[dict] = []
    seen: set[str] = set()
    for page_url in pages:
        try:
            page = first_page if page_url == list_url else decode_text(request(page_url, timeout=45))
        except Exception:
            continue
        for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", page, flags=re.I | re.S):
            attrs, inner = match.groups()
            href_match = re.search(r"href=[\"']([^\"']+)[\"']", attrs, flags=re.I)
            if not href_match:
                continue
            href = urllib.parse.urljoin(page_url, href_match.group(1))
            if path_marker not in href or not href.endswith(".shtml") or href in seen:
                continue
            title_match = re.search(r"title=[\"']([^\"']+)[\"']", attrs, flags=re.I | re.S)
            title = title_match.group(1).strip() if title_match else textify(inner)
            if not title or title in {"今日句容", "乡镇动态", "部门动态"}:
                continue
            links.append({"channel": channel_name, "title": title, "url": href})
            seen.add(href)
    return links


def article_score(title: str, body: str) -> int:
    haystack = f"{title}\n{body[:2500]}"
    score = 0
    for keyword, weight in AGRI_KEYWORDS.items():
        count = haystack.count(keyword)
        if count:
            score += min(count, 4) * weight
    return score


def is_agri_article(title: str, body: str, score: int) -> bool:
    if len(body) < 220 or score < 12:
        return False
    if "句容" not in body[:1600] and not any(place in f"{title}{body[:1600]}" for place in ("茅山", "白兔", "丁庄", "戴庄")):
        return False
    return True


def download_local_reports(manifest: list[dict], target_count: int = 60) -> list[dict]:
    discovered: list[dict] = []
    for channel_name, list_url, path_marker in LOCAL_CHANNELS:
        discovered.extend(discover_channel_links(channel_name, list_url, path_marker))

    title_prefiltered = [
        {**item, "title_score": article_score(item["title"], "")}
        for item in discovered
        if article_score(item["title"], "") >= 4
    ]
    title_prefiltered.sort(key=lambda item: item["title_score"], reverse=True)
    if len(title_prefiltered) < target_count * 2:
        prefiltered_urls = {item["url"] for item in title_prefiltered}
        fallback = [
            {**item, "title_score": 0}
            for item in discovered
            if item["url"] not in prefiltered_urls
        ]
        title_prefiltered.extend(fallback[: target_count * 3])

    candidates: list[dict] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    for item in title_prefiltered[: max(target_count * 6, 260)]:
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        try:
            raw = request(item["url"], timeout=60)
            page = decode_text(raw)
        except Exception:
            continue
        title = extract_title(page) or item["title"]
        title_key = re.sub(r"\s+", "", title)
        if title_key in seen_titles:
            continue
        body = extract_article_body(page)
        score = article_score(title, body)
        if not is_agri_article(title, body, score):
            continue
        candidates.append(
            {
                **item,
                "title": title,
                "date": extract_date(page),
                "source": extract_source(page),
                "score": score,
                "body": body,
                "raw": raw,
            }
        )
        seen_titles.add(title_key)
        if len(candidates) >= target_count * 2:
            break

    candidates.sort(key=lambda item: (item["score"], item.get("date", "")), reverse=True)
    selected = candidates[:target_count]
    records: list[dict] = []
    for index, item in enumerate(selected, start=1):
        slug = slugify(item["title"])
        page_path = PAGE_DIR / f"report_{index:02d}_{slug}.html"
        md_path = REPORT_DIR / f"{index:02d}_{slug}.md"
        page_path.write_bytes(item.pop("raw"))
        md_text = "\n".join(
            [
                f"# {item['title']}",
                "",
                f"- 类型: 江苏句容本地农业产业报道",
                f"- 栏目: {item['channel']}",
                f"- 来源: {item['source']}",
                f"- 日期: {item['date']}",
                f"- 原文链接: {item['url']}",
                f"- 农业相关评分: {item['score']}",
                "",
                "## 正文",
                "",
                item["body"],
                "",
            ]
        )
        md_path.write_text(md_text, encoding="utf-8")
        record = {
            "kind": "jurong_local_agri_report",
            "title": item["title"],
            "date": item["date"],
            "source": item["source"],
            "channel": item["channel"],
            "url": item["url"],
            "score": item["score"],
            "file": str(md_path.relative_to(ROOT)),
            "source_page": str(page_path.relative_to(ROOT)),
            "ok": True,
            "bytes": md_path.stat().st_size,
            "sha256": sha256(md_path),
        }
        records.append(record)
        manifest.append(record)
    return records


def discover_stat_links() -> list[dict]:
    url = "https://www.jurong.gov.cn/jrtjj/tjgb/jrxxgkpt_list.shtml"
    page = decode_text(request(url, timeout=60))
    links: list[dict] = []
    seen: set[str] = set()
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", page, flags=re.I | re.S):
        attrs, inner = match.groups()
        href_match = re.search(r"href=[\"']([^\"']+)[\"']", attrs, flags=re.I)
        if not href_match:
            continue
        title_match = re.search(r"title=[\"']([^\"']+)[\"']", attrs, flags=re.I | re.S)
        title = title_match.group(1).strip() if title_match else textify(inner)
        if "国民经济和社会发展统计公报" not in title:
            continue
        href = urllib.parse.urljoin(url, href_match.group(1))
        if href in seen:
            continue
        seen.add(href)
        year_match = re.search(r"(20\d{2})", title)
        links.append({"title": title, "url": href, "year": year_match.group(1) if year_match else ""})
    links.sort(key=lambda item: item.get("year", ""), reverse=True)
    return links


def extract_history_lines(body: str) -> list[str]:
    lines = []
    for raw_line in re.split(r"[\n。；;]", body):
        line = raw_line.strip()
        if len(line) < 8:
            continue
        if any(keyword in line for keyword in HISTORY_KEYWORDS):
            lines.append(line)
    return lines[:80]


def download_historical_data(manifest: list[dict]) -> list[dict]:
    records: list[dict] = []
    for item in discover_stat_links():
        try:
            raw = request(item["url"], timeout=60)
            page = decode_text(raw)
        except Exception:
            continue
        title = extract_title(page) or item["title"]
        body = extract_article_body(page)
        history_lines = extract_history_lines(body)
        if not history_lines:
            continue
        year = item.get("year") or "unknown"
        md_path = HISTORY_DIR / f"jurong_statistics_{year}.md"
        page_path = PAGE_DIR / f"statistics_{year}.html"
        page_path.write_bytes(raw)
        md_text = "\n".join(
            [
                f"# {title}",
                "",
                "- 类型: 江苏句容本地历史统计数据",
                "- 来源: 句容市统计局",
                f"- 年份: {year}",
                f"- 原文链接: {item['url']}",
                "",
                "## 农业相关摘录",
                "",
                *[f"- {line}" for line in history_lines],
                "",
                "## 原文抽取正文",
                "",
                body,
                "",
            ]
        )
        md_path.write_text(md_text, encoding="utf-8")
        record = {
            "kind": "jurong_historical_statistics",
            "title": title,
            "year": year,
            "source": "句容市统计局",
            "url": item["url"],
            "file": str(md_path.relative_to(ROOT)),
            "source_page": str(page_path.relative_to(ROOT)),
            "ok": True,
            "bytes": md_path.stat().st_size,
            "sha256": sha256(md_path),
        }
        records.append(record)
        manifest.append(record)
    return records


def write_ingest_summaries(book_records: list[dict], history_records: list[dict], report_records: list[dict]) -> list[Path]:
    book_lines = [
        "# 江苏句容农业后台专著资料目录",
        "",
        "说明：本目录只纳入公开可下载或机构开放发布的农业专著、手册和源书，不包含盗版商业图书。",
        "",
    ]
    for record in book_records:
        book_lines.extend(
            [
                f"## {record['title']}",
                "",
                f"- 来源: {record['source']}",
                f"- 原文链接: {record['url']}",
                f"- 本地文件: {record['file']}",
                f"- 适配江苏句容理由: {record['relevance']}",
                f"- 下载状态: {'成功' if record.get('ok') else '失败'}",
                "",
            ]
        )
    book_doc = INGEST_DOCS / "06_jurong_open_monograph_catalog.md"
    book_doc.write_text("\n".join(book_lines), encoding="utf-8")

    history_lines = [
        "# 江苏句容本地农业历史数据索引",
        "",
        "来源为句容市统计局历年国民经济和社会发展统计公报，重点抽取农林牧渔、粮食、农村居民收入等农业相关指标。",
        "",
    ]
    for record in history_records:
        history_lines.extend(
            [
                f"## {record['year']}年",
                "",
                f"- 标题: {record['title']}",
                f"- 原文链接: {record['url']}",
                f"- 本地文件: {record['file']}",
                "",
            ]
        )
    history_doc = INGEST_DOCS / "07_jurong_historical_agri_data.md"
    history_doc.write_text("\n".join(history_lines), encoding="utf-8")

    report_lines = [
        "# 江苏句容本地农业产业报道支持库",
        "",
        f"本批次去重保存 {len(report_records)} 篇江苏句容本地农业产业报道，来源优先为句容市人民政府公开栏目。",
        "",
    ]
    for index, record in enumerate(report_records, start=1):
        report_lines.extend(
            [
                f"## {index}. {record['title']}",
                "",
                f"- 日期: {record['date']}",
                f"- 栏目: {record['channel']}",
                f"- 来源: {record['source']}",
                f"- 原文链接: {record['url']}",
                f"- 本地文件: {record['file']}",
                f"- 主题强度: {record['score']}",
                "",
            ]
        )
    report_doc = INGEST_DOCS / "08_jurong_local_agri_reports_60.md"
    report_doc.write_text("\n".join(report_lines), encoding="utf-8")
    return [book_doc, history_doc, report_doc]


def write_manifest(manifest: list[dict]) -> None:
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "policy": "Only public official/open-license sources are downloaded. Commercial copyrighted books are excluded.",
        "records": manifest,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = sorted({key for row in manifest for key in row.keys()})
    with CSV_MANIFEST_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)


def main() -> None:
    ensure_dirs()
    manifest: list[dict] = []
    book_records = download_books(manifest)
    history_records = download_historical_data(manifest)
    report_records = download_local_reports(manifest, target_count=60)
    ingest_docs = write_ingest_summaries(book_records, history_records, report_records)
    for path in ingest_docs:
        manifest.append(
            {
                "kind": "derived_ingest_summary",
                "title": path.stem,
                "file": str(path.relative_to(ROOT)),
                "ok": True,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write_manifest(manifest)
    print(
        json.dumps(
            {
                "books": sum(1 for row in book_records if row.get("ok")),
                "history_docs": len(history_records),
                "reports": len(report_records),
                "manifest": str(MANIFEST_PATH),
                "ingest_docs": [str(path) for path in ingest_docs],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
