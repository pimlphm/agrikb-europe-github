# Release Notes

## Prepared Package

This package contains two sanitized AgriKB GUI editions based on the TrustedPC local project:

- China GUI in `china/`
- Europe Toulouse GUI in `europe_toulouse/`

## Validation

- The private `.env` file was removed from both editions.
- `.env.example` remains in both editions for configuration.
- The Europe Toulouse backend passed Python syntax compilation before packaging.
- The Europe Toulouse GUI was opened locally at `http://127.0.0.1:8020/ui/`.
- The `/health` endpoint responded successfully during local verification.

## Known Notes

The package includes local runtime and environment files, so it is large. This is intentional for handoff convenience. For a public GitHub repository, consider using a source-only branch and publishing this full portable package as a release asset.

