from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources"
DB_PATH = ROOT / "knowledge" / "chunks.db"
WIKI_DIR = ROOT / "knowledge" / "wiki"
CHUNK_DIR = ROOT / "knowledge" / "chunks"
MEMORY_DIR = ROOT / "knowledge" / "agent_memory"
SESSIONS_DIR = ROOT / "knowledge" / "sessions"


AGRI_TERMS = [
    "AGROVOC",
    "Crop Ontology",
    "Google Earth Engine",
    "有机农业",
    "有機農業",
    "农业开放数据",
    "作物",
    "产品项目",
    "认证",
    "驗證",
    "溯源",
    "遥感",
    "水稻",
    "小麦",
    "玉米",
    "马铃薯",
    "大豆",
    "棉花",
    "向日葵",
    "Rice",
    "Wheat",
    "Maize",
    "Potato",
    "Soybean",
    "Cotton",
    "Sunflower",
]


def assert_under_root(path: Path) -> Path:
    resolved = path.resolve()
    if not str(resolved).lower().startswith(str(ROOT.resolve()).lower()):
        raise RuntimeError(f"Refusing to write outside project root: {resolved}")
    return resolved


def reset_runtime_index() -> None:
    for path in [DB_PATH, WIKI_DIR, CHUNK_DIR, MEMORY_DIR, SESSIONS_DIR]:
        path = assert_under_root(path)
        if not path.exists():
            continue
        if path.is_file():
            path.unlink()
            continue
        for child in path.iterdir():
            if child.name == ".gitkeep":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    for path in [DB_PATH.parent, WIKI_DIR, CHUNK_DIR, MEMORY_DIR, SESSIONS_DIR]:
        assert_under_root(path).mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_name TEXT NOT NULL,
                source TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                text TEXT NOT NULL,
                entities_json TEXT NOT NULL,
                conditions_json TEXT NOT NULL,
                relations_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def token_count(text: str) -> int:
    return len(re.findall(r"[\w\u4e00-\u9fff]+", text))


def infer_entities(text: str, extra: list[str] | None = None) -> list[str]:
    entities = []
    lower = text.lower()
    for term in AGRI_TERMS:
        if term.lower() in lower:
            entities.append(term)
    for term in extra or []:
        if term and term not in entities:
            entities.append(term)
    for match in re.findall(r"\b(?:CO_\d{3}|[A-Z]{2,}[A-Z0-9_-]{2,})\b", text):
        if match not in entities:
            entities.append(match)
    return entities[:24]


