from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

from piper.voice import PiperVoice, SynthesisConfig


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: piper_synth_worker.py INPUT_JSON MODEL_ONNX OUTPUT_WAV", file=sys.stderr)
        return 2
    input_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    text = str(payload.get("text") or "").strip()
    length_scale = float(payload.get("length_scale") or 1.0)
    sentence_silence = float(payload.get("sentence_silence") or 0.18)
    if not text:
        raise ValueError("empty text")

    voice = PiperVoice.load(model_path)
    config = SynthesisConfig(length_scale=length_scale)
    silence = b""
    with wave.open(str(output_path), "wb") as wav_file:
        params_set = False
        wrote_audio = False
        for index, chunk in enumerate(voice.synthesize(text, config)):
            if not params_set:
                wav_file.setframerate(chunk.sample_rate)
                wav_file.setsampwidth(chunk.sample_width)
                wav_file.setnchannels(chunk.sample_channels)
                silence = bytes(int(chunk.sample_rate * sentence_silence * chunk.sample_width))
                params_set = True
            if index > 0 and silence:
                wav_file.writeframes(silence)
            wav_file.writeframes(chunk.audio_int16_bytes)
            wrote_audio = True
        if not wrote_audio:
            raise RuntimeError("piper produced no audio chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
