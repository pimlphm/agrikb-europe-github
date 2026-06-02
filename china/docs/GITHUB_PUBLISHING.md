# GitHub Publishing Guide

This folder is prepared as a GitHub-style project. Because it includes original IP materials under `original_data/知识产权/`, publish it as a private repository unless those materials are approved for public release.

## Private Repository Option

Use this when collaborators are allowed to see the patent, copyright and figure materials.

```powershell
git init
git add .
git commit -m "Initial full-assets AeroKB project"
git branch -M main
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

## Public Repository Option

Before public release, remove or replace private materials:

```text
original_data/知识产权/
knowledge/chunks.db
knowledge/wiki/
knowledge/agent_memory/*.json
knowledge/sessions/
data/raw/
data/processed/
```

Then publish only source code, scripts, safe docs and redacted demo data.

## Recommended Repository Name

```text
aerokb-local-knowledge-workbench
```

## Recommended GitHub Topics

```text
rag
knowledge-graph
fastapi
ollama
openai-compatible
document-ai
evidence-chain
provenance
local-first
knowledge-base
```

## Pre-Push Checklist

- Confirm `.env` is absent.
- Confirm no real API key appears in text files.
- Decide whether `original_data/知识产权/` is private-only.
- Decide whether `knowledge/chunks.db` should be tracked or regenerated.
- Run basic checks if the target computer has Python and Node.