def chunk(
    doc_name: str,
    chunk_type: str,
    text: str,
    source: str,
    index: int,
    entities: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    chunk_id = f"{Path(doc_name).stem}_{index:04d}_{stable_id(text)[:8]}"
    meta = {
        "doc_id": Path(doc_name).stem,
        "doc_name": doc_name,
        "source_path": source,
        "tokens": token_count(text),
        "stage": "curated_agriculture_index",
        "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if metadata:
        meta.update(metadata)
    return {
        "chunk_id": chunk_id,
        "doc_name": doc_name,
        "source": source,
        "chunk_type": chunk_type,
        "text": text.strip(),
        "entities": infer_entities(text, entities),
        "conditions": [],
        "relations": [{"type": "agriculture_source_profile", "confidence": 0.84}],
        "metadata": meta,
    }


def insert_chunks(chunks: list[dict]) -> None:
    if not chunks:
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
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


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "big5", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def paragraph_chunks(path: Path, doc_name: str, source_type: str, entities: list[str]) -> list[dict]:
    text = read_text(path)
    blocks = [block.strip() for block in re.split(r"\n(?=# |\n## |\n- |\d+\. )", text) if block.strip()]
    grouped: list[str] = []
    buffer = ""
    for block in blocks:
        if len(buffer) + len(block) < 1800:
            buffer = f"{buffer}\n{block}".strip()
        else:
            if buffer:
                grouped.append(buffer)
            buffer = block
    if buffer:
        grouped.append(buffer)
    return [
        chunk(
            doc_name=doc_name,
            chunk_type=source_type,
            text=item,
            source=str(path.relative_to(ROOT)),
            index=i,
            entities=entities,
            metadata={"source_type": "document"},
        )
        for i, item in enumerate(grouped, start=1)
    ]


def write_wiki(name: str, title: str, body: str) -> None:
    target = WIKI_DIR / name
    target.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    text = read_text(path)
    rows = list(csv.DictReader(text.splitlines()))
    fields = list(rows[0].keys()) if rows else []
    return fields, rows


def build_taiwan_chunks(chunks: list[dict]) -> None:
    canonical = RAW_ROOT / "taiwan_open_data" / "taiwan_organic_agriculture_information.csv"
    user_supplied = RAW_ROOT / "user_supplied" / "COA_OpenData.csv"
    fields, rows = load_csv(user_supplied if user_supplied.exists() else canonical)
    status_counts = Counter(row.get("Status", "") for row in rows if row.get("Status"))
    org_counts = Counter(row.get("CompanyName", "") for row in rows if row.get("CompanyName"))
    product_counts: Counter[str] = Counter()
    crop_counts: Counter[str] = Counter()
    county_counts: Counter[str] = Counter()
    org_products: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        address = row.get("Address", "")
        county = address[:3] if address else "未知"
        county_counts[county] += 1
        org = row.get("CompanyName", "") or "未知机构"
        for item in re.split(r"[、,;；/／\s]+", row.get("Products", "") or ""):
            item = item.strip()
            if item:
                product_counts[item] += 1
                org_products[org][item] += 1
        for item in re.split(r"[、,;；/／\s]+", row.get("ContainCrops", "") or ""):
            item = item.strip().replace("（", "(").replace("）", ")")
            if item and len(item) <= 24:
                crop_counts[item] += 1

    source = str(user_supplied.relative_to(ROOT)) if user_supplied.exists() else str(canonical.relative_to(ROOT))
    summary_lines = [
        "台湾有机农业开放资料 / COA_OpenData.csv 已接入 AgriKB。",
        f"记录数: {len(rows)}。",
        f"字段: {', '.join(fields)}。",
        "验证状态: " + "; ".join(f"{k} {v}" for k, v in status_counts.most_common()),
        "主要产品类别: " + "; ".join(f"{k} {v}" for k, v in product_counts.most_common(25)),
        "主要实际作物: " + "; ".join(f"{k} {v}" for k, v in crop_counts.most_common(25)),
        "地区分布: " + "; ".join(f"{k} {v}" for k, v in county_counts.most_common(20)),
        "主要验证机构: " + "; ".join(f"{k} {v}" for k, v in org_counts.most_common(20)),
    ]
    chunks.append(
        chunk(
            "台湾有机农业开放资料_COA_OpenData.csv",
            "taiwan_open_data_summary",
            "\n".join(summary_lines),
            source,
            1,
            ["台湾有机农业开放资料", "COA_OpenData.csv", "有机农业", "认证"],
        )
    )

    for i, (county, count) in enumerate(county_counts.most_common(24), start=2):
        county_rows = [row for row in rows if (row.get("Address", "")[:3] if row.get("Address") else "未知") == county]
        county_products = Counter()
        county_orgs = Counter()
        for row in county_rows:
            county_orgs[row.get("CompanyName", "") or "未知机构"] += 1
            for item in re.split(r"[、,;；/／\s]+", row.get("Products", "") or ""):
                if item.strip():
                    county_products[item.strip()] += 1
        sample = []
        for row in county_rows[:6]:
            sample.append(
                f"{row.get('Name','')} | {row.get('Products','')[:70]} | {row.get('CompanyName','')} | {row.get('EffectiveDate','')}"
            )
        text = "\n".join(
            [
                f"{county} 有机农业主体数: {count}",
                "主要产品: " + "; ".join(f"{k} {v}" for k, v in county_products.most_common(12)),
                "主要验证机构: " + "; ".join(f"{k} {v}" for k, v in county_orgs.most_common(8)),
                "样例记录:",
                *sample,
            ]
        )
        chunks.append(
            chunk(
                "台湾有机农业开放资料_COA_OpenData.csv",
                "taiwan_county_profile",
                text,
                source,
                i,
                [county, "有机农业", "农业主体"],
                {"county": county},
            )
        )

    for i, (org, count) in enumerate(org_counts.most_common(20), start=100):
        text = "\n".join(
            [
                f"验证机构: {org}",
                f"记录数: {count}",
                "主要产品: " + "; ".join(f"{k} {v}" for k, v in org_products[org].most_common(14)),
            ]
        )
        chunks.append(
            chunk(
                "台湾有机农业开放资料_COA_OpenData.csv",
                "taiwan_certification_body",
                text,
                source,
                i,
                [org, "验证机构", "认证"],
            )
        )

    write_wiki(
        "taiwan_organic_agriculture_COA_OpenData.md",
        "台湾有机农业开放资料 / COA_OpenData.csv",
        "\n".join(summary_lines),
    )


def build_agrovoc_chunks(chunks: list[dict]) -> None:
    path = RAW_ROOT / "agrovoc" / "agrovoc_concept_sample.csv"
    if not path.exists():
        return
    _, rows = load_csv(path)
    for group_idx, start in enumerate(range(0, min(len(rows), 600), 40), start=1):
        group = rows[start : start + 40]
        lines = ["AGROVOC 多语言农业控制词表概念样例。"]
        for row in group:
            labels = " / ".join([row.get("label_zh", ""), row.get("label_en", ""), row.get("label_es", ""), row.get("label_fr", "")]).strip(" /")
            lines.append(f"- {labels} | URI: {row.get('uri','')}")
        chunks.append(
            chunk(
                "AGROVOC_thesaurus_concepts.csv",
                "agrovoc_concept_sample",
                "\n".join(lines),
                str(path.relative_to(ROOT)),
                group_idx,
                ["AGROVOC", "农业控制词表", "多语言术语"],
            )
        )


def build_crop_ontology_chunks(chunks: list[dict]) -> None:
    meta_path = RAW_ROOT / "crop_ontology" / "crop_ontology_metadata_summary.csv"
    if meta_path.exists():
        _, rows = load_csv(meta_path)
        for i, row in enumerate(rows, start=1):
            text = f"Crop Ontology 作物本体: {row.get('id')} | {row.get('title')}\n说明: {row.get('description')}"
            chunks.append(
                chunk(
                    "Crop_Ontology_metadata.csv",
                    "crop_ontology_metadata",
                    text,
                    str(meta_path.relative_to(ROOT)),
                    i,
                    ["Crop Ontology", row.get("id", ""), row.get("title", "")],
                )
            )

    for path in sorted((RAW_ROOT / "crop_ontology").glob("brapi_*_CO_*.json")):
        data = json.loads(read_text(path))
        result = data.get("result", [])
        items = result if isinstance(result, list) else result.get("data", [])
        kind = "trait" if "traits" in path.name else "variable"
        ontology_id = path.stem.rsplit("_", 1)[-1]
        for group_idx, start in enumerate(range(0, len(items), 8), start=1):
            group = items[start : start + 8]
            lines = [f"Crop Ontology {ontology_id} {kind} BRAPI 记录。"]
            for item in group:
                ident = (
                    item.get("traitDbId")
                    or item.get("traitId")
                    or item.get("observationVariableDbId")
                    or item.get("observationVariableId")
                    or item.get("variableDbId")
                    or ""
                )
                name = item.get("name") or item.get("traitName") or item.get("observationVariableName") or ""
                lines.append(f"- {ident} | {name}")
            chunks.append(
                chunk(
                    f"Crop_Ontology_{ontology_id}_{kind}.json",
                    f"crop_ontology_{kind}",
                    "\n".join(lines),
                    str(path.relative_to(ROOT)),
                    group_idx,
                    ["Crop Ontology", ontology_id, kind],
                )
            )


def build_gee_chunks(chunks: list[dict]) -> None:
    path = RAW_ROOT / "google_earth_engine" / "earth_engine_agriculture_catalog_links.csv"
    if not path.exists():
        return
    _, rows = load_csv(path)
    for group_idx, start in enumerate(range(0, len(rows), 12), start=1):
        group = rows[start : start + 12]
        lines = ["Google Earth Engine agriculture 标签数据集目录。"]
        for row in group:
            lines.append(f"- {row.get('title','')} | {row.get('url','')}")
        chunks.append(
            chunk(
                "Google_Earth_Engine_agriculture_catalog.csv",
                "gee_agriculture_dataset_catalog",
                "\n".join(lines),
                str(path.relative_to(ROOT)),
                group_idx,
                ["Google Earth Engine", "agriculture", "遥感"],
            )
        )


def build_manifest_chunks(chunks: list[dict]) -> None:
    path = RAW_ROOT / "source_manifest.json"
    if not path.exists():
        return
    data = json.loads(read_text(path))
    ok = [item for item in data if item.get("ok")]
    failed = [item for item in data if not item.get("ok")]
    lines = [
        "农业公开知识源下载与接入 manifest。",
        f"成功记录: {len(ok)}。",
        f"失败保留记录: {len(failed)}。",
        "用户补充文件 COA_OpenData.csv 与台湾开放资料 CSV 哈希一致，已作为 user_supplied 来源留痕。",
    ]
    for item in ok[:30]:
        lines.append(f"- {item.get('file')} | {item.get('url')}")
    chunks.append(
        chunk(
            "AgriKB_public_source_manifest.json",
            "source_manifest",
            "\n".join(lines),
            str(path.relative_to(ROOT)),
            1,
            ["manifest", "公开知识源", "COA_OpenData.csv"],
        )
    )


def update_manifest_for_user_file() -> None:
    manifest_path = RAW_ROOT / "source_manifest.json"
    if not manifest_path.exists():
        return
    data = json.loads(read_text(manifest_path))
    user_file = RAW_ROOT / "user_supplied" / "COA_OpenData.csv"
    if user_file.exists():
        record = {
            "url": "user-file://D:/微信存储/.../COA_OpenData.csv",
            "file": str(user_file.relative_to(ROOT)),
            "ok": True,
            "bytes": user_file.stat().st_size,
            "sha256": hashlib.sha256(user_file.read_bytes()).hexdigest(),
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "note": "User supplied file; hash matches data.gov.tw dataset 49444 CSV.",
        }
        data = [item for item in data if item.get("file") != record["file"] and item.get("url") != record["url"]]
        data.append(record)
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    reset_runtime_index()
    init_db()
    update_manifest_for_user_file()
    chunks: list[dict] = []

    docs = [
        ("00_public_agri_sources_overview.md", "public_sources_overview", ["公开知识源", "农业知识库"]),
        ("01_taiwan_organic_agriculture_data.md", "taiwan_open_data_summary", ["台湾有机农业开放资料"]),
        ("02_agrovoc_thesaurus_profile.md", "agrovoc_profile", ["AGROVOC"]),
        ("03_crop_ontology_profile.md", "crop_ontology_profile", ["Crop Ontology"]),
        ("04_google_earth_engine_agriculture_catalog.md", "gee_agriculture_profile", ["Google Earth Engine"]),
        ("05_chatgpt_share_reference.md", "chatgpt_share_reference", ["ChatGPT 分享链接"]),
    ]
    for doc, source_type, entities in docs:
        path = RAW_ROOT / "docs_for_ingest" / doc
        if path.exists():
            chunks.extend(paragraph_chunks(path, doc, source_type, entities))
            write_wiki(doc, Path(doc).stem, read_text(path)[:4000])

    build_taiwan_chunks(chunks)
    build_agrovoc_chunks(chunks)
    build_crop_ontology_chunks(chunks)
    build_gee_chunks(chunks)
    build_manifest_chunks(chunks)
    insert_chunks(chunks)
    print({"chunks": len(chunks), "db": str(DB_PATH)})


if __name__ == "__main__":
    main()
