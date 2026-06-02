# Troubleshooting

## Service Does Not Start

Check whether port `8010` is already in use:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8010
```

If another process is using it, stop that process or change `KNOWLEDGE_RAG_PORT` in `.env`.

## Python Is Not Found

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-NewComputer.ps1
```

The setup script should create or reuse the local virtual environment.

## UI Opens But Backend Is Offline

Check:

```text
http://127.0.0.1:8010/health
```

If unavailable, restart with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Portable.ps1
```

## Ollama Models Do Not Appear

Check:

```text
http://localhost:11434/api/tags
```

If that URL is unavailable:

1. Start Ollama.
2. Pull a model.
3. Refresh the model selector in the UI.

## Remote API Does Not Work

Check `.env`:

```text
KNOWLEDGE_RAG_BACKEND=openai_compatible
KNOWLEDGE_RAG_BASE_URL=...
KNOWLEDGE_RAG_API_KEY=...
KNOWLEDGE_RAG_MODEL=...
```

Do not add extra spaces around the key. Do not commit the file.

## Upload Is Slow

For hundreds of documents:

- Use background upload.
- Keep `write_chunk_json_files: false`.
- Keep `db_batch_size` reasonably high.
- Avoid enabling remote embeddings unless necessary.
- Wait for coarse tree readiness before asking detailed questions.

## Answers Lack Evidence

Possible causes:

- Documents are still ingesting.
- Query is outside the uploaded document scope.
- Chunk index is empty.
- Evidence did not match the claim strongly enough.

Check the knowledge tree and `indexed_chunk_count` in `/health`.

## Garbled Chinese In Some Legacy Markdown

Some older reports may have been written or viewed with the wrong encoding. New GitHub documentation files are UTF-8 Markdown. Prefer the `docs/` set and `README_GITHUB.md` for publishing.
