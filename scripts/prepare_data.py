#!/usr/bin/env python3
"""Download and parse the Berean Standard Bible into the PWA data folder."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_DATA = ROOT / "web" / "data"
BSB_URL = "https://bereanbible.com/bsb.txt"
LINE_RE = re.compile(r"^(.+?) (\d+):(\d+)(.*)$")


def parse_bsb(text: str) -> dict:
    bible: dict[str, dict[str, dict[str, str]]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = LINE_RE.match(line)
        if not match:
            continue
        book, chapter, verse, body = match.groups()
        if book == "VerseBerean Standard Bible":
            continue
        body = body.strip()
        if not body:
            continue
        bible.setdefault(book, {}).setdefault(chapter, {})[verse] = body
    if "Psalm" not in bible:
        raise SystemExit("BSB parse failed: no Psalm book found")
    return bible


def main() -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    print("downloading BSB")
    with urllib.request.urlopen(BSB_URL, timeout=120) as resp:
        raw = resp.read().decode("utf-8-sig")
    bible = parse_bsb(raw)
    out = WEB_DATA / "bsb.json"
    out.write_text(json.dumps(bible, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(bible)} books)")


if __name__ == "__main__":
    main()
