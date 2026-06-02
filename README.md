# AgriKB Dual GUI Project

AgriKB is a local smart agriculture decision-support project prepared as two GUI editions:

- `china/`: the original Chinese edition, kept for China-focused demonstrations and local agricultural service scenarios.
- `europe_toulouse/`: an English European edition focused on Toulouse, Occitanie, France.

The project is intended as an early-stage product and technical introduction for smart agriculture. It presents regional context, market signals, knowledge retrieval, and advisory Q&A without monetization claims or exaggerated commercial language.

## Purpose

AgriKB helps agricultural service teams, local government staff, cooperatives, and project evaluators explore how a trusted local PC can support agriculture workflows:

- Regional crop and production context.
- Market and wholesale price checking.
- Knowledge-base backed agricultural Q&A.
- Graph-style knowledge navigation.
- Local-first operation with portable runtime assets.
- Separate GUI narratives for China and Europe.

## Quick Start

Use Windows PowerShell or double-click the launcher files.

### China GUI

```bat
START_CHINA_GUI.bat
```

Default local address:

```text
http://127.0.0.1:8010/ui/
```

### Europe Toulouse GUI

```bat
START_EUROPE_TOULOUSE_GUI.bat
```

Default local address:

```text
http://127.0.0.1:8020/ui/
```

The Toulouse edition uses Toulouse, Occitanie, France as the demonstration production area and the Toulouse MIN Occitanie wholesale market as the market reference point.

## Configuration

The private `.env` file from the original local package is intentionally not included.

Before using model or live-data functions on a new computer, copy the provided `.env.example` in the relevant edition folder and configure local credentials:

```text
china/.env.example
europe_toulouse/.env.example
```

You can also use the included configuration scripts in each edition folder, such as `CONFIG_API_KEY.bat` or `Configure-ApiKey.ps1`.

## Main Architecture

```text
User
  |
  v
Web GUI
  |-- china/web/
  |-- europe_toulouse/web/
  |
  v
FastAPI backend
  |-- src/backend/app.py
  |-- /health
  |-- /ui/
  |-- /api/query
  |-- /api/regional/live
  |-- /api/market/prices
  |-- /api/knowledge/tree
  |
  v
Knowledge and data layer
  |-- knowledge/
  |-- data/
  |-- original_data/
  |
  v
Local runtime and model tools
  |-- runtime/
  |-- .venv/
  |-- models/
```

## Folder Guide

- `web/`: front-end GUI files.
- `src/backend/`: FastAPI application and API routes.
- `knowledge/`: local knowledge assets used by retrieval and graph features.
- `data/` and `original_data/`: agricultural reference data and source material.
- `runtime/`: bundled local runtime tools.
- `.venv/`: bundled Python environment for one-click local execution.
- `models/`: local speech or model support assets.
- `docs/` and `deliverables/`: supporting project documents and generated materials.

## GitHub Notes

This repository is intentionally large because it keeps the portable local runtime for easier handoff. No single file should exceed GitHub's 100 MB file limit, but the repository may still be heavy. If GitHub reports repository-size warnings, publish the full portable package as a Release asset and keep a slimmer source-only branch for code review.

Never commit `.env`, API keys, tokens, cookies, or private machine-specific credentials.

