from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import time
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "delivery_expansion_20260523"
DOC_DIR = RAW_DIR / "docs_for_ingest"
POLICY_DIR = RAW_DIR / "policy_documents"
DATA_DIR = RAW_DIR / "open_data"
ASSET_DIR = ROOT / "web" / "assets" / "new-farmer-icons"
WIKI_DIR = ROOT / "knowledge" / "wiki"
DB_PATH = ROOT / "knowledge" / "chunks.db"


DATASET_PAGES = {
    "taiwan_daily_agricultural_product_prices": "https://data.gov.tw/dataset/8066",
    "taiwan_crop_unified_codes": "https://data.gov.tw/dataset/166558",
    "taiwan_traceable_organic_products": "https://data.gov.tw/dataset/126472",
    "taiwan_main_agricultural_import_export": "https://data.gov.tw/dataset/93697",
    "taiwan_major_ag_products_production": "https://data.gov.tw/dataset/96378",
    "taiwan_ag_income_price_index": "https://data.gov.tw/dataset/95728",
}

DIRECT_SOURCES = {
    "faostat_crops_livestock_normalized.zip": "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip",
    "world_bank_agriculture_value_added_usd.zip": "https://api.worldbank.org/v2/en/indicator/NV.AGR.TOTL.CD?downloadformat=csv",
    "world_bank_agriculture_value_added_percent_gdp.zip": "https://api.worldbank.org/v2/en/indicator/NV.AGR.TOTL.ZS?downloadformat=csv",
    "nasa_power_taipei_ag_weather_2025.csv": (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        "parameters=T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN&community=AG"
        "&longitude=121.5654&latitude=25.0330&start=20250101&end=20251231&format=CSV"
    ),
    "nasa_power_beijing_ag_weather_2025.csv": (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        "parameters=T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN&community=AG"
        "&longitude=116.4074&latitude=39.9042&start=20250101&end=20251231&format=CSV"
    ),
}

POLICY_SOURCES = {
    "gov_2025_high_quality_farmer_training.html": "https://www.gov.cn/zhengce/zhengceku/202506/content_7026209.htm",
    "moa_2024_reply_high_quality_farmers.html": "https://www.moa.gov.cn/govpublic/ncshsycjs/202408/t20240802_6460213.htm",
    "moe_new_professional_farmer_training_plan.html": "https://www.moe.gov.cn/srcsite/A07/s7055/201403/t20140321_166571.html",
    "moa_2025_bulletin_high_quality_farmer.pdf": "https://www.moa.gov.cn/nybgb/2025/202506/202507/P020250702370443551450.pdf",
}

DESIGN_REFERENCES = [
    ("Koru Farm", "https://www.koru.farm/en", "语音 AI 助手、多农场管理、作物分析。"),
    ("Trazo", "https://trazo.ag/", "从种子到销售的一体化农场管理平台。"),
    ("CropBuddy", "https://crop-buddy.com/", "安静、现代、以经营者日常工作为中心的农场软件。"),
    ("FarmGuide AI", "https://farmguide.ai/", "面向精准农业的端到端农场管理与农艺应用。"),
    ("Agera", "https://www.agera.farm/", "AI 农业平台，强调 NDVI、GIS 与数据看板。"),
    ("AgriOS", "https://getagrios.com/", "农业操作系统，强调审计导出和模块化配置。"),
]

