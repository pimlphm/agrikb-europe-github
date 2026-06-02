from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources"
INGEST_DOCS = RAW_ROOT / "docs_for_ingest"
AGROVOC_DIR = RAW_ROOT / "agrovoc"
CROP_ONTOLOGY_DIR = RAW_ROOT / "crop_ontology"
GEE_DIR = RAW_ROOT / "google_earth_engine"
TAIWAN_DIR = RAW_ROOT / "taiwan_open_data"
MANIFEST_PATH = RAW_ROOT / "source_manifest.json"


TAIWAN_URLS = {
    "taiwan_organic_agriculture_information.json": "https://data.moa.gov.tw/Service/OpenData/Traceability/TraceabilityOrganic.aspx?IsTransData=1&UnitId=D45",
    "taiwan_organic_agriculture_information.csv": "https://data.moa.gov.tw/Service/OpenData/Traceability/TraceabilityOrganic.aspx?FOTT=CSV&IsTransData=1&UnitId=D45",
    "taiwan_organic_agriculture_information.xml": "https://data.moa.gov.tw/Service/OpenData/Traceability/TraceabilityOrganic.aspx?FOTT=Xml&IsTransData=1&UnitId=D45",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "big5", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_manifest() -> list[dict]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return []


def upsert_manifest(manifest: list[dict], url: str, path: Path) -> None:
    if not path.exists():
        return
    record = {
        "url": url,
        "file": rel(path),
        "ok": True,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "error": "",
    }
    for idx, item in enumerate(manifest):
        if item.get("url") == url or item.get("file") == rel(path):
            manifest[idx] = {**item, **record}
            return
    manifest.append(record)


def write_doc(name: str, text: str) -> Path:
    target = INGEST_DOCS / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.strip() + "\n", encoding="utf-8")
    return target


def parse_taiwan_csv() -> tuple[list[str], list[dict]]:
    path = TAIWAN_DIR / "taiwan_organic_agriculture_information.csv"
    if not path.exists():
        return [], []
    text = read_text(path)
    rows = list(csv.DictReader(text.splitlines()))
    fields = list(rows[0].keys()) if rows else []
    return fields, rows


def summarize_taiwan() -> Path:
    fields, rows = parse_taiwan_csv()
    status_counts: dict[str, int] = {}
    org_counts: dict[str, int] = {}
    products: dict[str, int] = {}
    crops: dict[str, int] = {}
    for row in rows:
        status = row.get("Status", "").strip()
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
        org = row.get("CompanyName", "").strip()
        if org:
            org_counts[org] = org_counts.get(org, 0) + 1
        for item in re.split(r"[、,;；/／\s]+", row.get("Products", "") or ""):
            item = item.strip()
            if item:
                products[item] = products.get(item, 0) + 1
        for item in re.split(r"[、,;；/／\s]+", row.get("ContainCrops", "") or ""):
            item = item.strip().replace("（", "(").replace("）", ")")
            if item and len(item) <= 24:
                crops[item] = crops.get(item, 0) + 1

    lines = [
        "# 台湾有机农业开放资料",
        "",
        "来源链接: https://data.gov.tw/en/datasets/49444",
        "",
        "该资料集由台湾政府开放资料平台发布，字段包含农业产品经营者名称、地址、电话、产品项目、实际作物、验证行为、验证机构、证书编号、有效期、验证状态、通讯地址和旧证书编号等。",
        "",
        f"- 下载记录数: {len(rows)}",
        f"- 字段: {', '.join(fields)}",
        "- 已保存原始格式: CSV, JSON, XML",
        "",
        "## 验证状态分布",
    ]
    for key, count in sorted(status_counts.items(), key=lambda item: item[1], reverse=True)[:20]:
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## 主要验证机构"])
    for key, count in sorted(org_counts.items(), key=lambda item: item[1], reverse=True)[:20]:
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## 高频产品类别"])
    for key, count in sorted(products.items(), key=lambda item: item[1], reverse=True)[:30]:
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## 高频作物"])
    for key, count in sorted(crops.items(), key=lambda item: item[1], reverse=True)[:30]:
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## 样例记录"])
    for idx, row in enumerate(rows[:10], start=1):
        name = row.get("Name", "")
        products_value = row.get("Products", "")[:80]
        company = row.get("CompanyName", "")
        effective = row.get("EffectiveDate", "")
        status = row.get("Status", "")
        lines.append(f"{idx}. {name} | 状态: {status} | 产品: {products_value} | 验证机构: {company} | 有效期: {effective}")
    return write_doc("01_taiwan_organic_agriculture_data.md", "\n".join(lines))


