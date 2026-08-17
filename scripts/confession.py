#!/usr/bin/env python3
"""Resolve the daily confession reading and benediction."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from bible import number_words, resolve_reference

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "web" / "data" / "confessions"

FULL_TO_ALIAS = {
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

SOURCE_NAMES = {
    "wcf": "the Westminster Confession of Faith",
    "wsc": "the Westminster Shorter Catechism",
    "wlc": "the Westminster Larger Catechism",
    "hc": "the Heidelberg Catechism",
    "belgic": "the Belgic Confession",
    "standards": "the Westminster Standards",
}


def _load(name: str):
    return json.loads((CONF / name).read_text(encoding="utf-8"))


_CORPUS = None
_DAILY = None
_ECHOES = None
_BENEDICTIONS = None


def corpus() -> dict:
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = _load("corpus.json")
    return _CORPUS


def daily_calendar() -> dict:
    global _DAILY
    if _DAILY is None:
        _DAILY = _load("westminster_daily.json")
    return _DAILY


def echoes() -> list:
    global _ECHOES
    if _ECHOES is None:
        _ECHOES = _load("echoes.json")
    return _ECHOES


def benedictions() -> list:
    global _BENEDICTIONS
    if _BENEDICTIONS is None:
        _BENEDICTIONS = _load("benedictions.json")["items"]
    return _BENEDICTIONS


def lesson_chapters(refs: list[str]) -> set[tuple[str, int]]:
    found: set[tuple[str, int]] = set()
    for ref in refs:
        try:
            passage = resolve_reference(ref)
        except Exception:
            continue
        alias = FULL_TO_ALIAS.get(passage["book"].lower())
        if not alias:
            continue
        for verse in passage["verses"]:
            found.add((alias, verse["chapter"]))
    return found


def echo_for_lessons(refs: list[str]) -> dict | None:
    chapters = lesson_chapters(refs)
    if not chapters:
        return None
    for echo in echoes():
        echo_set = {(item["book"], item["chapter"]) for item in echo["refs"]}
        if chapters & echo_set:
            return echo
    return None


def resolve_item(item: dict) -> dict:
    src = item["source"]
    data = corpus()
    if src == "wcf":
        chapter = next(ch for ch in data["wcf"]["chapters"] if ch["chapter"] == item["chapter"])
        section = next(sec for sec in chapter["sections"] if sec["section"] == item["section"])
        return {
            "source": src,
            "label": f"Westminster Confession {item['chapter']}.{item['section']}",
            "heading": f"Chapter {item['chapter']}. {chapter['title']}",
            "body": section["text"],
            "spoken": (
                f"Chapter {number_words(item['chapter'])}, {chapter['title']}, "
                f"section {number_words(item['section'])}. {section['text']}"
            ),
        }
    if src in {"wsc", "wlc", "hc"}:
        key = src
        entry = next(q for q in data[key]["items"] if q["number"] == item["number"])
        title = data[key]["title"]
        qn = entry["number"]
        return {
            "source": src,
            "label": f"{title} Q{qn}",
            "heading": f"Q{qn}. {entry['question']}",
            "body": entry["answer"],
            "spoken": (
                f"Question {number_words(qn)}. {entry['question']} {entry['answer']}"
            ),
        }
    if src == "belgic":
        entry = next(a for a in data["belgic"]["items"] if a["article"] == item["article"])
        return {
            "source": src,
            "label": f"Belgic Confession Article {entry['article']}",
            "heading": f"Article {entry['article']}. {entry['title']}",
            "body": entry["text"],
            "spoken": (
                f"Article {number_words(entry['article'])}, {entry['title']}. {entry['text']}"
            ),
        }
    raise KeyError(item)


def evening_sequential(d: date) -> dict:
    hc_count = len(corpus()["hc"]["items"])
    belgic_count = len(corpus()["belgic"]["items"])
    cycle = hc_count + belgic_count
    index = (d.timetuple().tm_yday - 1) % cycle
    if index < hc_count:
        return resolve_item({"source": "hc", "number": index + 1})
    return resolve_item({"source": "belgic", "article": index - hc_count + 1})


def morning_sequential(d: date) -> list[dict]:
    key = d.strftime("%m-%d")
    plan = daily_calendar().get(key) or daily_calendar().get("02-28")
    return [resolve_item(item) for item in plan["items"]]


def reading_name(items: list[dict], *, echo: bool) -> str:
    sources = {item["source"] for item in items}
    if echo:
        return SOURCE_NAMES[items[0]["source"]]
    if sources <= {"wsc", "wlc", "wcf"} and len(sources) > 1:
        return SOURCE_NAMES["standards"]
    return SOURCE_NAMES[items[0]["source"]]


def confession_for(d: date, office_id: str, lessons: list[str]) -> dict | None:
    if office_id not in {"morning", "evening"}:
        return None
    echo = echo_for_lessons(lessons)
    if echo:
        item = resolve_item({"source": echo["source"], **echo["cite"]})
        return {
            "mode": "echo",
            "name": reading_name([item], echo=True),
            "echo_label": echo["echo"],
            "matched": echo["scripture"],
            "items": [item],
        }
    if office_id == "morning":
        items = morning_sequential(d)
        return {
            "mode": "daily",
            "name": reading_name(items, echo=False),
            "items": items,
        }
    item = evening_sequential(d)
    return {
        "mode": "daily",
        "name": reading_name([item], echo=False),
        "items": [item],
    }


def benediction_for(d: date, office_id: str) -> dict:
    items = benedictions()
    index = (d.timetuple().tm_yday - 1) % len(items)
    if office_id == "evening":
        index = (index + 3) % len(items)
    return items[index]


def spoken_confession(block: dict) -> str:
    parts = [f"A reading from {block['name']}."]
    for item in block["items"]:
        parts.append(item["spoken"])
    return " ".join(parts)