ICON_SVGS = {
    "new_farmer": ("新农人", "#2f7d52", "M12 4a4 4 0 0 1 4 4v1h2v2h-2.2A6 6 0 0 1 6.2 11H4V9h2V8a4 4 0 0 1 6-4h6Zm-5 9h10l-1 7H8l-1-7Zm3-7h4v2h-4V6Z"),
    "policy": ("政策", "#416f9f", "M6 3h9l3 3v15H6V3Zm8 1.8V7h2.2L14 4.8ZM8 10h8v1.6H8V10Zm0 4h8v1.6H8V14Zm0 4h5v1.6H8V18Z"),
    "crop": ("作物", "#7a9f2f", "M12 21c-2-4-1.5-8.2 1.6-11.3C16.1 7.2 19.3 6.5 21 7c-.3 4.2-3.1 7.2-7.4 8.1A11 11 0 0 0 12 21ZM11 21c-1-4.6-3.2-7.4-8-8 .4-3.8 3.7-5.5 6.7-3.5 2.6 1.8 3 5.5 1.3 11.5Z"),
    "market": ("行情", "#b6852d", "M4 19h16v2H4v-2Zm1-8h3v6H5v-6Zm5-5h3v11h-3V6Zm5 3h3v8h-3V9Zm3.5-5 2.2 2.2-6.7 6.7-3-3-5.2 5.2-1.4-1.4L11 7.2l3 3L18.5 4Z"),
    "weather": ("气象", "#3f83b7", "M7 18a4 4 0 0 1 .8-7.9A5.5 5.5 0 0 1 18 12h.4a3 3 0 1 1 0 6H7Zm8-12 1.2-2 1.2 2 2.3.5-1.6 1.7.2 2.3-2.1-1-2.1 1 .2-2.3-1.6-1.7L15 6.1Z"),
    "traceability": ("溯源", "#8a5132", "M12 2 4 6v6c0 4.8 3.4 8.5 8 10 4.6-1.5 8-5.2 8-10V6l-8-4Zm0 3 5 2.5V12c0 3.1-2 5.8-5 7-3-1.2-5-3.9-5-7V7.5L12 5Zm-1 4h2v5h-2V9Zm0 6h2v2h-2v-2Z"),
    "bureau": ("农业局", "#5f6f63", "M4 20h16v2H4v-2Zm2-1V9l6-5 6 5v10h-2v-8H8v8H6Zm4-5h4v5h-4v-5Z"),
    "company": ("企业", "#7d678c", "M4 21V5l8-3 8 3v16h-2V7l-6-2.2L6 7v14H4Zm4-9h3v2H8v-2Zm5 0h3v2h-3v-2Zm-5 4h3v2H8v-2Zm5 0h3v2h-3v-2Z"),
}


def main() -> None:
    for path in (RAW_DIR, DOC_DIR, POLICY_DIR, DATA_DIR, ASSET_DIR, WIKI_DIR):
        path.mkdir(parents=True, exist_ok=True)
    manifest = []
    for slug, page_url in DATASET_PAGES.items():
        manifest.extend(download_dataset_page(slug, page_url))
    for filename, url in DIRECT_SOURCES.items():
        manifest.append(download_file(url, DATA_DIR / filename, source_name=filename))
    policy_records = [download_file(url, POLICY_DIR / filename, source_name=filename) for filename, url in POLICY_SOURCES.items()]
    manifest.extend(policy_records)

    docs = build_documents(manifest, policy_records)
    chunks = []
    for path, title, chunk_type, entities in docs:
        chunks.append(make_chunk(path.name, chunk_type, path.read_text(encoding="utf-8"), path, entities))
        write_wiki(path.name, title, path.read_text(encoding="utf-8"))
    write_icons()
    write_manifest(manifest)
    insert_chunks(chunks)
    print(json.dumps({"downloaded": len([m for m in manifest if m["ok"]]), "chunks_added": len(chunks), "raw_dir": str(RAW_DIR)}, ensure_ascii=False))


def download_dataset_page(slug: str, page_url: str) -> list[dict]:
    records = []
    page_path = DATA_DIR / f"{slug}.html"
    records.append(download_file(page_url, page_path, source_name=slug))
    html = page_path.read_text(encoding="utf-8", errors="ignore") if page_path.exists() else ""
    urls = []
    for match in re.findall(r"https://data\.moa\.gov\.tw/[^\"'\s<>]+", html):
        match = match.replace("&amp;", "&")
        if "FOTT=CSV" in match and match not in urls:
            urls.append(match)
    if urls:
        records.append(download_file(urls[0], DATA_DIR / f"{slug}.csv", source_name=slug))
    return records


def download_file(url: str, target: Path, source_name: str) -> dict:
    record = {"source": source_name, "url": url, "path": str(target.relative_to(ROOT)), "ok": False}
    try:
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        target.write_bytes(response.content)
        record.update({"ok": True, "status": response.status_code, "bytes": target.stat().st_size, "content_type": response.headers.get("content-type", "")})
    except Exception as exc:
        record.update({"error": f"{type(exc).__name__}: {exc}"[:240]})
    return record


