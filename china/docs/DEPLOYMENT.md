# Deployment Guide

## Portable Windows Deployment

The project is designed to run as a portable Windows folder.

Recommended first run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-NewComputer.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Portable.ps1
```

Double-click launchers are also included:

```text
启动迁移版.bat
配置API密钥.bat
```

## First-Run Checklist

1. Extract the project folder.
2. Run setup.
3. Configure `.env` if remote API fallback is needed.
4. Start the backend.
5. Open `http://127.0.0.1:8010/ui/`.
6. Check `http://127.0.0.1:8010/health`.
7. Upload or import documents.
8. Ask a test question.

## API Key Setup

Use `.env.example` as the template. Never commit real keys.

```text
KNOWLEDGE_RAG_BACKEND=auto
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
KNOWLEDGE_RAG_BASE_URL=https://api.moonshot.cn/v1
KNOWLEDGE_RAG_MODEL=moonshot-v1-8k
KNOWLEDGE_RAG_API_KEY=your-key
```

## Ollama Setup

If Ollama is installed on the target computer:

1. Start Ollama.
2. Pull at least one chat model.
3. Open the UI.
4. Refresh the local model selector.
5. Choose a model and click "用于回答".

If Ollama is not installed, configure the OpenAI-compatible API fallback.

## What Not To Ship

Do not include:

```text
.env
.venv
runtime/
backups/
__pycache__/
private uploaded source documents
real API keys
local logs
```

## Recommended GitHub Release Artifact

For a GitHub release, publish a clean zip that includes:

```text
web/
src/
core/doc_parser.py
knowledge/ingestion/
knowledge/graph/
knowledge/agent_memory/
.env.example
requirements-runtime.txt
Start-Portable.ps1
Setup-NewComputer.ps1
Configure-ApiKey.ps1
README_GITHUB.md
docs/
```