def parse_agrovoc_sample(limit: int = 2500) -> list[dict]:
    rdf_path = AGROVOC_DIR / "agrovoc_core.rdf"
    if not rdf_path.exists():
        return []

    label_by_uri: dict[str, dict[str, str]] = {}
    current_uri = ""
    with rdf_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            about = re.search(r'<rdf:Description rdf:about="([^"]+)"', line)
            if about:
                current_uri = html.unescape(about.group(1))
                continue
            if current_uri and "skosxl:literalForm" in line:
                match = re.search(r'xml:lang="([^"]+)">(.+?)</skosxl:literalForm>', line)
                if not match:
                    continue
                lang = match.group(1)
                if lang not in {"en", "zh", "zh-cn", "es", "fr"}:
                    continue
                text = html.unescape(strip_tags(match.group(2)))
                label_by_uri.setdefault(current_uri, {}).setdefault(lang, text)

    rows: list[dict] = []
    current_uri = ""
    current_pref: list[str] = []
    current_broader = 0

    def flush() -> None:
        nonlocal current_uri, current_pref, current_broader
        if not current_uri.startswith("http://aims.fao.org/aos/agrovoc/c_") or not current_pref:
            return
        labels: dict[str, str] = {}
        for pref_uri in current_pref:
            for lang, text in label_by_uri.get(pref_uri, {}).items():
                labels.setdefault(lang, text)
        if labels:
            rows.append(
                {
                    "uri": current_uri,
                    "label_zh": labels.get("zh") or labels.get("zh-cn", ""),
                    "label_en": labels.get("en", ""),
                    "label_es": labels.get("es", ""),
                    "label_fr": labels.get("fr", ""),
                    "broader_links": current_broader,
                }
            )

    with rdf_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            about = re.search(r'<rdf:Description rdf:about="([^"]+)"', line)
            if about:
                if current_uri and len(rows) < limit:
                    flush()
                if len(rows) >= limit:
                    break
                current_uri = html.unescape(about.group(1))
                current_pref = []
                current_broader = 0
                continue
            if not current_uri:
                continue
            if "skosxl:prefLabel" in line:
                resource = re.search(r'rdf:resource="([^"]+)"', line)
                if resource:
                    current_pref.append(html.unescape(resource.group(1)))
            elif "skos:broader" in line:
                current_broader += 1
    if current_uri and len(rows) < limit:
        flush()
    return rows[:limit]


def summarize_agrovoc(manifest: list[dict]) -> Path:
    rows = parse_agrovoc_sample()
    sample_csv = AGROVOC_DIR / "agrovoc_concept_sample.csv"
    if rows:
        with sample_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        upsert_manifest(manifest, "derived://agrovoc_core.rdf concept label sample", sample_csv)

    lines = [
        "# AGROVOC 农业多语言控制词表",
        "",
        "来源链接: https://interoperable-europe.ec.europa.eu/collection/eu-semantic-interoperability-catalogue/solution/agrovoc-thesaurus",
        "",
        "AGROVOC 是 FAO 维护的农业多语言控制词表。此知识库保存了 Interoperable Europe 入口页、RDF 导出页，以及 AGROVOC 官方 latestAgrovoc Core RDF ZIP 原始包。",
        "",
        "## 接入方式",
        "- 原始包: data/raw/public_agriculture_sources/agrovoc/agrovoc_core.rdf.zip",
        "- 解包 RDF/XML: data/raw/public_agriculture_sources/agrovoc/agrovoc_core.rdf",
        f"- 检索摘要: 已抽取 {len(rows)} 个概念样例为 CSV，便于本地知识库索引和快速预览",
        "",
        "## 概念样例",
    ]
    for row in rows[:80]:
        label = row["label_zh"] or row["label_en"] or row["label_es"] or row["label_fr"]
        labels = " / ".join([v for v in [row["label_zh"], row["label_en"], row["label_es"], row["label_fr"]] if v])
        lines.append(f"- {label}: {labels} | {row['uri']}")
    if not rows:
        lines.append("- 未能抽取概念样例，但原始 RDF/ZIP 已保存。")
    return write_doc("02_agrovoc_thesaurus_profile.md", "\n".join(lines))


