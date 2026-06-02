from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge.ingestion.ingest_pipeline import IngestPipeline
from src.backend.utils import load_config


RAW_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources"
INGEST_DOCS = RAW_ROOT / "docs_for_ingest"
JURONG_SUPPORT_ROOT = RAW_ROOT / "jurong_local_agri_support"


def collect_paths() -> list[str]:
    paths: list[Path] = [
        INGEST_DOCS / "06_jurong_open_monograph_catalog.md",
        INGEST_DOCS / "07_jurong_historical_agri_data.md",
        INGEST_DOCS / "08_jurong_local_agri_reports_60.md",
        JURONG_SUPPORT_ROOT / "jurong_support_manifest.json",
        JURONG_SUPPORT_ROOT / "jurong_support_manifest.csv",
    ]
    paths.extend(sorted((JURONG_SUPPORT_ROOT / "reports").glob("*.md")))
    paths.extend(sorted((JURONG_SUPPORT_ROOT / "historical_data").glob("*.md")))
    if os.environ.get("AGRIKB_INGEST_FULL_MONOGRAPHS") == "1":
        paths.extend(sorted((JURONG_SUPPORT_ROOT / "monographs").glob("*.pdf")))
    return [str(path) for path in paths if path.exists() and path.stat().st_size > 0]


def main() -> None:
    config = load_config()
    pipeline = IngestPipeline(config)
    paths = collect_paths()
    summary = pipeline.ingest_paths(paths)
    print({"paths": len(paths), **summary, "chunk_db": str(pipeline.db_path)})


if __name__ == "__main__":
    main()
