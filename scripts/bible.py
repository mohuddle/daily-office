#!/usr/bin/env python3
"""Parse lectionary references against the Berean Standard Bible."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BSB_JSON = ROOT / "web" / "data" / "bsb.json"

ABBREV = {
    "Gen": "Genesis",
    "Exod": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deut": "Deuteronomy",
    "Josh": "Joshua",
    "Judg": "Judges",
    "Ruth": "Ruth",
    "1 Sam": "1 Samuel",
    "2 Sam": "2 Samuel",
    "1 Kgs": "1 Kings",
    "2 Kgs": "2 Kings",
    "1 Chr": "1 Chronicles",
    "2 Chr": "2 Chronicles",
    "Ezra": "Ezra",
    "Neh": "Nehemiah",
    "Esth": "Esther",
    "Job": "Job",
    "Ps": "Psalm",
    "Psalm": "Psalm",
    "Psalms": "Psalm",
    "Prov": "Proverbs",
    "Eccl": "Ecclesiastes",
    "Song": "Song of Solomon",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Ezek": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obad": "Obadiah",
    "Jonah": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zeph": "Zephaniah",
    "Hag": "Haggai",
    "Zech": "Zechariah",
    "Mal": "Malachi",
    "Matt": "Matthew",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Rom": "Romans",
    "1 Cor": "1 Corinthians",
    "2 Cor": "2 Corinthians",
    "Gal": "Galatians",
    "Eph": "Ephesians",
    "Phil": "Philippians",
    "Col": "Colossians",
    "1 Thess": "1 Thessalonians",
    "2 Thess": "2 Thessalonians",
    "1 Tim": "1 Timothy",
    "2 Tim": "2 Timothy",
    "Titus": "Titus",
    "Phlm": "Philemon",
    "Philemon": "Philemon",
    "Heb": "Hebrews",
    "Jas": "James",
    "1 Pet": "1 Peter",
    "2 Pet": "2 Peter",
    "1 John": "1 John",
    "2 John": "2 John",
    "3 John": "3 John",
    "Jude": "Jude",
    "Rev": "Revelation",
    "Genesis": "Genesis",
    "Exodus": "Exodus",
    "Leviticus": "Leviticus",
    "Numbers": "Numbers",
    "Deuteronomy": "Deuteronomy",
    "Joshua": "Joshua",
    "Judges": "Judges",
    "1 Samuel": "1 Samuel",
    "2 Samuel": "2 Samuel",
    "1 Kings": "1 Kings",
    "2 Kings": "2 Kings",
    "1 Chronicles": "1 Chronicles",
    "2 Chronicles": "2 Chronicles",
    "Nehemiah": "Nehemiah",
    "Esther": "Esther",
    "Proverbs": "Proverbs",
    "Ecclesiastes": "Ecclesiastes",
    "Song of Solomon": "Song of Solomon",
    "Isaiah": "Isaiah",
    "Jeremiah": "Jeremiah",
    "Lamentations": "Lamentations",
    "Ezekiel": "Ezekiel",
    "Daniel": "Daniel",
    "Hosea": "Hosea",
    "Obadiah": "Obadiah",
    "Micah": "Micah",
    "Nahum": "Nahum",
    "Habakkuk": "Habakkuk",
    "Zephaniah": "Zephaniah",
    "Haggai": "Haggai",
    "Zechariah": "Zechariah",
    "Malachi": "Malachi",
    "Matthew": "Matthew",
    "Romans": "Romans",
    "1 Corinthians": "1 Corinthians",
    "2 Corinthians": "2 Corinthians",
    "Galatians": "Galatians",
    "Ephesians": "Ephesians",
    "Philippians": "Philippians",
    "Colossians": "Colossians",
    "1 Thessalonians": "1 Thessalonians",
    "2 Thessalonians": "2 Thessalonians",
    "1 Timothy": "1 Timothy",
    "2 Timothy": "2 Timothy",
    "Philemon": "Philemon",
    "Hebrews": "Hebrews",
    "James": "James",
    "1 Peter": "1 Peter",
    "2 Peter": "2 Peter",
    "Revelation": "Revelation",
}

ABBREV_KEYS = sorted(ABBREV, key=len, reverse=True)

_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

_bible: dict | None = None


def load_bible() -> dict:
    global _bible
    if _bible is None:
        _bible = json.loads(BSB_JSON.read_text(encoding="utf-8"))
    return _bible


def normalize(ref: str) -> str:
    return (
        ref.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .strip()
    )


def strip_ab(token: str) -> str:
    return re.sub(r"[abAB]$", "", token)


def number_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] if ones == 0 else f"{_TENS[tens]}-{_ONES[ones]}"
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        if rest == 0:
            return f"{_ONES[hundreds]} hundred"
        return f"{_ONES[hundreds]} hundred {number_words(rest)}"
    return str(n)


def chapter_count(book: str, chapter: int) -> int:
    bible = load_bible()
    return len(bible[book][str(chapter)])


def verse_text(book: str, chapter: int, verse: int) -> str:
    bible = load_bible()
    try:
        return bible[book][str(chapter)][str(verse)]
    except KeyError as exc:
        raise KeyError(f"Missing {book} {chapter}:{verse}") from exc


def split_book(ref: str) -> tuple[str, str]:
    raw = normalize(ref)
    for key in ABBREV_KEYS:
        if raw == key or raw.startswith(key + " "):
            rest = raw[len(key):].strip()
            return ABBREV[key], rest
    raise ValueError(f"Unknown book in reference: {ref}")


def expand_span(book: str, start_ch: int, start_vs: int | None, end_ch: int, end_vs: int | None) -> list[dict]:
    verses: list[dict] = []
    ch = start_ch
    while ch <= end_ch:
        first = start_vs if ch == start_ch and start_vs else 1
        last = end_vs if ch == end_ch and end_vs else chapter_count(book, ch)
        for vs in range(first, last + 1):
            verses.append(
                {
                    "book": book,
                    "chapter": ch,
                    "verse": vs,
                    "text": verse_text(book, ch, vs),
                }
            )
        ch += 1
    return verses


def parse_numeric_parts(book: str, rest: str) -> list[dict]:
    if not rest:
        raise ValueError(f"No chapter/verse for {book}")
    parts = [p.strip() for p in rest.split(",") if p.strip()]
    verses: list[dict] = []
    last_chapter: int | None = None
    for part in parts:
        part = strip_ab(part.replace(" ", ""))
        part = re.sub(r"[abAB](?=-|$)", "", part)
        m = re.fullmatch(r"(\d+):(\d+)-(\d+):(\d+)", part)
        if m:
            verses.extend(expand_span(book, int(m[1]), int(m[2]), int(m[3]), int(m[4])))
            last_chapter = int(m[3])
            continue
        m = re.fullmatch(r"(\d+)-(\d+):(\d+)-(\d+)", part)
        if m:
            verses.extend(expand_span(book, int(m[1]), None, int(m[2]), int(m[4])))
            last_chapter = int(m[2])
            continue
        m = re.fullmatch(r"(\d+)-(\d+):(\d+)", part)
        if m:
            verses.extend(expand_span(book, int(m[1]), None, int(m[2]), int(m[3])))
            last_chapter = int(m[2])
            continue
        m = re.fullmatch(r"(\d+):(\d+)-(\d+)", part)
        if m:
            verses.extend(expand_span(book, int(m[1]), int(m[2]), int(m[1]), int(m[3])))
            last_chapter = int(m[1])
            continue
        m = re.fullmatch(r"(\d+):(\d+)", part)
        if m:
            verses.extend(expand_span(book, int(m[1]), int(m[2]), int(m[1]), int(m[2])))
            last_chapter = int(m[1])
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            if last_chapter is not None and int(m[1]) <= chapter_count(book, last_chapter) and int(m[2]) <= chapter_count(book, last_chapter) and int(m[1]) < 50:
                # verse range inheriting chapter: "18-20"
                verses.extend(expand_span(book, last_chapter, int(m[1]), last_chapter, int(m[2])))
            else:
                verses.extend(expand_span(book, int(m[1]), None, int(m[2]), None))
                last_chapter = int(m[2])
            continue
        m = re.fullmatch(r"(\d+)", part)
        if m:
            if last_chapter is not None and int(m[1]) <= chapter_count(book, last_chapter):
                verses.extend(expand_span(book, last_chapter, int(m[1]), last_chapter, int(m[1])))
            else:
                verses.extend(expand_span(book, int(m[1]), None, int(m[1]), None))
                last_chapter = int(m[1])
            continue
        raise ValueError(f"Cannot parse passage part {part!r} in {book} {rest}")
    return verses


def resolve_reference(ref: str, *, psalms: bool = False) -> dict:
    raw = normalize(ref)
    if psalms or re.fullmatch(r"[0-9,\-\s]+", raw):
        book = "Psalm"
        verses = parse_numeric_parts(book, raw)
        return {"reference": ref, "book": book, "verses": verses}
    book, rest = split_book(raw)
    verses = parse_numeric_parts(book, rest)
    return {"reference": ref, "book": book, "verses": verses}


def spoken_numbers(*nums: int) -> str:
    return " ".join(number_words(n) for n in nums)


def _psalm_chapters(verses: list[dict]) -> list[int]:
    nums: list[int] = []
    seen: set[int] = set()
    for verse in verses:
        if verse["chapter"] not in seen:
            seen.add(verse["chapter"])
            nums.append(verse["chapter"])
    return nums


def _covers_whole_chapters(book: str, verses: list[dict]) -> bool:
    chapters = _psalm_chapters(verses)
    if verses[0]["verse"] != 1:
        return False
    last_ch = chapters[-1]
    return verses[-1]["verse"] == chapter_count(book, last_ch) and len(verses) == sum(
        chapter_count(book, ch) for ch in chapters
    )


def spoken_reference(ref: str, *, psalms: bool = False) -> str:
    """Speak a citation without ever saying 'colon'. Psalm 6:1 → 'Psalm six one'."""
    passage = resolve_reference(ref, psalms=psalms)
    verses = passage["verses"]
    first, last = verses[0], verses[-1]
    book = passage["book"]
    if book == "Psalm" and (psalms or _covers_whole_chapters(book, verses)):
        nums = _psalm_chapters(verses)
        if len(nums) == 1:
            return f"Psalm {number_words(nums[0])}"
        return (
            "Psalms "
            + ", ".join(number_words(n) for n in nums[:-1])
            + f" and {number_words(nums[-1])}"
        )
    if first["chapter"] == last["chapter"] and first["verse"] == last["verse"] and len(verses) == 1:
        spoken_book = "Psalm" if book == "Psalm" else book
        return f"{spoken_book} {spoken_numbers(first['chapter'], first['verse'])}"
    if first["chapter"] == last["chapter"]:
        spoken_book = "Psalm" if book == "Psalm" else book
        if first["verse"] == 1 and last["verse"] == chapter_count(book, first["chapter"]):
            return f"{spoken_book} {number_words(first['chapter'])}"
        return (
            f"{spoken_book} {spoken_numbers(first['chapter'], first['verse'])} "
            f"through {number_words(last['verse'])}"
        )
    spoken_book = "Psalm" if book == "Psalm" else book
    return (
        f"{spoken_book} {spoken_numbers(first['chapter'], first['verse'])} "
        f"through {spoken_numbers(last['chapter'], last['verse'])}"
    )


SELAH_RE = re.compile(r"\s*Selah\.?", re.IGNORECASE)


def with_selah_pauses(text: str) -> str:
    """Insert a one-second silence before and after every Selah."""
    paused = SELAH_RE.sub(" [silence 1s] Selah. [silence 1s] ", text)
    return re.sub(r"\s+", " ", paused).strip()


def passage_text(ref: str, *, psalms: bool = False) -> str:
    passage = resolve_reference(ref, psalms=psalms)
    chunks: list[str] = []
    current_psalm = None
    for v in passage["verses"]:
        if passage["book"] == "Psalm" and v["chapter"] != current_psalm:
            if current_psalm is not None:
                chunks.append("[silence 2s]")
            current_psalm = v["chapter"]
            chunks.append(f"Psalm {number_words(v['chapter'])}.")
        chunks.append(with_selah_pauses(v["text"]))
    return " ".join(chunks)
