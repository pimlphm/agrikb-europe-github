from __future__ import annotations

import io
import json
import re
import subprocess
import tempfile
import threading
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = ROOT / "models" / "vosk" / "vosk-model-small-cn-0.22"
_MODEL = None
_MODEL_LOCK = threading.Lock()


def get_stt_status() -> dict:
    try:
        import vosk  # noqa: F401

        package_available = True
    except Exception:
        package_available = False
    try:
        import imageio_ffmpeg  # noqa: F401

        converter_available = True
    except Exception:
        converter_available = False
    return {
        "available": package_available and DEFAULT_MODEL_DIR.exists(),
        "engine": "vosk",
        "language": "zh-CN",
        "model_dir": str(DEFAULT_MODEL_DIR),
        "model_present": DEFAULT_MODEL_DIR.exists(),
        "converter": "ffmpeg",
        "converter_available": converter_available,
    }


def transcribe_chinese_audio_bytes(audio_bytes: bytes, filename: str = "", content_type: str = "") -> dict:
    if not audio_bytes:
        raise ValueError("录音为空，请重新录制。")
    if _looks_like_wav(audio_bytes, filename=filename, content_type=content_type):
        return transcribe_chinese_wav_bytes(audio_bytes)
    wav_bytes = _convert_audio_to_wav(audio_bytes, filename=filename, content_type=content_type)
    result = transcribe_chinese_wav_bytes(wav_bytes)
    result["source_format"] = content_type or Path(filename or "audio").suffix.lstrip(".") or "browser-audio"
    result["converted"] = True
    return result


def transcribe_chinese_wav_bytes(audio_bytes: bytes) -> dict:
    if not audio_bytes:
        raise ValueError("录音为空，请重新录制。")
    model = _load_model()
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            if channels != 1 or sample_width != 2:
                raise ValueError("录音格式需要是单声道 16 位 WAV。")
            recognizer = _build_recognizer(model, sample_rate)
            parts: list[str] = []
            while True:
                chunk = wav_file.readframes(4000)
                if not chunk:
                    break
                if recognizer.AcceptWaveform(chunk):
                    parts.append(_result_text(recognizer.Result()))
            parts.append(_result_text(recognizer.FinalResult()))
    except wave.Error as exc:
        raise ValueError("录音格式不是有效 WAV，请重新录制。") from exc
    text = _clean_chinese_transcript("".join(parts))
    return {
        "text": text,
        "transcript": text,
        "language": "zh-CN",
        "engine": "vosk",
        "sample_rate": sample_rate if "sample_rate" in locals() else None,
        "message": "已完成本地中文转写。" if text else "没有识别到中文内容。",
    }


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not DEFAULT_MODEL_DIR.exists():
        raise RuntimeError("本地中文语音识别模型未安装，请先下载 vosk-model-small-cn-0.22。")
    try:
        from vosk import Model, SetLogLevel
    except Exception as exc:
        raise RuntimeError("Vosk 语音识别组件未安装，请运行 Setup-NewComputer.ps1 或安装 requirements-runtime.txt。") from exc
    with _MODEL_LOCK:
        if _MODEL is None:
            SetLogLevel(-1)
            _MODEL = Model(str(DEFAULT_MODEL_DIR))
    return _MODEL


def _looks_like_wav(audio_bytes: bytes, filename: str = "", content_type: str = "") -> bool:
    suffix = Path(filename or "").suffix.lower()
    content = (content_type or "").lower()
    has_wav_header = audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"
    return has_wav_header or suffix == ".wav" or "wav" in content


def _input_suffix(filename: str = "", content_type: str = "") -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".wav", ".webm", ".ogg", ".oga", ".mp4", ".m4a", ".aac", ".mp3"}:
        return suffix
    content = (content_type or "").lower()
    if "webm" in content:
        return ".webm"
    if "ogg" in content or "opus" in content:
        return ".ogg"
    if "mp4" in content or "m4a" in content:
        return ".m4a"
    if "mpeg" in content or "mp3" in content:
        return ".mp3"
    return ".bin"


def _convert_audio_to_wav(audio_bytes: bytes, filename: str = "", content_type: str = "") -> bytes:
    try:
        import imageio_ffmpeg
    except Exception as exc:
        raise RuntimeError("浏览器录音需要音频转换组件，请安装 imageio-ffmpeg 后再试。") from exc
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="agrikb_stt_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / f"input{_input_suffix(filename=filename, content_type=content_type)}"
        output_path = tmp_path / "output.wav"
        input_path.write_bytes(audio_bytes)
        command = [
            ffmpeg_exe,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=45)
        if completed.returncode != 0 or not output_path.exists():
            detail = (completed.stderr or completed.stdout or "").strip()
            raise ValueError(f"录音格式转换失败：{detail or '无法读取浏览器录音'}")
        return output_path.read_bytes()


def _build_recognizer(model, sample_rate: int):
    from vosk import KaldiRecognizer

    recognizer = KaldiRecognizer(model, float(sample_rate))
    recognizer.SetWords(False)
    return recognizer


def _result_text(raw: str) -> str:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return ""
    return str(payload.get("text") or "")


def _clean_chinese_transcript(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"([\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", r"\1", value)
    value = re.sub(r"\s+([，。！？；：、,.!?;:])", r"\1", value)
    value = re.sub(r"([，。！？；：、])\s+", r"\1", value)
    return value.strip()
