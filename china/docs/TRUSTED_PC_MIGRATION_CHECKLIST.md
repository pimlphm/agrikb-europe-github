# AgriKB Trusted-PC Migration Checklist

Updated: 2026-05-25

## Current Result

- The private `.env` is present and contains the trusted Kimi Coding Plan key aliases required by the backend and frontend settings panel.
- `sk-kimi-*` keys force `backend=kimi_cli`, `base_url=https://api.kimi.com/coding/v1`, and `model=kimi-for-coding`.
- `KNOWLEDGE_RAG_REMOTE_EMBEDDINGS=false`, so the project does not need a separate remote embedding model on a blank PC.
- `runtime/python311/python.exe`, `.venv/Lib/site-packages`, `runtime/kimi/kimi.exe`, and `runtime/kimi/opencode/bin/rg.exe` are bundled.
- The full Kimi CLI module runtime is bundled under `runtime/kimi/python313` and `runtime/kimi/kimi-cli-tool`.
- The backend prefers the package-local `python -m kimi_cli` runner, so it does not depend on uv trampoline shims with old absolute paths.
- The startup scripts now restart stale AgriKB uvicorn processes that are still using the old OpenAI-compatible provider.

## New Blank Windows PC Steps

1. Extract the zip to a normal folder.
2. Run `CHECK_NEW_PC_ENV.bat`.
3. Confirm the report says `Provider: KimiCliProvider`, `Real model: True`, and both settings API tests are true.
4. Run `START_AgriKB_TRUSTED_PC.bat`.

## No Extra Install Required

- Python install: not required.
- pip install: not required for normal startup.
- Kimi CLI install: not required.
- uv install: not required for the full package. It is only used by the one-click repair script if an older broken package needs to download a missing Kimi CLI runtime.
- Ollama install: optional only; not required for the Kimi Coding Plan path.
- Separate embedding model: not required.

## Remaining External Requirements

- Internet access to the Kimi Coding endpoint.
- The Kimi account must keep quota and Coding Plan model permission active.
- The zip must stay on trusted storage because it contains `.env`.