def build_documents(manifest: list[dict], policy_records: list[dict]) -> list[tuple[Path, str, str, list[str]]]:
    data_doc = DOC_DIR / "delivery_open_agriculture_data.md"
    data_doc.write_text(build_data_summary(manifest), encoding="utf-8")
    policy_doc = DOC_DIR / "new_farmer_policy_pack.md"
    policy_doc.write_text(build_policy_summary(policy_records), encoding="utf-8")
    design_doc = DOC_DIR / "agri_agent_design_reference.md"
    design_doc.write_text(build_design_summary(), encoding="utf-8")
    icon_doc = DOC_DIR / "new_farmer_icon_catalog.md"
    icon_doc.write_text(build_icon_summary(), encoding="utf-8")
    return [
        (data_doc, "交付版公开农业数据扩展", "delivery_open_data_pack", ["农业局数据", "公开数据", "FAOSTAT", "NASA POWER", "World Bank", "台湾农业部"]),
        (policy_doc, "新农人政策文件包", "new_farmer_policy_pack", ["新农人", "高素质农民", "新型职业农民", "政策"]),
        (design_doc, "农业 Agent 软件界面参考", "agri_agent_design_reference", ["农业软件", "Agent", "界面设计", "农民", "农业局", "企业"]),
        (icon_doc, "新农人图标内嵌目录", "new_farmer_icon_pack", ["新农人", "图标", "政策", "作物", "溯源"]),
    ]


