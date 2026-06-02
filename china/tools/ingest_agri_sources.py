from __future__ import annotations

from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backend.service import KnowledgeBaseService
from src.backend.utils import load_config


RAW_ROOT = ROOT / "data" / "raw" / "public_agriculture_sources"
JURONG_SUPPORT_ROOT = RAW_ROOT / "jurong_local_agri_support"


def collect_paths() -> list[str]:
    paths: list[Path] = []
    paths.extend(sorted((RAW_ROOT / "docs_for_ingest").glob("*.md")))
    paths.extend(
        [
            RAW_ROOT / "taiwan_open_data" / "taiwan_organic_agriculture_information.csv",
            RAW_ROOT / "taiwan_open_data" / "taiwan_organic_agriculture_information.json",
            RAW_ROOT / "agrovoc" / "agrovoc_concept_sample.csv",
            RAW_ROOT / "crop_ontology" / "crop_ontology_metadata_summary.csv",
            RAW_ROOT / "google_earth_engine" / "earth_engine_agriculture_catalog_links.csv",
            RAW_ROOT / "source_manifest.json",
        ]
    )
    paths.extend(sorted((RAW_ROOT / "crop_ontology").glob("brapi_traits_CO_*.json")))
    paths.extend(sorted((RAW_ROOT / "crop_ontology").glob("brapi_variables_CO_*.json")))
    paths.extend(sorted((JURONG_SUPPORT_ROOT / "reports").glob("*.md")))
    paths.extend(sorted((JURONG_SUPPORT_ROOT / "historical_data").glob("*.md")))
    if os.environ.get("AGRIKB_INGEST_FULL_MONOGRAPHS") == "1":
        paths.extend(sorted((JURONG_SUPPORT_ROOT / "monographs").glob("*.pdf")))
    paths.extend(
        [
            JURONG_SUPPORT_ROOT / "jurong_support_manifest.json",
            JURONG_SUPPORT_ROOT / "jurong_support_manifest.csv",
        ]
    )
    return [str(path) for path in paths if path.exists() and path.stat().st_size > 0]


def main() -> None:
    config = load_config()
    service = KnowledgeBaseService(config)
    paths = collect_paths()
    summary = service.ingest_paths(paths)
    print({"paths": len(paths), **summary, "indexed_chunk_count": service._indexed_chunk_count})


if __name__ == "__main__":
    main()
