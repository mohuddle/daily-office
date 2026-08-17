#!/usr/bin/env python3
"""Serve the Daily Office PWA on the LAN and log every request."""

from __future__ import annotations

import argparse
import datetime as dt
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parents[1] / "web"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        now = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {self.client_address[0]} {fmt % args}", flush=True)


def serve(host: str, port: int) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"serving {ROOT} on http://{host}:{port}/", flush=True)
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--ports", default="8765,8080")
    args = parser.parse_args()
    ports = [int(p) for p in args.ports.split(",") if p.strip()]
    threads = []
    for port in ports:
        t = threading.Thread(target=serve, args=(args.host, port), daemon=True)
        t.start()
        threads.append(t)
    print("Daily Office LAN server running. Press Ctrl+C to stop.", flush=True)
    threads[0].join()


if __name__ == "__main__":
    main()
