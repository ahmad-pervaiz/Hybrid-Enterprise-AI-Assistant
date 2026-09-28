"""Web UI for the Hybrid Enterprise AI Assistant.

Serves ui/index.html and a small JSON API using only the standard library.
The RAG engine is built in a background thread so the UI is usable
(OKF queries) while the embedding model and FAISS index load.

Usage:
    python ui_server.py [--port 8000]
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from okf_engine import OKFEngine
from router import Router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OKF_ROOT = os.path.join(BASE_DIR, "okf_knowledge")
DOCS_ROOT = os.path.join(BASE_DIR, "docs")
UI_FILE = os.path.join(BASE_DIR, "ui", "index.html")

router = Router(OKFEngine(OKF_ROOT))
rag_status = {"state": "loading", "message": "Loading embedding model and FAISS index..."}


def _load_rag() -> None:
    try:
        from rag_engine import RAGEngine

        router.rag_engine = RAGEngine(DOCS_ROOT)
        rag_status.update(state="ready", message="FAISS index ready")
    except Exception as exc:
        rag_status.update(state="unavailable", message=f"{type(exc).__name__}: {exc}")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            with open(UI_FILE, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            self._json(200, {"okf": {"state": "ready"}, "rag": rag_status})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/api/query":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            query = json.loads(self.rfile.read(length) or b"{}").get("query", "").strip()
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON body"})
            return
        if not query:
            self._json(400, {"error": "query is required"})
            return
        self._json(200, router.route(query))

    def log_message(self, fmt: str, *args) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    threading.Thread(target=_load_rag, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Hybrid Enterprise AI Assistant UI: http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
