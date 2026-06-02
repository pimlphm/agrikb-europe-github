from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
PIPER_DIR = ROOT / "models" / "piper"
DEFAULT_VOICE = "zh_CN-huayan-medium"
DEFAULT_MODEL = PIPER_DIR / f"{DEFAULT_VOICE}.onnx"
DEFAULT_CONFIG = PIPER_DIR / f"{DEFAULT_VOICE}.onnx.json"
OUTPUT_DIR = ROOT / "runtime" / "tts"
MAX_TTS_CHARS = 900
DEFAULT_DAEMON_URL = os.environ.get("AGRIKB_TTS_DAEMON_URL", "http://127.0.0.1:8011")


def get_tts_status(check_daemon: bool = True) -> dict:
    daemon_status = _get_daemon_status() if check_daemon else {"available": False}
    return {
        "engine": "piper-tts",
        "voice": DEFAULT_VOICE,
        "language": "zh-CN",
        "available": (_piper_available() and DEFAULT_MODEL.exists() and DEFAULT_CONFIG.exists()) or daemon_status.get("available", False),
        "model_path": str(DEFAULT_MODEL),
        "config_path": str(DEFAULT_CONFIG),
        "model_exists": DEFAULT_MODEL.exists(),
        "config_exists": DEFAULT_CONFIG.exists(),
        "piper_installed": _piper_available(),
        "daemon_url": DEFAULT_DAEMON_URL,
        "daemon_available": daemon_status.get("available", False),
        "open_source": True,
    }


def synthesize_chinese_tts_bytes(text: str, rate: float = 1.0) -> tuple[bytes, str]:
    try:
        response = requests.post(
            f"{DEFAULT_DAEMON_URL.rstrip('/')}/tts",
            json={"text": text, "rate": rate},
            timeout=120,
        )
        response.raise_for_status()
        return response.content, response.headers.get("X-AgriKB-TTS-File", "agrikb-tts.wav")
    except Exception:
        wav_path = synthesize_chinese_tts(text, rate=rate)
        return wav_path.read_bytes(), wav_path.name


def synthesize_chinese_tts(text: str, rate: float = 1.0) -> Path:
    clean_text = _clean_tts_text(text)
    if not clean_text:
        raise ValueError("TTS text is empty.")
    if not _piper_available():
        raise RuntimeError("piper-tts is not installed. Run Setup-NewComputer.ps1 or install requirements-runtime.txt.")
    if not DEFAULT_MODEL.exists() or not DEFAULT_CONFIG.exists():
        raise RuntimeError("Chinese Piper voice model is missing. Expected models/piper/zh_CN-huayan-medium.onnx and .onnx.json.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    length_scale = max(0.62, min(1.7, 1.0 / max(0.55, min(1.85, float(rate or 1.0)))))
    cache_key = hashlib.sha256(f"{DEFAULT_VOICE}|{length_scale:.3f}|{clean_text}".encode("utf-8")).hexdigest()[:24]
    output_path = OUTPUT_DIR / f"agrikb-tts-{cache_key}.wav"
    if output_path.exists() and output_path.stat().st_size > 44:
        return output_path

    temp_output_path = OUTPUT_DIR / f"agrikb-tts-{cache_key}.tmp.wav"
    temp_input_path = OUTPUT_DIR / f"agrikb-tts-{cache_key}.txt"
    if temp_output_path.exists():
        temp_output_path.unlink()
    temp_input_path.write_text(clean_text + "\n", encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "piper",
        "-m",
        str(DEFAULT_MODEL),
        "-c",
        str(DEFAULT_CONFIG),
        "-i",
        str(temp_input_path),
        "-f",
        str(temp_output_path),
        "--length-scale",
        f"{length_scale:.3f}",
        "--sentence-silence",
        "0.18",
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ROOT),
            timeout=90,
            check=False,
        )
    finally:
        temp_input_path.unlink(missing_ok=True)
    if completed.returncode != 0 or not temp_output_path.exists() or temp_output_path.stat().st_size <= 44:
        stderr = completed.stderr.decode("utf-8", "replace") if isinstance(completed.stderr, bytes) else str(completed.stderr or "")
        stdout = completed.stdout.decode("utf-8", "replace") if isinstance(completed.stdout, bytes) else str(completed.stdout or "")
        detail = (stderr or stdout or "unknown piper error").strip()
        raise RuntimeError(f"Piper TTS failed: {detail[:600]}")
    temp_output_path.replace(output_path)
    return output_path


def _piper_available() -> bool:
    return importlib.util.find_spec("piper") is not None


def _get_daemon_status() -> dict:
    try:
        response = requests.get(f"{DEFAULT_DAEMON_URL.rstrip('/')}/status", timeout=0.6)
        if response.ok:
            return response.json()
    except Exception:
        pass
    return {"available": False}


def _clean_tts_text(text: str) -> str:
    cleaned = " ".join(str(text or "").replace("\u200b", "").split())
    if len(cleaned) > MAX_TTS_CHARS:
        truncated = cleaned[:MAX_TTS_CHARS]
        sentence_end = max(truncated.rfind(mark) for mark in ("\u3002", "\uff01", "\uff1f", ".", "!", "?"))
        return truncated[: sentence_end + 1] if sentence_end > 120 else truncated
    return cleaned