def build_data_summary(manifest: list[dict]) -> str:
    lines = ["# 交付版公开农业数据扩展", "", f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for item in manifest:
        status = "成功" if item.get("ok") else f"失败: {item.get('error', '')}"
        lines.append(f"- {item['source']}: {status} | {item['url']} | {item.get('path', '')}")
    lines.append("\n## CSV/ZIP 数据概览")
    for path in sorted(DATA_DIR.glob("*")):
        if path.suffix.lower() == ".csv":
            lines.extend(csv_profile(path))
        elif path.suffix.lower() == ".zip":
            lines.extend(zip_profile(path))
    return "\n".join(lines)


def csv_profile(path: Path) -> list[str]:
    rows = read_csv_rows(path, limit=5000)
    if not rows:
        return [f"\n### {path.name}", "- 未能解析表格内容。"]
    fields = list(rows[0].keys())
    lines = [f"\n### {path.name}", f"- 抽样行数: {len(rows)}", f"- 字段: {', '.join(fields[:18])}"]
    for field in fields[:8]:
        values = [str(row.get(field, "")).strip() for row in rows if str(row.get(field, "")).strip()]
        if not values:
            continue
        top = Counter(values).most_common(5)
        if len(top) > 1:
            lines.append(f"- {field} 高频值: " + "; ".join(f"{k} {v}" for k, v in top))
    return lines


def zip_profile(path: Path) -> list[str]:
    lines = [f"\n### {path.name}", f"- 文件大小: {path.stat().st_size:,} bytes"]
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            lines.append("- 压缩包文件: " + ", ".join(names[:6]))
            csv_name = next((name for name in names if name.lower().endswith(".csv")), "")
            if csv_name:
                with zf.open(csv_name) as f:
                    sample = f.read(1_200_000)
                text = decode_bytes(sample)
                rows = list(csv.DictReader(text.splitlines()))[:2000]
                if rows:
                    lines.append(f"- {csv_name} 抽样行数: {len(rows)}")
                    lines.append("- 字段: " + ", ".join(list(rows[0].keys())[:16]))
    except Exception as exc:
        lines.append(f"- 解析失败: {exc}")
    return lines


def build_policy_summary(policy_records: list[dict]) -> str:
    lines = ["# 新农人 / 高素质农民政策文件包", "", "本包内嵌官方政策页面与公报 PDF，供农业局、培训机构、合作社和企业做政策问答与培训材料检索。", ""]
    for item in policy_records:
        lines.append(f"## {item['source']}")
        lines.append(f"- 来源: {item['url']}")
        lines.append(f"- 本地文件: {item.get('path', '')}")
        local_path = ROOT / item.get("path", "")
        if item.get("ok") and item.get("path", "").lower().endswith(".html") and local_path.exists():
            text = extract_html_text(local_path)
            lines.append(f"- 正文摘录: {text[:900]}")
        elif not item.get("ok"):
            lines.append(f"- 下载状态: {item.get('error', '未成功下载')}")
        lines.append("")
    lines.append("## 可进入知识图谱的政策节点")
    lines.extend([
        "- 新农人 / 新型职业农民 / 高素质农民",
        "- 培育项目、资金管理、培训规范、质量评价",
        "- 农业经营主体、家庭农场、合作社、农业企业",
        "- 生产技术、经营管理、品牌营销、数字农业、乡村产业",
    ])
    return "\n".join(lines)


def build_design_summary() -> str:
    lines = ["# 农业 Agent 与农业软件界面参考", "", "界面设计不复制他站素材，只提炼交付版产品共性：简约、角色清晰、数据卡片、问答和操作入口集中。", ""]
    for name, url, note in DESIGN_REFERENCES:
        lines.append(f"- {name}: {url} | {note}")
    lines.extend([
        "",
        "## AgriKB 交付版设计原则",
        "- 首屏同时服务农民、农业局和商业公司三类角色。",
        "- 问答框、联网搜索、知识图谱和政策资料放在同一工作台。",
        "- 避免营销式大图，把数据、政策、行情、气象、溯源和报告导出做成清晰工具入口。",
        "- 使用低饱和农业绿、粮食金、信息蓝和土壤棕，卡片圆角保持克制。",
    ])
    return "\n".join(lines)


def build_icon_summary() -> str:
    lines = ["# 新农人图标内嵌目录", "", "图标为本项目内嵌 SVG，覆盖交付版首页和政策资料入口。", ""]
    for name, (label, _, _) in ICON_SVGS.items():
        lines.append(f"- {label}: web/assets/new-farmer-icons/{name}.svg")
    return "\n".join(lines)


def write_icons() -> None:
    for name, (label, color, path_data) in ICON_SVGS.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" role="img" aria-label="{label}">
  <rect width="24" height="24" rx="5" fill="{color}" opacity="0.12"/>
  <path d="{path_data}" fill="{color}"/>
</svg>
'''
        (ASSET_DIR / f"{name}.svg").write_text(svg, encoding="utf-8")


def write_manifest(manifest: list[dict]) -> None:
    (RAW_DIR / "source_manifest_delivery.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def make_chunk(doc_name: str, chunk_type: str, text: str, source: Path, entities: list[str]) -> dict:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return {
        "chunk_id": f"{Path(doc_name).stem}_{digest}",
        "doc_name": doc_name,
        "source": str(source.relative_to(ROOT)),
        "chunk_type": chunk_type,
        "text": text,
        "entities": entities,
        "conditions": [],
        "relations": [{"type": "delivery_expansion", "confidence": 0.88}],
        "metadata": {"doc_name": doc_name, "source_path": str(source.relative_to(ROOT)), "stage": "delivery_expansion_20260523"},
    }


def insert_chunks(chunks: list[dict]) -> None:
    if not chunks:
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO chunks (
                chunk_id, doc_name, source, chunk_type, text,
                entities_json, conditions_json, relations_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["chunk_id"],
                    item["doc_name"],
                    item["source"],
                    item["chunk_type"],
                    item["text"],
                    json.dumps(item["entities"], ensure_ascii=False),
                    json.dumps(item["conditions"], ensure_ascii=False),
                    json.dumps(item["relations"], ensure_ascii=False),
                    json.dumps(item["metadata"], ensure_ascii=False),
                )
                for item in chunks
            ],
        )
        conn.commit()


def write_wiki(filename: str, title: str, body: str) -> None:
    (WIKI_DIR / filename).write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def read_csv_rows(path: Path, limit: int = 5000) -> list[dict]:
    text = decode_bytes(path.read_bytes())
    try:
        return list(csv.DictReader(text.splitlines()))[:limit]
    except Exception:
        return []


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "big5", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


if __name__ == "__main__":
    main()
