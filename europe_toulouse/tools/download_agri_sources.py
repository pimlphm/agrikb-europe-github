from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources"
SOURCE_PAGES = RAW_ROOT / "source_pages"
INGEST_DOCS = RAW_ROOT / "docs_for_ingest"
AGROVOC_DIR = RAW_ROOT / "agrovoc"
CROP_ONTOLOGY_DIR = RAW_ROOT / "crop_ontology"
GEE_DIR = RAW_ROOT / "google_earth_engine"
TAIWAN_DIR = RAW_ROOT / "taiwan_open_data"
CHATGPT_DIR = RAW_ROOT / "chatgpt_share"


SOURCES = {
    "chatgpt_share": {
        "page": "https://chatgpt.com/share/6a11b7aa-d9b0-83ec-88d4-26e0cc66e50a",
    },
    "taiwan_organic": {
        "page": "https://data.gov.tw/en/datasets/49444",
        "json": "https://data.moa.gov.tw/Service/OpenData/Traceability/TraceabilityOrganic.aspx?IsTransData=1&UnitId=D45",
        "csv": "https://data.moa.gov.tw/Service/OpenData/Traceability/TraceabilityOrganic.aspx?FOTT=CSV&IsTransData=1&UnitId=D45",
        "xml": "https://data.moa.gov.tw/Service/OpenData/Traceability/TraceabilityOrganic.aspx?FOTT=Xml&IsTransData=1&UnitId=D45",
    },
    "agrovoc_interoperable_europe": {
        "page": "https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/agrovoc-thesaurus",
        "rdf_export": "https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/agrovoc-thesaurus/rdf-export",
        "official_core_rdf_zip": "https://agrovoc.fao.org/latestAgrovoc/agrovoc_core.rdf.zip",
    },
    "crop_ontology": {
        "home": "https://cropontology.org/",
        "api_help": "https://cropontology.org/api_help",
        "metadata": "https://cropontology.org/metadata",
        "ontos_stats": "https://cropontology.org/ontos_stats",
        "traits": "https://cropontology.org/brapi/v1/traits",
        "variables": "https://cropontology.org/brapi/v1/variables",
    },
    "google_earth_engine_agriculture": {
        "tag_page_zh_cn": "https://developers.google.com/earth-engine/datasets/tags/agriculture?hl=zh-cn",
    },
}


SELECTED_CROP_RDF = {
    "rice_CO_320": "https://cropontology.org/ontology/CO_320/rdf",
    "wheat_CO_321": "https://cropontology.org/ontology/CO_321/rdf",
    "maize_CO_322": "https://cropontology.org/ontology/CO_322/rdf",
    "cassava_CO_334": "https://cropontology.org/ontology/CO_334/rdf",
    "potato_CO_330": "https://cropontology.org/ontology/CO_330/rdf",
    "soybean_CO_336": "https://cropontology.org/ontology/CO_336/rdf",
    "cotton_CO_358": "https://cropontology.org/ontology/CO_358/rdf",
    "sunflower_CO_359": "https://cropontology.org/ontology/CO_359/rdf",
}


