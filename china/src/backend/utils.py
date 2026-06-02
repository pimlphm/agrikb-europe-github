from __future__ import annotations

import os
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict:
    load_env_file()
    config_path = path or (ROOT / "config.yaml")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    apply_env_overrides(config)
    return config


def load_env_file(path: Path | None = None) -> None:
    env_path = path or (ROOT / ".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def apply_env_overrides(config: dict) -> None:
    mappings = {
        "KNOWLEDGE_RAG_BACKEND": ("backend",),
        "KNOWLEDGE_RAG_HOST": ("api", "host"),
        "KNOWLEDGE_RAG_PORT": ("api", "port"),
        "OLLAMA_BASE_URL": ("ollama", "base_url"),
        "OLLAMA_MODEL": ("ollama", "model"),
        "KNOWLEDGE_RAG_BASE_URL": ("openai_compatible", "base_url"),
        "KIMI_BASE_URL": ("openai_compatible", "base_url"),
        "MOONSHOT_BASE_URL": ("openai_compatible", "base_url"),
        "KNOWLEDGE_RAG_API_KEY": ("openai_compatible", "api_key"),
        "OPENAI_API_KEY": ("openai_compatible", "api_key"),
        "KIMI_API_KEY": ("openai_compatible", "api_key"),
        "MOONSHOT_API_KEY": ("openai_compatible", "api_key"),
        "KNOWLEDGE_RAG_MODEL": ("openai_compatible", "model"),
        "OPENAI_MODEL": ("openai_compatible", "model"),
        "KIMI_MODEL": ("openai_compatible", "model"),
        "MOONSHOT_MODEL": ("openai_compatible", "model"),
        "AGRIKB_FRONTEND_BASE_URL": ("frontend_api", "base_url"),
        "AGRIKB_FRONTEND_MODEL": ("frontend_api", "model"),
        "AGRIKB_FRONTEND_KIMI_API_KEY": ("frontend_api", "api_key"),
        "KNOWLEDGE_RAG_EMBEDDING_MODEL": ("openai_compatible", "embedding_model"),
        "OPENAI_EMBEDDING_MODEL": ("openai_compatible", "embedding_model"),
        "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS": ("retrieval", "remote_embeddings"),
    }
    for env_name, path_parts in mappings.items():
        value = os.environ.get(env_name)
        if value is None or value == "":
            continue
        target = config
        for part in path_parts[:-1]:
            target = target.setdefault(part, {})
        if path_parts[-1] == "port":
            try:
                target[path_parts[-1]] = int(value)
            except ValueError:
                continue
        elif path_parts[-1] == "remote_embeddings":
            target[path_parts[-1]] = value.strip().lower() in {"1", "true", "yes", "on"}
        else:
            target[path_parts[-1]] = value
    effective_key = os.environ.get("KIMI_API_KEY") or os.environ.get("KNOWLEDGE_RAG_API_KEY") or os.environ.get("MOONSHOT_API_KEY") or ""
    if effective_key.startswith("sk-kimi-"):
        config["backend"] = "kimi_cli"
        for section in ("openai_compatible", "kimi_cli"):
            target = config.setdefault(section, {})
            target["base_url"] = "https://api.kimi.com/coding/v1"
            target["model"] = "kimi-for-coding"
            target["api_key"] = effective_key


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def ensure_dir(path: str | Path) -> Path:
    resolved = resolve_repo_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def list_demo_documents() -> list[str]:
    docs = []
    for pattern in ("docs/demo_airbus/*.md", "docs/demo_boeing/*.md"):
        docs.extend(str(path) for path in sorted(ROOT.glob(pattern)))
    return docs
