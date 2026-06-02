# Developer Guide

## Local Development

Install runtime dependencies into a virtual environment, then start:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.backend.app:app --host 127.0.0.1 --port 8010
```

Open:

```text
http://127.0.0.1:8010/ui/
```

## Code Style

- Keep the frontend static and build-free unless there is a strong reason to add a build system.
- Keep UI language product-facing and avoid exposing implementation details.
- Keep provenance explicit.
- Prefer small, focused backend service methods over large endpoint functions.
- Do not introduce heavy dependencies for basic graph rendering.

## Important Files

```text
src/backend/app.py               FastAPI route layer
src/backend/service.py           Orchestration layer
src/backend/providers/ollama.py  Local model provider
src/generation/generator.py      Evidence-grounded answer generator
src/retrieval/                   Retrieval implementations
web/app.js                       Frontend interaction logic
web/style.css                    UI styling
```

## Testing

Syntax checks:

```powershell
.\.venv\Scripts\python.exe -m compileall src\backend src\generation
node --check web\app.js
```

Backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Smoke checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
Invoke-RestMethod http://127.0.0.1:8010/api/models
```

## Adding a Provider

Provider classes should implement:

```python
check_connection()
generate(prompt, system=None, model=None)
embed_texts(texts, model=None)
```

Optional:

```python
list_models()
set_model(model)
structured_output(prompt, schema, system=None)
```

## Adding an API Endpoint

1. Add request model in `src/backend/app.py`.
2. Implement logic in `src/backend/service.py`.
3. Keep endpoint response backward-compatible where possible.
4. Update `docs/API_REFERENCE.md`.
5. Add or update tests.

## Frontend Guidelines

- Use existing DOM patterns in `web/index.html`.
- Keep state in `web/app.js`.
- Keep CSS in `web/style.css`.
- Prefer progressive enhancement.
- Avoid showing chunk IDs, scores or backend internals in primary UI unless debug mode is enabled.
