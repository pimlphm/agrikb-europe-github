from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Iterable, List

import requests


class OpenAICompatibleProvider:
    def __init__(self, config: dict) -> None:
        settings = config.get("openai_compatible", {})
        retrieval = config.get("retrieval", {})
        self.base_url = settings.get("base_url", "https://api.openai.com/v1").rstrip("/")
        self.api_key = settings.get("api_key", "")
        self.model = settings.get("model", "")
        self.embedding_model = settings.get("embedding_model", "")
        self.temperature = settings.get("temperature", 0.2)
        self.max_tokens = settings.get("max_tokens", 2048)
        self.embedding_dim = retrieval.get("dense_embedding_dim", 128)

    def check_connection(self) -> bool:
        if not self.api_key or not self.model:
            return False
        try:
            response = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=8)
            if 200 <= response.status_code < 400:
                return True
            if response.status_code in {401, 403}:
                return False
            return self._check_chat_completion()
        except Exception:
            return self._check_chat_completion()

    def list_models(self) -> list[str]:
        if not self.api_key:
            return []
        try:
            response = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=8)
            response.raise_for_status()
            data = response.json()
            return [item.get("id", "") for item in data.get("data", []) if item.get("id")]
        except Exception:
            return []

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        if not self.api_key:
            raise RuntimeError("Missing KNOWLEDGE_RAG_API_KEY or OPENAI_API_KEY.")
        chosen_model = model or self.model
        if not chosen_model:
            raise RuntimeError("Missing KNOWLEDGE_RAG_MODEL or openai_compatible.model.")
        if self._looks_like_kimi_coding_plan(chosen_model):
            raise RuntimeError("检测到 Kimi Coding Plan API Key，已阻止普通 chat/completions 直连；请使用随包内置的新农人助手 Coding / Kimi CLI 通道。")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": chosen_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        if not 200 <= response.status_code < 400:
            raise RuntimeError(self._format_api_error(response))
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

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
        if not self.api_key or not chosen_model:
            return [self._fallback_embed(text) for text in texts]

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={"model": chosen_model, "input": texts},
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = [item.get("embedding", []) for item in data.get("data", [])]
            if len(embeddings) != len(texts):
                return [self._fallback_embed(text) for text in texts]
            return embeddings
        except Exception:
            return [self._fallback_embed(text) for text in texts]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _fallback_embed(self, text: str) -> list[float]:
        vector = [0.0] * self.embedding_dim
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            vector[int(digest[:8], 16) % self.embedding_dim] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _check_chat_completion(self) -> bool:
        if not self.api_key or not self.model:
            return False
        if self._looks_like_kimi_coding_plan(self.model):
            return False
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "temperature": 0,
                    "max_tokens": 4,
                },
                timeout=20,
            )
            return 200 <= response.status_code < 400
        except Exception:
            return False

    def _looks_like_kimi_coding_plan(self, model: str | None = None) -> bool:
        chosen_model = str(model or self.model or "")
        return self.api_key.startswith("sk-kimi-") or chosen_model == "kimi-for-coding" or "api.kimi.com/coding" in self.base_url

    def _format_api_error(self, response: requests.Response) -> str:
        status = response.status_code
        if status in {401, 403}:
            body = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", response.text or "")[:420]
            if "Kimi For Coding" in body or "Coding Agents" in body:
                return "Kimi Coding Plan API 不支持普通直连 chat/completions，请使用随包的 Kimi CLI 通道。"
            return "新农人助手 API 鉴权失败：请检查 API Key、账户额度和模型权限。"
        body = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", response.text or "")[:420]
        return f"新农人助手 API 调用失败：HTTP {status} {response.reason}. {body}".strip()

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
        raise ValueError("Failed to parse structured JSON response from OpenAI-compatible backend")
