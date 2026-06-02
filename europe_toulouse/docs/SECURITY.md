# Security and Data Policy

## Secrets

Never commit:

```text
.env
API keys
private tokens
local credentials
```

Use `.env.example` as the public template.

## Uploaded Documents

Uploaded source files may contain private or proprietary information. Treat these directories as private data:

```text
data/raw/
data/processed/
knowledge/chunks.db
knowledge/wiki/
knowledge/sessions/
knowledge/agent_memory/
```

Do not publish them unless the data owner explicitly approves.

## Provenance Integrity

AeroKB must not present unsupported model output as document evidence.

Rules:

- Use `document` only for local document chunks.
- Use `inferred` only for synthesis from supporting evidence.
- Use `model_prior` for model knowledge not grounded in documents.
- Use `unsupported` when evidence is insufficient.
- Use `web_search` only when a real web-search provider supplies source data.

## Local-First Assumption

Default behavior should prefer local processing and local storage. Remote APIs should be explicit and configured per machine.

## Safe Packaging

Before publishing or sharing a zip, inspect it for:

```text
.env
.venv
runtime/
backups/
raw uploaded files
logs
private documents
API keys
```

## GitHub Publishing Checklist

- Replace project-specific private names if needed.
- Remove private knowledge databases unless intentionally publishing a demo dataset.
- Keep `.env.example`, not `.env`.
- Confirm dependency licenses.
- Choose a license.
- Add a clear disclaimer that users are responsible for validating generated answers.
