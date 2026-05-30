"""Executable stdlib HTTP server for the DataSentinel demo API."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .source_http import SourceHttpApp, build_default_app


def make_handler(app: SourceHttpApp | None = None) -> type[BaseHTTPRequestHandler]:
    api = app or build_default_app()

    class DataSentinelHandler(BaseHTTPRequestHandler):
        server_version = "DataSentinelDemo/0.1"

        def do_OPTIONS(self) -> None:
            self._handle()

        def do_GET(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            self._handle()

        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(length) if length else None
            trace_id = self.headers.get("X-Trace-Id") or "trace_http"
            result = api.handle(
                self.command,
                self.path,
                trace_id,
                body,
                self.headers.get("Content-Type"),
                {key: value for key, value in self.headers.items()},
            )
            payload = json.dumps(result["body"]).encode("utf-8") if result["status"] != 204 else b""
            self.send_response(result["status"])
            for key, value in result["headers"].items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DataSentinelHandler


def main() -> None:
    parser = ArgumentParser(description="Run the DataSentinel local demo API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), make_handler())
    print(f"DataSentinel API listening on http://{args.host}:{args.port}/api/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
