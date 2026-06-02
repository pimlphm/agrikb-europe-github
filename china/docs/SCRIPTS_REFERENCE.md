# Scripts Reference

This document explains the scripts in the portable project and the original data folder.

## Portable Runtime Scripts

| Script | Purpose | Typical Use |
| --- | --- | --- |
| `Setup-NewComputer.ps1` | Detects Python, prepares virtual environment, installs runtime dependencies, creates `.env` from template, checks Ollama/API mode | First run on a new Windows computer |
| `Start-Portable.ps1` | Runs setup if needed, starts FastAPI backend, opens Web UI | Daily startup |
| `Start-Background.ps1` | Starts backend in background mode | Run service without foreground console |
| `Test-Portable.ps1` | Executes portable smoke checks | Verify deployment |
| `Configure-ApiKey.ps1` | Helps configure OpenAI-compatible API key and model in `.env` | When no local Ollama or remote API is preferred |
| `启动迁移版.bat` | Windows double-click launcher for portable startup | Non-technical user startup |
| `启动前后端.bat` | Windows double-click launcher for backend/frontend startup | Alternate startup |
| `配置API密钥.bat` | Windows double-click launcher for API-key setup | Non-technical API configuration |

## Source-Code Support Scripts

| File | Purpose |
| --- | --- |
| `knowledge/graph/graph_builder.py` | Builds graph artifacts from knowledge data |
| `knowledge/ingestion/ingest_pipeline.py` | Main document ingestion pipeline |
| `knowledge/ingestion/segmenter.py` | Segments parsed documents into chunks |
| `knowledge/ingestion/extractor.py` | Extracts lightweight structured information |
| `core/doc_parser.py` | Parses supported file formats into text/document payloads |

## Original Data Scripts

These scripts are located in:

```text
../知识产权/
```

| Script | Purpose |
| --- | --- |
| `generate_docx.py` | Generates DOCX application documents from structured text |
| `create_editable_patent_figures.py` | Produces editable patent figure assets |
| `enhance_patent_hardware_figures.py` | Enhances patent figures with hardware details |
| `restructure_patent_implementation.py` | Restructures implementation sections of the patent application |
| `rewrite_implementation_four_detailed.py` | Rewrites and expands the fourth implementation section |
| `rewrite_implementation_six_embodiments.py` | Generates or rewrites multiple embodiment sections |
| `deepen_implementation_from_project.py` | Expands patent implementation details based on project architecture |

## Script Safety Rules

- Do not hardcode API keys in scripts.
- Do not overwrite final `.docx` deliverables without first making a backup.
- Keep generated patent outputs separate from runtime source code.
- Treat original patent scripts as private project assets unless publication is approved.

## Recommended GitHub Treatment

For a public GitHub repository, include runtime scripts and source-code support scripts. Keep patent-generation scripts private unless legal/IP review approves publication.
