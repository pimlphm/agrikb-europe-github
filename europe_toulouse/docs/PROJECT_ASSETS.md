# Project Assets

This document explains what should be understood as "the project" when publishing or maintaining AeroKB as a GitHub-style repository.

## Asset Categories

| Category | Location | Purpose | Publish By Default |
| --- | --- | --- | --- |
| Source code | `src/`, `core/`, `knowledge/ingestion/`, `knowledge/graph/`, `web/` | Backend, frontend, ingestion, retrieval and graph code | Yes |
| Runtime scripts | `*.ps1`, `*.bat` | Setup, start, test and API-key configuration | Yes |
| Configuration templates | `.env.example`, `config.yaml`, `requirements-runtime.txt` | Portable runtime configuration | Yes, without real secrets |
| Runtime index data | `knowledge/chunks.db`, `knowledge/wiki/`, `knowledge/agent_memory/` | Current processed knowledge index and generated summaries | Private or demo-only |
| Upload directories | `data/raw/`, `data/processed/` | User-uploaded source documents and processing artifacts | No, unless approved |
| Original IP materials | sibling folder `../知识产权/` | Patent, software copyright, diagrams and source generation scripts | Private by default |
| Documentation | `README_GITHUB.md`, `docs/`, `CHANGELOG.md`, `CONTRIBUTING.md` | GitHub-facing project explanation | Yes |

## Recommended GitHub Layout

```text
aerokb-local-knowledge-workbench/
  README.md
  README_GITHUB.md
  CHANGELOG.md
  CONTRIBUTING.md
  .gitignore
  .env.example
  config.yaml
  requirements-runtime.txt
  Start-Portable.ps1
  Setup-NewComputer.ps1
  Configure-ApiKey.ps1
  web/
  src/
  core/
  knowledge/
    ingestion/
    graph/
    agent_memory/
  docs/
```

For public GitHub, keep raw source documents and generated knowledge databases out of the repository unless they are explicitly cleared for publication.

## Private Asset Boundary

The following may contain private or proprietary information:

```text
../知识产权/
data/raw/
data/processed/
knowledge/chunks.db
knowledge/wiki/
knowledge/sessions/
knowledge/agent_memory/*.json
```

Use `docs/DATA_MANIFEST.md` to describe these assets instead of publishing them blindly.

## Repository Readiness

This project now contains:

- GitHub homepage summary: `README_GITHUB.md`
- Full documentation set: `docs/`
- Script reference: `docs/SCRIPTS_REFERENCE.md`
- Source-code reference: `docs/SOURCE_CODE_REFERENCE.md`
- Data manifest: `docs/DATA_MANIFEST.md`
- Git ignore rules: `.gitignore`
- Contribution guide: `CONTRIBUTING.md`
- Change log: `CHANGELOG.md`
