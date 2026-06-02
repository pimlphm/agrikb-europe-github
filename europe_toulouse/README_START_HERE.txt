AgriKB Trusted-PC One-Click Package
===================================

This package is prepared for a trusted Windows computer. It contains a private
.env file with the local Kimi Coding Plan key, so do not upload it to public
GitHub, cloud drives shared with others, screenshots, or untrusted machines.

First Run On A New Blank Windows PC
-----------------------------------

1. Extract the whole zip folder first. Do not run files directly inside the zip.
2. Double-click CHECK_NEW_PC_ENV.bat to run the full environment and real model check.
3. Double-click START_AgriKB_TRUSTED_PC.bat to start AgriKB.
4. Open http://127.0.0.1:8010/ui/ if the browser does not open automatically.

What Is Already Bundled
-----------------------

- Portable Python: runtime/python311/python.exe
- Python dependencies: .venv/Lib/site-packages
- Kimi CLI bridge: runtime/kimi/kimi.exe
- Full portable Kimi CLI runtime: runtime/kimi/python313 and runtime/kimi/kimi-cli-tool
- ripgrep used by Kimi CLI: runtime/kimi/opencode/bin/rg.exe
- Private local API configuration: .env
- Knowledge base, data, models, web UI, scripts, docs, and deliverables

API Key Notes
-------------

- sk-kimi-* Coding Plan keys are configured to use the bundled Kimi CLI channel.
- Backend and frontend backup keys are both stored in .env for trusted-PC portability.
- Remote embeddings stay disabled by default; the package uses the built-in local fallback embedding path.
- To replace the key later, double-click CONFIG_API_KEY.bat or run:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Configure-ApiKey.ps1

Startup Protection
------------------

If port 8010 already has an old AgriKB service that was started before the key fix,
START_AgriKB_TRUSTED_PC.bat now restarts that old AgriKB uvicorn process and starts
the packaged runtime again. This prevents the app from accidentally using the old
OpenAI-compatible direct channel, which causes Kimi Coding Plan authentication errors.

Kimi CLI Trampoline Fix
-----------------------

Older packages copied only the small uv-generated kimi.exe shim. On a new PC it can
fail with "uv trampoline failed to canonicalize script path" because that shim points
back to the old computer's uv tool path. This package now includes the full Kimi CLI
Python 3.13 runtime and the backend calls `python -m kimi_cli` from inside the package.
If an older extracted copy is already on another PC, copy this package's
FIX_KIMI_TRAMPOLINE_ONECLICK.bat and Patch-Fix-KimiTrampoline.ps1 into that AgriKB
folder and double-click the BAT to repair it.

Useful Entry Points
-------------------

- START_AgriKB_TRUSTED_PC.bat: start the app.
- CHECK_NEW_PC_ENV.bat: check Python, Kimi CLI, keys, UI, and real model call.
- CONFIG_API_KEY.bat: replace the private API key.
- MOBILE_WIFI_TEST.bat: test phone access on the same network.
- FIX_MOBILE_WIFI_ACCESS.bat: add a Windows firewall rule for phone access.
- UNINSTALL_AgriKB.bat: remove this local package cleanly.
- FIX_KIMI_TRAMPOLINE_ONECLICK.bat: repair older extracted copies that still fail on uv trampoline paths.