def brapi_items(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return []
    result = data.get("result", [])
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        payload = result.get("data", [])
        return payload if isinstance(payload, list) else []
    return []


def summarize_crop_ontology() -> Path:
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

    selected_ids = ["CO_320", "CO_321", "CO_322", "CO_334", "CO_330", "CO_336", "CO_358", "CO_359"]
    selected_counts = []
    trait_samples = []
    variable_samples = []
    for oid in selected_ids:
        traits = brapi_items(CROP_ONTOLOGY_DIR / f"brapi_traits_{oid}.json")
        variables = brapi_items(CROP_ONTOLOGY_DIR / f"brapi_variables_{oid}.json")
        selected_counts.append((oid, len(traits), len(variables)))
        for item in traits[:5]:
            trait_samples.append((oid, item.get("traitDbId") or item.get("traitId") or "", item.get("name") or item.get("traitName") or ""))
        for item in variables[:4]:
            variable_samples.append((oid, item.get("observationVariableDbId") or item.get("observationVariableId") or item.get("variableDbId") or "", item.get("name") or item.get("observationVariableName") or ""))

    lines = [
        "# Crop Ontology 作物性状与观测变量",
        "",
        "来源链接: https://cropontology.org/",
        "",
        "Crop Ontology 提供作物性状、观测变量、测量方法、尺度和 RDF/BRAPI 接口。此知识库保存了首页、API 帮助页、元数据、统计信息、重点作物 traits/variables，以及若干重点作物 RDF。",
        "",
        f"- 识别到的作物 ontology 数: {len(ontology_rows)}",
        "- 已下载重点作物: rice, wheat, maize, cassava, potato, soybean, cotton, sunflower",
        "- 全量 traits/variables API 当前返回 500，已按重点作物调用 BRAPI-like 接口补齐。",
        "",
        "## 重点作物 traits/variables 数量",
    ]
    for oid, trait_count, variable_count in selected_counts:
        lines.append(f"- {oid}: traits {trait_count}, variables {variable_count}")
    lines.extend(["", "## 作物本体样例"])
    for row in ontology_rows[:35]:
        lines.append(f"- {row['id']} | {row['title']}: {row['description'][:180]}")
    lines.extend(["", "## Trait 样例"])
    for oid, trait_id, name in trait_samples[:45]:
        lines.append(f"- {oid} | {trait_id} | {name}")
    lines.extend(["", "## Variable 样例"])
    for oid, var_id, name in variable_samples[:35]:
        lines.append(f"- {oid} | {var_id} | {name}")
    return write_doc("03_crop_ontology_profile.md", "\n".join(lines))


def write_overview(manifest: list[dict]) -> Path:
    ok_count = sum(1 for item in manifest if item.get("ok"))
    failed = [item for item in manifest if not item.get("ok")]
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
        f"- 成功文件/派生文件: {ok_count}",
        f"- 保留失败记录: {len(failed)}",
        "- manifest: data/raw/public_agriculture_sources/source_manifest.json",
        "- 检索摘要目录: data/raw/public_agriculture_sources/docs_for_ingest",
        "- 原始数据目录: data/raw/public_agriculture_sources",
        "",
        "## 知识库接入范围",
        "- AGROVOC: 保存入口页/RDF 导出页/官方 Core RDF ZIP，并抽取概念样例用于本地检索。",
        "- Crop Ontology: 保存首页/API/元数据/统计/重点作物 traits/variables/重点作物 RDF。",
        "- Google Earth Engine: 保存 agriculture 标签页，并抽取数据集目录链接。",
        "- 台湾农业开放数据: 保存有机农业资料 CSV/JSON/XML，并统计经营主体、产品项目、认证字段。",
        "- ChatGPT 分享链接: 保存页面快照或访问失败记录，作为用户来源说明入口。",
    ]
    if failed:
        lines.extend(["", "## 补救说明"])
        lines.append("- Crop Ontology 全量 traits/variables 端点返回 500；已改用重点作物 traits/variables 接口接入。")
        lines.append("- 台湾资料已通过 PowerShell 成功下载 CSV/JSON/XML，并覆盖最初的证书校验失败记录。")
    return write_doc("00_public_agri_sources_overview.md", "\n".join(lines))


def main() -> None:
    manifest = load_manifest()
    for filename, url in TAIWAN_URLS.items():
        upsert_manifest(manifest, url, TAIWAN_DIR / filename)
    for path in CROP_ONTOLOGY_DIR.glob("brapi_traits_CO_*.json"):
        oid = path.stem.rsplit("_", 1)[-1]
        upsert_manifest(manifest, f"https://cropontology.org/brapi/v1/traits/{oid}", path)
    for path in CROP_ONTOLOGY_DIR.glob("brapi_variables_CO_*.json"):
        oid = path.stem.rsplit("_", 1)[-1]
        upsert_manifest(manifest, f"https://cropontology.org/brapi/v1/variables/{oid}", path)

    docs = [
        summarize_taiwan(),
        summarize_agrovoc(manifest),
        summarize_crop_ontology(),
    ]
    overview = write_overview(manifest)
    docs.append(overview)
    for doc in docs:
        upsert_manifest(manifest, f"derived://{doc.name}", doc)

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(MANIFEST_PATH), "records": len(manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
