#!/usr/bin/env python3
"""Build confession data: corpus, Westminster Daily calendar, Dogmatika echoes."""

from __future__ import annotations

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "data" / "confessions"
CREED_SRC = Path("/tmp/creeds")
PLAN_TXT = Path("/tmp/dogmatika/plan.txt")
UA = {"User-Agent": "daily-office-confession-builder/1.0"}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        if tag in {"p", "h1", "h2", "h3", "div", "li", "br"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def load_creed(name: str) -> dict:
    return json.loads((CREED_SRC / name).read_text(encoding="utf-8"))


def compact_wcf() -> dict:
    raw = load_creed("westminster_confession_of_faith.json")
    chapters = []
    for ch in raw["Data"]:
        sections = []
        for sec in ch["Sections"]:
            sections.append({"section": int(sec["Section"]), "text": sec["Content"].strip()})
        chapters.append(
            {
                "chapter": int(ch["Chapter"]),
                "title": ch["Title"].strip(),
                "sections": sections,
            }
        )
    return {"title": "Westminster Confession of Faith", "chapters": chapters}


def compact_catechism(filename: str, title: str) -> dict:
    raw = load_creed(filename)
    items = []
    for item in raw["Data"]:
        items.append(
            {
                "number": int(item["Number"]),
                "question": item["Question"].strip(),
                "answer": item["Answer"].strip(),
            }
        )
    return {"title": title, "items": items}


def compact_belgic() -> dict:
    raw = load_creed("belgic_confession_of_faith.json")
    items = []
    for item in raw["Data"]:
        items.append(
            {
                "article": int(item["Article"]),
                "title": item["Title"].strip(),
                "text": item["Content"].strip(),
            }
        )
    return {"title": "Belgic Confession", "items": items}


def fetch_day(mm: int, dd: int) -> tuple[str, dict]:
    key = f"{mm:02d}-{dd:02d}"
    url = f"https://reformedconfessions.com/westminster-daily/{mm:02d}/{dd:02d}"
    req = urllib.request.Request(url, headers=UA)
    html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    parser = TextExtractor()
    parser.feed(html)
    text = re.sub(r"\s+", " ", "".join(parser.parts))
    items: list[dict] = []
    for num in re.findall(r"Shorter Catechism Q (\d+)\.", text):
        items.append({"source": "wsc", "number": int(num)})
    for num in re.findall(r"Larger Catechism Q (\d+)\.", text):
        items.append({"source": "wlc", "number": int(num)})
    m = re.search(r"Confession of Faith Chapter (\d+):.*?(\d+)\.", text)
    if m:
        items.append({"source": "wcf", "chapter": int(m.group(1)), "section": int(m.group(2))})
    heading = ""
    hm = re.search(r"next year\.\s+(.*?)\s+(Shorter Catechism|Larger Catechism|Confession of Faith)", text)
    if hm:
        heading = hm.group(1).strip()
    return key, {"heading": heading, "items": items}


def scrape_westminster_daily() -> dict:
    jobs = [(m, d) for m in range(1, 13) for d in range(1, 32)]
    jobs.append((2, 29))
    calendar: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(fetch_day, m, d) for m, d in jobs]
        for fut in as_completed(futs):
            try:
                key, payload = fut.result()
            except Exception as exc:
                print("skip day", exc)
                continue
            if payload["items"] or payload["heading"]:
                calendar[key] = payload
                print(f"  {key} {payload['items']}")
    return calendar


BOOK_ALIASES = {
    "genesis": "gen",
    "exodus": "exod",
    "leviticus": "lev",
    "numbers": "num",
    "deuteronomy": "deut",
    "joshua": "josh",
    "judges": "judg",
    "ruth": "ruth",
    "1 samuel": "1sam",
    "2 samuel": "2sam",
    "1 kings": "1kgs",
    "2 kings": "2kgs",
    "1 chronicles": "1chr",
    "2 chronicles": "2chr",
    "ezra": "ezra",
    "nehemiah": "neh",
    "esther": "esth",
    "job": "job",
    "psalm": "ps",
    "psalms": "ps",
    "proverbs": "prov",
    "ecclesiastes": "eccl",
    "song of solomon": "song",
    "isaiah": "isa",
    "jeremiah": "jer",
    "lamentations": "lam",
    "ezekiel": "ezek",
    "daniel": "dan",
    "hosea": "hos",
    "joel": "joel",
    "amos": "amos",
    "obadiah": "obad",
    "jonah": "jonah",
    "micah": "mic",
    "nahum": "nah",
    "habakkuk": "hab",
    "zephaniah": "zeph",
    "haggai": "hag",
    "zechariah": "zech",
    "malachi": "mal",
    "matthew": "matt",
    "mark": "mark",
    "luke": "luke",
    "john": "john",
    "acts": "acts",
    "romans": "rom",
    "1 corinthians": "1cor",
    "2 corinthians": "2cor",
    "galatians": "gal",
    "ephesians": "eph",
    "philippians": "phil",
    "colossians": "col",
    "1 thessalonians": "1thess",
    "2 thessalonians": "2thess",
    "1 timothy": "1tim",
    "2 timothy": "2tim",
    "titus": "titus",
    "philemon": "phlm",
    "hebrews": "heb",
    "james": "jas",
    "1 peter": "1pet",
    "2 peter": "2pet",
    "1 john": "1john",
    "2 john": "2john",
    "3 john": "3john",
    "jude": "jude",
    "revelation": "rev",
}


