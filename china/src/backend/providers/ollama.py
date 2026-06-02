from __future__ import annotations

import json
from typing import Any, Iterable, List

import requests


class OllamaProvider:
    def __init__(self, config: dict) -> None:
        settings = config.get("ollama", {})
        retrieval = config.get("retrieval", {})
        self.base_url = settings.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = settings.get("model", "qwen2.5:7b-instruct")
        self.temperature = settings.get("temperature", 0.2)
        self.max_tokens = settings.get("max_tokens", 2048)
        self.num_ctx = settings.get("num_ctx", 4096)
        self.num_thread = settings.get("num_thread")
        self.top_p = settings.get("top_p", 0.85)
        self.keep_alive = settings.get("keep_alive", "10m")
        self.embedding_model = settings.get("embedding_model", self.model)
        self.embedding_dim = retrieval.get("dense_embedding_dim", 128)

    def check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=8)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        models = []
        for item in data.get("models", []):
            name = item.get("name") or item.get("model")
            if not name:
                continue
            details = item.get("details") or {}
            models.append(
                {
                    "name": name,
                    "label": name,
                    "size": item.get("size"),
                    "modified_at": item.get("modified_at"),
                    "family": details.get("family") or details.get("families"),
                    "parameter_size": details.get("parameter_size"),
                    "quantization": details.get("quantization_level"),
                }
            )
        return sorted(models, key=lambda model: model["name"].lower())

    def set_model(self, model: str) -> None:
        model = str(model or "").strip()
        if not model:
            raise ValueError("Ollama model name is required.")
        self.model = model

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": self.num_ctx,
                "top_p": self.top_p,
            },
            "keep_alive": self.keep_alive,
        }
        if self.num_thread:
            payload["options"]["num_thread"] = self.num_thread
        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    def structured_output(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        schema_prompt = (
            "Return JSON only. The response must satisfy this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"{prompt}"
        )
        text = self.generate(schema_prompt, system=system)
        return self._extract_json(text)

    def embed_texts(self, texts: Iterable[str], model: str | None = None) -> List[List[float]]:
        texts = list(texts)
        if not texts:
            return []

        chosen_model = model or self.embedding_model
        payload = {"model": chosen_model, "input": texts}

        try:
            response = requests.post(f"{self.base_url}/api/embed", json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            if isinstance(data.get("embeddings"), list):
                return data["embeddings"]
        except Exception:
            pass

        embeddings: List[List[float]] = []
        for text in texts:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": chosen_model, "prompt": text},
                timeout=120,
            )
            response.raise_for_status()
            embeddings.append(response.json().get("embedding", []))
        return embeddings

    def _extract_json(self, text: str) -> dict:
        candidates = [text]
        if "```json" in text:
            candidates.append(text.split("```json", 1)[1].split("```", 1)[0])
        if "```" in text:
            candidates.append(text.split("```", 1)[1].split("```", 1)[0])
        for candidate in candidates:
            candidate = candidate.strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise ValueError("Failed to parse structured JSON response from Ollama")
