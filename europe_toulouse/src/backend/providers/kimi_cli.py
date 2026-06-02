from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[3]
_RESPONSE_CACHE: "OrderedDict[str, str]" = OrderedDict()
_CACHE_LIMIT = 64


class KimiCliProvider:
    def __init__(self, config: dict) -> None:
        settings = config.get("kimi_cli", {})
        api_settings = config.get("openai_compatible", {})
        retrieval = config.get("retrieval", {})
        self.executable = self._resolve_executable(settings.get("executable", "kimi"))
        self.base_url = settings.get("base_url") or api_settings.get("base_url") or "https://api.kimi.com/coding/v1"
        self.api_key = (
            settings.get("api_key")
            or api_settings.get("api_key")
            or os.environ.get("KIMI_API_KEY", "")
            or os.environ.get("KNOWLEDGE_RAG_API_KEY", "")
        )
        self.model = settings.get("model") or api_settings.get("model") or "kimi-for-coding"
        if str(self.api_key or "").startswith("sk-kimi-") or self.model == "kimi-for-coding":
            self.base_url = "https://api.kimi.com/coding/v1"
            self.model = "kimi-for-coding"
        self.timeout = int(os.environ.get("AGRIKB_KIMI_TIMEOUT") or settings.get("timeout", 420))
        self.max_retries = int(os.environ.get("AGRIKB_KIMI_MAX_RETRIES") or settings.get("max_retries", 2))
        self.work_dir = str(Path(settings.get("work_dir") or ROOT).resolve())
        self.embedding_dim = retrieval.get("dense_embedding_dim", 128)
        self.module_python = (ROOT / "runtime" / "kimi" / "python313" / "python.exe").resolve()
        self.module_site_packages = (ROOT / "runtime" / "kimi" / "kimi-cli-tool" / "Lib" / "site-packages").resolve()
        self.module_scripts = (ROOT / "runtime" / "kimi" / "kimi-cli-tool" / "Scripts").resolve()

    def check_connection(self) -> bool:
        if self._module_runner_available():
            return True
        if Path(self.executable).exists():
            return True
        return bool(shutil.which(self.executable))

    def list_models(self) -> list[str]:
        return [self.model] if self.check_connection() else []

    def generate(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        if not self.check_connection():
            raise RuntimeError("新农人助手模型命令不可用：未找到随包 runtime/kimi/kimi.exe，也未在 PATH 中找到 kimi。")
        if not self.api_key:
            raise RuntimeError("新农人助手 API Key 为空：请检查 .env 中的 KNOWLEDGE_RAG_API_KEY 或 KIMI_API_KEY。")
        chosen_model = model or self.model
        safe_system = (
            "You are the answer model for the AgriKB agricultural knowledge base. "
            "Do not call tools, read or modify local files, or execute commands. "
            "Answer only from the user question and the evidence included in the prompt. "
            "When the prompt asks for JSON, return machine-readable JSON without extra explanation. "
            "For ordinary Chinese answers, use clear Chinese reading structure: conclusion first, then reasons, then actions; "
            "use short headings, short paragraphs, and numbered action lists, never one long block of text."
        )
        if system:
            safe_system = f"{safe_system}\n{system}"
        full_prompt = f"{safe_system}\n\n{prompt}"
        cache_key = self._cache_key(full_prompt, chosen_model)
        if self._cache_enabled() and cache_key in _RESPONSE_CACHE:
            _RESPONSE_CACHE.move_to_end(cache_key)
            return _RESPONSE_CACHE[cache_key]
        prompt_variants = [full_prompt]
        compact_prompt = self._compact_prompt_for_retry(full_prompt)
        if compact_prompt != full_prompt:
            prompt_variants.append(compact_prompt)
        last_error = ""
        for index, candidate_prompt in enumerate(prompt_variants, start=1):
            try:
                answer = self._run_kimi(candidate_prompt, chosen_model)
                if self._cache_enabled() and answer:
                    _RESPONSE_CACHE[cache_key] = answer
                    _RESPONSE_CACHE.move_to_end(cache_key)
                    while len(_RESPONSE_CACHE) > _CACHE_LIMIT:
                        _RESPONSE_CACHE.popitem(last=False)
                return answer
            except RuntimeError as exc:
                last_error = str(exc)
                if index >= len(prompt_variants) or not self._is_timeout_like(last_error):
                    raise
                time.sleep(1.2)
        raise RuntimeError(last_error or "新农人助手模型请求失败。")

    def _run_kimi(self, full_prompt: str, chosen_model: str) -> str:
        env = os.environ.copy()
        env.update(
            {
                "KIMI_BASE_URL": self.base_url,
                "KIMI_MODEL_NAME": chosen_model,
                "KIMI_CLI_NO_AUTO_UPDATE": "1",
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        if self.api_key:
            env["KIMI_API_KEY"] = self.api_key
            env["KNOWLEDGE_RAG_API_KEY"] = self.api_key
        kimi_bin = str(Path(self.executable).resolve().parent) if Path(self.executable).exists() else ""
        bundled_rg = str((ROOT / "runtime" / "kimi" / "opencode" / "bin").resolve())
        python_bin = str(self.module_python.parent) if self.module_python.exists() else ""
        module_scripts = str(self.module_scripts) if self.module_scripts.exists() else ""
        pywin32_system32 = str(self.module_site_packages / "pywin32_system32")
        env["PATH"] = os.pathsep.join(
            item for item in (python_bin, pywin32_system32, module_scripts, kimi_bin, bundled_rg, env.get("PATH", "")) if item
        )
        if self._module_runner_available():
            env["PYTHONPATH"] = os.pathsep.join(
                item
                for item in (
                    str(self.module_site_packages),
                    str(self.module_site_packages / "win32"),
                    str(self.module_site_packages / "win32" / "lib"),
                    str(self.module_site_packages / "pythonwin"),
                    env.get("PYTHONPATH", ""),
                )
                if item
            )
            command = [
                str(self.module_python),
                "-m",
                "kimi_cli",
            ]
        else:
            command = [
                self.executable,
            ]
        command += [
            "--print",
            "--final-message-only",
            "--output-format",
            "text",
            "--input-format",
            "text",
            "--work-dir",
            self.work_dir,
            "--max-steps-per-turn",
            "1",
            "--max-retries-per-step",
            str(max(1, self.max_retries)),
            "--no-thinking",
            "--model",
            chosen_model,
        ]
        try:
            result = subprocess.run(
                command,
                cwd=self.work_dir,
                env=env,
                input=full_prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"新农人助手模型请求超时（已等待 {self.timeout} 秒）。") from exc
        if result.returncode != 0:
            detail = self._sanitize_error((result.stderr or result.stdout or "").strip())
            if self._is_timeout_like(detail):
                raise RuntimeError(detail or f"新农人助手模型请求超时（已等待 {self.timeout} 秒）。")
            raise RuntimeError(detail or "新农人助手模型请求失败。")
        return self._clean_stdout(result.stdout)

    def _module_runner_available(self) -> bool:
        return self.module_python.exists() and (self.module_site_packages / "kimi_cli").exists()

    def _resolve_executable(self, value: str) -> str:
        candidate = Path(str(value or "kimi"))
        if candidate.is_absolute():
            return str(candidate)
        if len(candidate.parts) > 1:
            bundled = (ROOT / candidate).resolve()
            if bundled.exists():
                return str(bundled)
        default_bundled = (ROOT / "runtime" / "kimi" / "kimi.exe").resolve()
        if default_bundled.exists():
            return str(default_bundled)
        return str(candidate)

    def _compact_prompt_for_retry(self, text: str, limit: int = 9000) -> str:
        value = str(text or "")
        if len(value) <= limit:
            return value
        head = value[:2200]
        tail = value[-(limit - len(head) - 280) :]
        return (
            f"{head}\n\n"
            "【系统精简重试说明】上一次模型请求超时，已压缩中间证据。"
            "请优先回答用户问题，保留结论、理由和下一步，不要解释压缩过程。\n\n"
            f"{tail}"
        )

    def _is_timeout_like(self, text: str) -> bool:
        value = str(text or "").lower()
        return any(marker in value for marker in ("timeout", "timed out", "超时", "请求超时", "压缩重试失败"))

    def _cache_enabled(self) -> bool:
        return str(os.environ.get("AGRIKB_KIMI_CACHE", "true")).lower() in {"1", "true", "yes", "on"}

    def _cache_key(self, full_prompt: str, model: str) -> str:
        material = f"{self.base_url}\0{model}\0{full_prompt}"
        return hashlib.sha256(material.encode("utf-8", errors="ignore")).hexdigest()

    def structured_output(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        schema_prompt = (
            "Return JSON only. The response must satisfy this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"{prompt}"
        )
        text = self.generate(schema_prompt, system=system)
        return self._extract_json(text)

    def embed_texts(self, texts: Iterable[str], model: str | None = None) -> List[List[float]]:
        return [self._fallback_embed(text) for text in texts]

    def _fallback_embed(self, text: str) -> list[float]:
        vector = [0.0] * self.embedding_dim
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            vector[int(digest[:8], 16) % self.embedding_dim] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _clean_stdout(self, text: str) -> str:
        value = re.sub(r"\n?To resume this session: kimi -r [0-9a-f-]+", "", text or "", flags=re.I).strip()
        return value

    def _sanitize_error(self, text: str) -> str:
        return re.sub(r"sk-[A-Za-z0-9_-]+", "sk-***", text or "")[:1000]

    def _extract_json(self, text: str) -> dict:
        candidates = [text]
        if "```json" in text:
            candidates.append(text.split("```json", 1)[1].split("```", 1)[0])
        if "```" in text:
            candidates.append(text.split("```", 1)[1].split("```", 1)[0])
        candidates.extend(self._json_substrings(text or ""))
        for candidate in candidates:
            candidate = candidate.strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise ValueError("新农人助手返回的结构化 JSON 无法解析")

    def _json_substrings(self, text: str) -> list[str]:
        snippets: list[str] = []
        for index, char in enumerate(text):
            if char not in "{[":
                continue
            snippet = self._balanced_json_at(text, index)
            if snippet:
                snippets.append(snippet)
        return snippets

    def _balanced_json_at(self, text: str, start: int) -> str:
        opening = text[start]
        closing = "}" if opening == "{" else "]"
        pairs = {"{": "}", "[": "]"}
        stack = [closing]
        in_string = False
        escape = False
        for index in range(start + 1, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char in pairs:
                stack.append(pairs[char])
                continue
            if stack and char == stack[-1]:
                stack.pop()
                if not stack:
                    return text[start : index + 1]
        return ""
