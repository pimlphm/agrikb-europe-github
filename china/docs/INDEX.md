# AgriKB Project Documentation

This directory contains the delivery documentation set for AgriKB.

## Reading Order

1. [Project Overview](../README_GITHUB.md)
2. [Project Assets](PROJECT_ASSETS.md)
3. [Data Manifest](DATA_MANIFEST.md)
4. [Competition First Prize Plan](COMPETITION_FIRST_PRIZE_PLAN.md)
5. [Dual-Track Positioning](DUAL_TRACK_POSITIONING.md)
6. [Scripts Reference](SCRIPTS_REFERENCE.md)
7. [Source Code Reference](SOURCE_CODE_REFERENCE.md)
8. [Nuwa-Inspired Experience Memory](NUWA_EXPERIENCE_MEMORY.md)
9. [File Manifest](FILE_MANIFEST.md)
10. [GitHub Publishing Guide](GITHUB_PUBLISHING.md)
11. [User Guide](USER_GUIDE.md)
12. [Architecture](ARCHITECTURE.md)
13. [API Reference](API_REFERENCE.md)
14. [Deployment Guide](DEPLOYMENT.md)
15. [Configuration Guide](CONFIGURATION.md)
16. [Developer Guide](DEVELOPER_GUIDE.md)
17. [Operations Guide](OPERATIONS.md)
18. [Troubleshooting](TROUBLESHOOTING.md)
19. [Security and Data Policy](SECURITY.md)

## Documentation Map

| Document | Audience | Purpose |
| --- | --- | --- |
| `README_GITHUB.md` | Everyone | GitHub homepage and project pitch |
| `PROJECT_ASSETS.md` | Maintainers | Defines source code, scripts, runtime data and original IP materials |
| `DATA_MANIFEST.md` | Maintainers, reviewers | Documents raw data, generated data, knowledge indexes and original patent materials |
| `COMPETITION_FIRST_PRIZE_PLAN.md` | Founders, product, reviewers | Aligns product development to the 2026 Jurong "福地青年英才" new-farmer competition and first-prize strategy |
| `DUAL_TRACK_POSITIONING.md` | Founders, product, reviewers | Defines the 数智信息技术 × 新农人 fusion positioning for competition narrative and demo design |
| `SCRIPTS_REFERENCE.md` | Developers, operators | Explains setup, startup, test and patent-generation scripts |
| `SOURCE_CODE_REFERENCE.md` | Developers | Maps source-code modules and responsibilities |
| `NUWA_EXPERIENCE_MEMORY.md` | Developers, reviewers | Explains the Nuwa-inspired experience memory schema and evidence boundary rules |
| `FILE_MANIFEST.md` / `FILE_MANIFEST.csv` | Maintainers | Complete file-level inventory of the full-assets project |
| `GITHUB_PUBLISHING.md` | Maintainers | Private/public GitHub publishing instructions |
| `USER_GUIDE.md` | End users | Upload documents, ask questions, inspect evidence |
| `ARCHITECTURE.md` | Engineers | Backend, frontend, ingestion, retrieval and graph design |
| `API_REFERENCE.md` | Integrators | REST endpoints and response concepts |
| `DEPLOYMENT.md` | Operators | New-computer setup and portable deployment |
| `CONFIGURATION.md` | Operators | `.env`, Ollama, OpenAI-compatible API and runtime settings |
| `DEVELOPER_GUIDE.md` | Developers | Local development, testing and code organization |
| `OPERATIONS.md` | Maintainers | Maintenance, reset, package hygiene and routine checks |
| `TROUBLESHOOTING.md` | Support | Common failures and fixes |
| `SECURITY.md` | Everyone | API-key, provenance and local-data rules |

## Documentation Principles

- Do not commit real `.env` files or API keys.
- Do not publish uploaded private documents unless explicitly cleared.
- Do not claim model-generated content is document evidence.
- Keep the project portable and runnable without a frontend build step.
- Keep GUI language user-facing; avoid exposing implementation internals in the product UI.