def parse_scripture_chunk(chunk: str) -> list[dict]:
    chunk = chunk.replace("–", "-").replace("—", "-").strip()
    chunk = re.sub(r"\s+", " ", chunk)
    if not chunk:
        return []
    m = re.match(r"^([1-3]?\s?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(.+)$", chunk)
    if not m:
        return []
    book = re.sub(r"\s+", " ", m.group(1)).strip().lower()
    rest = m.group(2).strip()
    alias = BOOK_ALIASES.get(book)
    if not alias:
        print("unknown book", book, "in", chunk)
        return []
    chapters: list[int] = []
    # e.g. 1-3  or  34-34; Joshua 1-2 handled outside  or  1-2
    first = rest.split(";")[0].strip()
    mm = re.match(r"^(\d+)(?:-(\d+))?", first)
    if not mm:
        return []
    start = int(mm.group(1))
    end = int(mm.group(2) or start)
    for n in range(start, end + 1):
        chapters.append(n)
    return [{"book": alias, "chapter": n} for n in chapters]


def parse_scripture_list(blob: str) -> list[dict]:
    refs = []
    for part in re.split(r"\s*[·;]\s*", blob):
        refs.extend(parse_scripture_chunk(part))
    return refs


def parse_echoes() -> list[dict]:
    text = PLAN_TXT.read_text(encoding="utf-8")
    echoes = []
    for raw in text.splitlines():
        line = raw.replace("\x0c", "").rstrip()
        m = re.match(
            r"^[A-Z][a-z]{2}\s+\d{2}\s+Read Scripture — (.+?)(?:\s{2,}(.+))?$",
            line,
        )
        if not m:
            continue
        scripture = m.group(1).strip()
        echo = (m.group(2) or "").strip()
        if not echo:
            # echo may be on same line with single spaces at end
            em = re.search(
                r"(Heidelberg Catechism Q\d+|Belgic Confession Art\. \d+|Westminster Confession \d+\.\d+|Canons of Dort V\.\d+|Confessional Anchor — Belgic Confession)\s*$",
                scripture,
            )
            if em:
                echo = em.group(1)
                scripture = scripture[: em.start()].strip()
        if not echo:
            continue
        if echo.startswith("Canons of Dort") or echo.startswith("Confessional Anchor"):
            continue
        refs = parse_scripture_list(scripture)
        kind, cite = classify_echo(echo)
        if not kind:
            print("unparsed echo", echo)
            continue
        echoes.append(
            {
                "scripture": scripture,
                "refs": refs,
                "echo": echo,
                "source": kind,
                "cite": cite,
            }
        )
    return echoes


def classify_echo(echo: str) -> tuple[str | None, dict]:
    if m := re.match(r"Heidelberg Catechism Q(\d+)$", echo):
        return "hc", {"number": int(m.group(1))}
    if m := re.match(r"Belgic Confession Art\. (\d+)$", echo):
        return "belgic", {"article": int(m.group(1))}
    if m := re.match(r"Westminster Confession (\d+)\.(\d+)$", echo):
        return "wcf", {"chapter": int(m.group(1)), "section": int(m.group(2))}
    return None, {}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("compacting creeds")
    corpus = {
        "wcf": compact_wcf(),
        "wsc": compact_catechism("westminster_shorter_catechism.json", "Westminster Shorter Catechism"),
        "wlc": compact_catechism("westminster_larger_catechism.json", "Westminster Larger Catechism"),
        "hc": compact_catechism("heidelberg_catechism.json", "Heidelberg Catechism"),
        "belgic": compact_belgic(),
    }
    (OUT / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    print("scraping Westminster Daily")
    calendar = scrape_westminster_daily()
    (OUT / "westminster_daily.json").write_text(json.dumps(calendar, indent=2), encoding="utf-8")
    print("days", len(calendar))
    print("parsing Dogmatika echoes")
    echoes = parse_echoes()
    (OUT / "echoes.json").write_text(json.dumps(echoes, indent=2), encoding="utf-8")
    print("echoes", len(echoes))
    print("done")


if __name__ == "__main__":
    main()
