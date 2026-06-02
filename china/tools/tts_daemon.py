from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.backend.voice_tts import get_tts_status, synthesize_chinese_tts


class TTSHandler(BaseHTTPRequestHandler):
    server_version = "AgriKBChineseTTS/1.0"

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/status":
            self.send_error(404)
            return
        self._send_json({**get_tts_status(check_daemon=False), "available": True, "daemon": "single-thread-main"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/tts":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            wav_path = synthesize_chinese_tts(str(payload.get("text") or ""), rate=float(payload.get("rate") or 1.0))
            data = wav_path.read_bytes()
        except Exception as exc:
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": str(exc)}, ensure_ascii=False).encode("utf-8"))
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-AgriKB-TTS-File", wav_path.name)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="AgriKB local Chinese TTS daemon")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), TTSHandler)
    print(f"AgriKB Chinese TTS daemon listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