def ensure_dirs() -> None:
    for path in [
        RAW_ROOT,
        SOURCE_PAGES,
        INGEST_DOCS,
        AGROVOC_DIR,
        CROP_ONTOLOGY_DIR,
        GEE_DIR,
        TAIWAN_DIR,
        CHATGPT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, timeout: int = 120) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        html.unescape(url),
        headers={
            "User-Agent": "AgriKB/2026.05 public-source-ingest (+local knowledge base)",
            "Accept": "*/*",
        },
    )
    record = {"url": url, "file": str(dest.relative_to(ROOT)), "ok": False, "error": ""}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
        dest.write_bytes(data)
        record.update(
            {
                "ok": True,
                "bytes": dest.stat().st_size,
                "sha256": sha256(dest),
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "big5", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_tags(value: str) -> str:
    value = re.sub(r"<(script|style).*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def extract_title(page: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>|<title[^>]*>(.*?)</title>", page, flags=re.I | re.S)
    if not match:
        return ""
    return strip_tags(next(group for group in match.groups() if group))


def parse_taiwan_csv(csv_path: Path) -> tuple[list[str], list[dict]]:
    text = read_text(csv_path)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    fields = list(rows[0].keys()) if rows else []
    return fields, rows


def summarize_taiwan(manifest: list[dict]) -> None:
    csv_path = TAIWAN_DIR / "taiwan_organic_agriculture_information.csv"
    fields, rows = parse_taiwan_csv(csv_path) if csv_path.exists() else ([], [])
    status_counts: dict[str, int] = {}
    behavior_counts: dict[str, int] = {}
    products: dict[str, int] = {}
    for row in rows:
        status = row.get("Status") or row.get("驗證狀態") or ""
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
        behavior = row.get("BehaviorType") or row.get("驗證行為") or ""
        if behavior:
            behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1
        for item in re.split(r"[、,;；/／\s]+", row.get("Products", "") or ""):
            item = item.strip()
            if item:
                products[item] = products.get(item, 0) + 1
    top_products = sorted(products.items(), key=lambda item: item[1], reverse=True)[:30]

    lines = [
        "# 台湾有机农业开放资料",
        "",
        "来源链接: https://data.gov.tw/en/datasets/49444",
        "",
        "该资料集由台湾政府开放资料平台发布，字段包含农业产品经营者名称、地址、电话、产品项目、验证行为、验证机构、证书编号、有效期、验证状态、通讯地址和旧证书编号等。",
        "",
        f"- 下载记录数: {len(rows)}",
        f"- 字段: {', '.join(fields)}",
        "- 已保存原始格式: CSV, JSON, XML",
        "",
        "## 验证状态分布",
    ]
    for key, count in sorted(status_counts.items(), key=lambda item: item[1], reverse=True)[:20]:
        lines.append(f"- {key}: {count}")
    lines.append("")
    lines.append("## 验证行为分布")
    for key, count in sorted(behavior_counts.items(), key=lambda item: item[1], reverse=True)[:20]:
        lines.append(f"- {key}: {count}")
    lines.append("")
    lines.append("## 高频产品项目")
    for key, count in top_products:
        lines.append(f"- {key}: {count}")
    lines.append("")
    lines.append("## 样例记录")
    for idx, row in enumerate(rows[:8], start=1):
        name = row.get("Name", "")
        products_value = row.get("Products", "")
        company = row.get("CompanyName", "")
        effective = row.get("EffectiveDate", "")
        lines.append(f"{idx}. {name} | 产品: {products_value} | 验证机构: {company} | 有效期: {effective}")
    write_doc("01_taiwan_organic_agriculture_data.md", "\n".join(lines))


def extract_agrovoc_zip(manifest: list[dict]) -> Path | None:
    zip_path = AGROVOC_DIR / "agrovoc_core.rdf.zip"
    if not zip_path.exists():
        return None
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [name for name in zf.namelist() if name.lower().endswith((".rdf", ".xml", ".nt"))]
            if not names:
                return None
            chosen = names[0]
            target = AGROVOC_DIR / Path(chosen).name
            if not target.exists():
                target.write_bytes(zf.read(chosen))
            manifest.append(
                {
                    "url": f"zip://{zip_path.name}!/{chosen}",
                    "file": str(target.relative_to(ROOT)),
                    "ok": True,
                    "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                    "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            )
            return target
    except zipfile.BadZipFile:
        return None


def summarize_agrovoc(manifest: list[dict]) -> None:
    rdf_path = extract_agrovoc_zip(manifest)
    concept_rows: list[dict] = []
    if rdf_path and rdf_path.exists():
        try:
            context = ET.iterparse(rdf_path, events=("end",))
            for _, elem in context:
                if elem.tag.endswith("Concept"):
                    about = elem.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "")
                    labels: dict[str, str] = {}
                    broader = 0
                    for child in list(elem):
                        tag = child.tag.lower()
                        if tag.endswith("preflabel") or tag.endswith("altlabel"):
                            lang = child.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", "") or "und"
                            text = (child.text or "").strip()
                            if text and lang not in labels:
                                labels[lang] = text
                        if tag.endswith("broader"):
                            broader += 1
                    if about and labels:
                        concept_rows.append(
                            {
                                "uri": about,
                                "label_en": labels.get("en", ""),
                                "label_zh": labels.get("zh", "") or labels.get("zh-cn", ""),
                                "label_any": next(iter(labels.values()), ""),
                                "languages": ",".join(sorted(labels)[:12]),
                                "broader_links": str(broader),
                            }
                        )
                    elem.clear()
                    if len(concept_rows) >= 2500:
                        break
        except ET.ParseError:
            concept_rows = []

    sample_csv = AGROVOC_DIR / "agrovoc_concept_sample.csv"
    if concept_rows:
        with sample_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(concept_rows[0]))
            writer.writeheader()
            writer.writerows(concept_rows)
        manifest.append(
            {
                "url": "derived://agrovoc_core.rdf.zip concept sample",
                "file": str(sample_csv.relative_to(ROOT)),
                "ok": True,
                "bytes": sample_csv.stat().st_size,
                "sha256": sha256(sample_csv),
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )

    lines = [
        "# AGROVOC 农业多语言控制词表",
        "",
        "来源链接: https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/agrovoc-thesaurus",
        "",
        "AGROVOC 是 FAO 维护的农业多语言控制词表。此知识库保存了 Interoperable Europe 入口页、RDF 导出页，以及 AGROVOC 官方 latestAgrovoc Core RDF ZIP 原始包。",
        "",
        "## 接入方式",
        "- 原始包: data/raw/public_agriculture_sources/agrovoc/agrovoc_core.rdf.zip",
        "- 解包 RDF/XML: 已从 ZIP 中提取首个 RDF/XML 文件供后续解析使用",
        "- 检索摘要: 已抽取最多 2500 个概念样例为 CSV，便于本地知识库索引和快速预览",
        "",
        "## 概念样例",
    ]
    for row in concept_rows[:40]:
        label = row["label_zh"] or row["label_en"] or row["label_any"]
        lines.append(f"- {label} | {row['uri']}")
    if not concept_rows:
        lines.append("- RDF 样例解析未成功，但原始 ZIP 已保存，可用 RDF 工具继续处理。")
    write_doc("02_agrovoc_thesaurus_profile.md", "\n".join(lines))


def summarize_crop_ontology(manifest: list[dict]) -> None:
    metadata_path = CROP_ONTOLOGY_DIR / "metadata.yaml"
    metadata_text = read_text(metadata_path) if metadata_path.exists() else ""
    ontology_rows = []
    pattern = re.compile(
        r"id:\s*([A-Z0-9_]+).*?title:\s*([^\n]+).*?description:\s*\"?(.+?)(?=\s+homepage:)",
        flags=re.S,
    )
    for match in pattern.finditer(metadata_text):
        ontology_rows.append(
            {
                "id": match.group(1).strip(),
                "title": strip_tags(match.group(2)).strip('" '),
                "description": strip_tags(match.group(3)).strip('" '),
            }
        )

    ontologies_csv = CROP_ONTOLOGY_DIR / "crop_ontology_metadata_summary.csv"
    if ontology_rows:
        with ontologies_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "title", "description"])
            writer.writeheader()
            writer.writerows(ontology_rows)
        manifest.append(
            {
                "url": "derived://cropontology.org/metadata summary",
                "file": str(ontologies_csv.relative_to(ROOT)),
                "ok": True,
                "bytes": ontologies_csv.stat().st_size,
                "sha256": sha256(ontologies_csv),
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )

    trait_samples = []
    traits_path = CROP_ONTOLOGY_DIR / "brapi_traits.json"
    if traits_path.exists():
        try:
            data = json.loads(read_text(traits_path))
            results = data.get("result", {}).get("data", data.get("data", []))
            for item in results[:40]:
                trait_samples.append(
                    {
                        "traitDbId": item.get("traitDbId", ""),
                        "name": item.get("traitName") or item.get("name", ""),
                        "description": item.get("description", ""),
                    }
                )
        except json.JSONDecodeError:
            pass

    lines = [
        "# Crop Ontology 作物性状与观测变量",
        "",
        "来源链接: https://cropontology.org/",
        "",
        "Crop Ontology 提供作物性状、观测变量、测量方法、尺度和 RDF/BRAPI 接口。此知识库保存了首页、API 帮助页、元数据、统计信息、BRAPI traits/variables，以及若干重点作物 RDF。",
        "",
        f"- 识别到的作物 ontology 数: {len(ontology_rows)}",
        "- 已下载重点 RDF: rice, wheat, maize, cassava, potato, soybean, cotton, sunflower",
        "",
        "## 作物本体样例",
    ]
    for row in ontology_rows[:35]:
        lines.append(f"- {row['id']} | {row['title']}: {row['description'][:180]}")
    lines.append("")
    lines.append("## Trait 样例")
    for row in trait_samples[:25]:
        lines.append(f"- {row['traitDbId']} | {row['name']}: {row['description'][:180]}")
    write_doc("03_crop_ontology_profile.md", "\n".join(lines))


def parse_gee_links(page_path: Path) -> list[dict]:
    page = read_text(page_path)
    links = []
    for match in re.finditer(r'href="([^"]*/earth-engine/datasets/catalog/[^"]+)"[^>]*>(.*?)</a>', page, flags=re.I | re.S):
        href = html.unescape(match.group(1))
        if href.startswith("/"):
            href = "https://developers.google.com" + href
        if "hl=" not in href:
            sep = "&" if "?" in href else "?"
            href = f"{href}{sep}hl=zh-cn"
        title = strip_tags(match.group(2))
        if not title or title.lower() in {"landsat", "modis", "sentinel"}:
            continue
        if not any(item["url"] == href for item in links):
            links.append({"title": title, "url": href})
    return links


def summarize_gee(manifest: list[dict]) -> list[dict]:
    page_path = GEE_DIR / "earth_engine_agriculture_tag_zh_cn.html"
    links = parse_gee_links(page_path) if page_path.exists() else []
    csv_path = GEE_DIR / "earth_engine_agriculture_catalog_links.csv"
    if links:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url"])
            writer.writeheader()
            writer.writerows(links)
        manifest.append(
            {
                "url": "derived://developers.google.com/earth-engine/datasets/tags/agriculture",
                "file": str(csv_path.relative_to(ROOT)),
                "ok": True,
                "bytes": csv_path.stat().st_size,
                "sha256": sha256(csv_path),
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )
    lines = [
        "# Google Earth Engine 农业数据集目录",
        "",
        "来源链接: https://developers.google.com/earth-engine/datasets/tags/agriculture?hl=zh-cn",
        "",
        "该目录汇总 Earth Engine 中带 agriculture 标签的数据集，适合土地覆盖、作物类型、灌溉、蒸散、作物概率、农业温室气体排放、遥感影像和森林损失驱动等场景。",
        "",
        f"- 抽取农业目录链接数: {len(links)}",
        "- 注意: Earth Engine 数据本体通常需要在 GEE 账号/脚本环境中按 dataset id 调用；本地已保存目录元数据与页面快照。",
        "",
        "## 数据集链接",
    ]
    for item in links:
        lines.append(f"- {item['title']} | {item['url']}")
    write_doc("04_google_earth_engine_agriculture_catalog.md", "\n".join(lines))
    return links


def write_doc(name: str, text: str) -> None:
    target = INGEST_DOCS / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.strip() + "\n", encoding="utf-8")


def write_overview(manifest: list[dict]) -> None:
    ok_count = sum(1 for item in manifest if item.get("ok"))
    lines = [
        "# 农业公开知识源接入说明",
        "",
        f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "本目录按用户指定链接下载并整理公开农业知识源，用于 AgriKB 农业知识库检索、问答和知识图谱展示。",
        "",
        "## 指定来源链接",
        "- ChatGPT 分享页: https://chatgpt.com/share/6a11b7aa-d9b0-83ec-88d4-26e0cc66e50a",
        "- 台湾有机农业开放资料: https://data.gov.tw/en/datasets/49444",
        "- Interoperable Europe AGROVOC: https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/agrovoc-thesaurus",
        "- Crop Ontology: https://cropontology.org/",
        "- Google Earth Engine agriculture tag: https://developers.google.com/earth-engine/datasets/tags/agriculture?hl=zh-cn",
        "",
        "## 下载摘要",
        f"- 成功文件: {ok_count}",
        f"- manifest: data/raw/public_agriculture_sources/source_manifest.json",
        "- 检索摘要目录: data/raw/public_agriculture_sources/docs_for_ingest",
        "- 原始数据目录: data/raw/public_agriculture_sources",
        "",
        "## 知识库接入范围",
        "- AGROVOC: 保存入口页/RDF 导出页/官方 Core RDF ZIP，并抽取概念样例用于本地检索。",
        "- Crop Ontology: 保存首页/API/元数据/统计/traits/variables/重点作物 RDF。",
        "- Google Earth Engine: 保存 agriculture 标签页，并抽取数据集目录链接。",
        "- 台湾农业开放数据: 保存有机农业资料 CSV/JSON/XML，并统计经营主体、产品项目、认证字段。",
        "- ChatGPT 分享链接: 保存页面快照或访问失败记录，作为用户来源说明入口。",
    ]
    write_doc("00_public_agri_sources_overview.md", "\n".join(lines))


def write_chatgpt_note() -> None:
    page = CHATGPT_DIR / "chatgpt_share.html"
    status = "已保存页面快照。" if page.exists() and page.stat().st_size > 0 else "页面可能需要浏览器会话访问，已保留链接。"
    write_doc(
        "05_chatgpt_share_reference.md",
        "\n".join(
            [
                "# ChatGPT 分享链接来源记录",
                "",
                "来源链接: https://chatgpt.com/share/6a11b7aa-d9b0-83ec-88d4-26e0cc66e50a",
                "",
                status,
                "",
                "该链接作为用户提供的公开知识源入口之一，知识库已保存链接和下载尝试记录。若分享页包含需要登录或动态加载的内容，可在后续手动导出为 Markdown 后放入本目录重新导入。",
            ]
        ),
    )


def main() -> None:
    ensure_dirs()
    manifest: list[dict] = []

    download_plan = [
        (SOURCES["chatgpt_share"]["page"], CHATGPT_DIR / "chatgpt_share.html"),
        (SOURCES["taiwan_organic"]["page"], SOURCE_PAGES / "taiwan_data_gov_49444.html"),
        (SOURCES["taiwan_organic"]["json"], TAIWAN_DIR / "taiwan_organic_agriculture_information.json"),
        (SOURCES["taiwan_organic"]["csv"], TAIWAN_DIR / "taiwan_organic_agriculture_information.csv"),
        (SOURCES["taiwan_organic"]["xml"], TAIWAN_DIR / "taiwan_organic_agriculture_information.xml"),
        (SOURCES["agrovoc_interoperable_europe"]["page"], SOURCE_PAGES / "interoperable_europe_agrovoc.html"),
        (SOURCES["agrovoc_interoperable_europe"]["rdf_export"], AGROVOC_DIR / "interoperable_europe_agrovoc_rdf_export.rdf"),
        (SOURCES["agrovoc_interoperable_europe"]["official_core_rdf_zip"], AGROVOC_DIR / "agrovoc_core.rdf.zip"),
        (SOURCES["crop_ontology"]["home"], SOURCE_PAGES / "cropontology_home.html"),
        (SOURCES["crop_ontology"]["api_help"], SOURCE_PAGES / "cropontology_api_help.html"),
        (SOURCES["crop_ontology"]["metadata"], CROP_ONTOLOGY_DIR / "metadata.yaml"),
        (SOURCES["crop_ontology"]["ontos_stats"], CROP_ONTOLOGY_DIR / "ontos_stats.json"),
        (SOURCES["crop_ontology"]["traits"], CROP_ONTOLOGY_DIR / "brapi_traits.json"),
        (SOURCES["crop_ontology"]["variables"], CROP_ONTOLOGY_DIR / "brapi_variables.json"),
        (SOURCES["google_earth_engine_agriculture"]["tag_page_zh_cn"], GEE_DIR / "earth_engine_agriculture_tag_zh_cn.html"),
    ]
    for url, dest in download_plan:
        manifest.append(download(url, dest))

    for name, url in SELECTED_CROP_RDF.items():
        manifest.append(download(url, CROP_ONTOLOGY_DIR / f"{name}.rdf", timeout=180))

    gee_links = summarize_gee(manifest)
    for item in gee_links[:12]:
        parsed = urllib.parse.urlparse(item["url"])
        filename = Path(parsed.path).name or "dataset"
        manifest.append(download(item["url"], GEE_DIR / "dataset_pages" / f"{filename}.html", timeout=90))

    write_chatgpt_note()
    summarize_taiwan(manifest)
    summarize_agrovoc(manifest)
    summarize_crop_ontology(manifest)
    write_overview(manifest)

    manifest_path = RAW_ROOT / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = RAW_ROOT / "README.md"
    readme.write_text(
        "AgriKB public agriculture source downloads.\n\n"
        "See source_manifest.json and docs_for_ingest/*.md for knowledge-base-ready summaries.\n",
        encoding="utf-8",
    )
    print(json.dumps({"manifest": str(manifest_path), "records": len(manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
