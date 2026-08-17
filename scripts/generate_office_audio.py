#!/usr/bin/env python3
"""Generate Scripture audio for one day's four offices."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bible import passage_text, spoken_reference  # noqa: E402
from confession import benediction_for, confession_for, spoken_confession  # noqa: E402
from liturgical import liturgical_day, orientation_sentence  # noqa: E402
from tts import TtsSettings, concat_mp3, make_silence, synthesize as tts_synthesize  # noqa: E402

AUDIO_DIR = ROOT / "web" / "audio"
INDEX_PATH = ROOT / "web" / "data" / "audio.json"
LECTIONARY = ROOT / "web" / "data" / "lectionary.json"
MIDDAY = ROOT / "web" / "data" / "midday.json"
COMPLINE = ROOT / "web" / "data" / "compline.json"
SENTENCES = ROOT / "web" / "data" / "sentences.json"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SILENCE_INVITE = "Let's begin our time together in silence."
SETTINGS: TtsSettings | None = None


def sunday_index(d: date) -> int:
    """Sunday = 0 … Saturday = 6."""
    return (d.weekday() + 1) % 7


def sentence_for(d: date, office_id: str) -> dict | None:
    if office_id not in {"morning", "evening"}:
        return None
    sentences = load_json(SENTENCES)["sentences"]
    index = sunday_index(d)
    if office_id == "evening":
        index = (index + 1) % len(sentences)
    return sentences[index]


def chicago_today() -> date:
    try:
        zone = ZoneInfo("America/Chicago")
    except ZoneInfoNotFoundError as exc:
        raise SystemExit(
            "Windows Python has no timezone database. Install tzdata:\n"
            "  py -3.13 -m pip install tzdata"
        ) from exc
    return datetime.now(zone).date()


def sunday_on_or_after(d: date) -> date:
    return d + timedelta(days=(6 - d.weekday()) % 7)


def week_dates(d: date) -> list[date]:
    start = sunday_on_or_after(d)
    return [start + timedelta(days=offset) for offset in range(7)]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def weekday_key(d: date) -> str:
    return WEEKDAYS[d.weekday()]


def offices_for(d: date) -> dict:
    lect = load_json(LECTIONARY)
    midday = load_json(MIDDAY)
    compline = load_json(COMPLINE)
    day = lect["days"][d.strftime("%m-%d")]
    wd = weekday_key(d)
    return {
        "morning": {
            "id": "morning",
            "title": "Morning Prayer",
            "welcome": "Welcome to Morning Prayer.",
            "filename": f"Morning_Scripture_{d.isoformat()}.mp3",
            "psalms": day["psalms_morning"],
            "lessons": day["morning_lessons"],
            "sentence": sentence_for(d, "morning"),
        },
        "midday": {
            "id": "midday",
            "title": "Midday Prayer",
            "welcome": "Welcome to Midday Prayer.",
            "filename": f"Midday_Scripture_{d.isoformat()}.mp3",
            "psalms": None,
            "lessons": midday["lessons"].get(wd, []),
            "sentence": None,
        },
        "evening": {
            "id": "evening",
            "title": "Evening Prayer",
            "welcome": "Welcome to Evening Prayer.",
            "filename": f"Evening_Scripture_{d.isoformat()}.mp3",
            "psalms": day["psalms_evening"],
            "lessons": day["evening_lessons"],
            "sentence": sentence_for(d, "evening"),
        },
        "compline": {
            "id": "compline",
            "title": "Compline",
            "welcome": "Welcome to Compline.",
            "filename": f"Compline_Scripture_{d.isoformat()}.mp3",
            "psalms": None,
            "lessons": compline["lessons"].get(wd, []),
            "sentence": None,
        },
    }


def opening_script(d: date, office: dict) -> str:
    parts = [
        office["welcome"],
        "[pause]",
        orientation_sentence(d),
    ]
    if office.get("sentence"):
        parts.extend(["[pause]", SILENCE_INVITE])
    return "\n".join(parts)


def sentence_script(office: dict) -> str:
    return office["sentence"]["bsb"]


def lessons_intro_script(office: dict) -> str:
    name = "morning prayer" if office["id"] == "morning" else "evening prayer"
    return f"The lessons for {name}."


def readings_script(d: date, office: dict) -> str:
    parts: list[str] = []
    if office["psalms"]:
        parts.append(f"{spoken_reference(office['psalms'], psalms=True)}.")
        parts.append(passage_text(office["psalms"], psalms=True))
        parts.append("[silence 2s]")
    lessons = office["lessons"]
    labels = ["The first lesson", "The second lesson", "The third lesson"]
    for i, ref in enumerate(lessons):
        label = labels[i] if i < len(labels) else f"Lesson {i + 1}"
        parts.append(f"{label}, {spoken_reference(ref)}.")
        parts.append("[silence 2s]")
        parts.append(passage_text(ref))
        parts.append("[silence 2s]")
    if lessons or office["psalms"]:
        parts.append("The Word of the Lord.")
        parts.append("[pause]")
        parts.append("Thanks be to God.")
    return "\n".join(parts)


def confession_block(d: date, office: dict) -> dict | None:
    if office["id"] not in {"morning", "evening"}:
        return None
    return confession_for(d, office["id"], office["lessons"])


def confession_script(block: dict) -> str:
    return spoken_confession(block)


def benediction_script(d: date, office: dict) -> str:
    return benediction_for(d, office["id"])["text"]


def closing_script(d: date, office: dict, block: dict | None = None) -> str:
    block = block if block is not None else confession_block(d, office)
    if not block:
        return ""
    return "\n".join(
        [
            "[silence 2s]",
            confession_script(block),
            "[silence 2s]",
            benediction_script(d, office),
        ]
    )


def body_script(d: date, office: dict) -> str:
    closing = closing_script(d, office)
    if office.get("sentence"):
        parts = [
            sentence_script(office),
            "[silence 2s]",
            lessons_intro_script(office),
            "[silence 2s]",
            readings_script(d, office),
        ]
        if closing:
            parts.append(closing)
        return "\n".join(parts)
    if closing:
        return readings_script(d, office) + "\n" + closing
    return readings_script(d, office)


def build_script(d: date, office: dict) -> str:
    if office.get("sentence"):
        return "\n".join(
            [
                opening_script(d, office),
                "[silence 4s]",
                body_script(d, office),
            ]
        )
    return "\n".join([opening_script(d, office), "[pause]", body_script(d, office)])


def require_ffmpeg() -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit("ffmpeg is required to stitch office audio.") from exc


def synthesize(text: str, dest: Path) -> None:
    if SETTINGS is None:
        raise RuntimeError("TTS settings were not loaded")
    tts_synthesize(SETTINGS, text, dest)


def update_index(d: date, files: dict[str, str]) -> None:
    index = {}
    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    index[d.isoformat()] = files
    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {}


def already_recorded(d: date, key: str, office: dict, force: bool) -> bool:
    if force:
        return False
    dest = AUDIO_DIR / office["filename"]
    if not dest.exists() or dest.stat().st_size < 1000:
        return False
    return bool(load_index().get(d.isoformat(), {}).get(key))


def generate_office(d: date, office: dict) -> None:
    script = build_script(d, office)
    script_path = ROOT / "web" / "data" / "scripts" / f"{office['id']}_{d.isoformat()}.txt"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")
    dest = AUDIO_DIR / office["filename"]
    print(f"synthesizing {office['id']} ({len(script)} chars) -> {dest.name}", flush=True)
    if office.get("sentence"):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            intro = tmpdir / "intro.mp3"
            sentence = tmpdir / "sentence.mp3"
            cue = tmpdir / "cue.mp3"
            readings = tmpdir / "readings.mp3"
            silence4 = tmpdir / "silence4.mp3"
            silence2 = tmpdir / "silence2.mp3"
            synthesize(opening_script(d, office), intro)
            synthesize(sentence_script(office), sentence)
            synthesize(lessons_intro_script(office), cue)
            synthesize(readings_script(d, office), readings)
            make_silence(silence4, 4)
            make_silence(silence2, 2)
            parts = [intro, silence4, sentence, silence2, cue, silence2, readings]
            block = confession_block(d, office)
            if block:
                confession_mp3 = tmpdir / "confession.mp3"
                benediction_mp3 = tmpdir / "benediction.mp3"
                synthesize(confession_script(block), confession_mp3)
                synthesize(benediction_script(d, office), benediction_mp3)
                parts.extend([silence2, confession_mp3, silence2, benediction_mp3])
            concat_mp3(parts, dest)
    else:
        synthesize(script, dest)
    print(f"  wrote {dest.stat().st_size} bytes", flush=True)


def generate_day(d: date, wanted: list[str] | None = None, force: bool = False) -> list[str]:
    print(f"date {d.isoformat()} {liturgical_day(d)['spoken']}", flush=True)
    offices = offices_for(d)
    keys = wanted or list(offices)
    files = load_index().get(d.isoformat(), {})
    errors: list[str] = []
    for key in keys:
        office = offices[key]
        if not office["lessons"] and not office["psalms"]:
            print(f"skip {key}: no lessons for this weekday", flush=True)
            continue
        if already_recorded(d, key, office, force):
            print(f"skip {key}: already recorded", flush=True)
            files[key] = f"audio/{office['filename']}"
            continue
        try:
            generate_office(d, office)
            files[key] = f"audio/{office['filename']}"
        except Exception as exc:
            message = f"{d.isoformat()} {key}: {exc}"
            print(f"ERROR {message}", flush=True)
            errors.append(message)
    if files:
        update_index(d, files)
        print("audio index updated", flush=True)
    return errors


def dates_from_args(args: argparse.Namespace) -> list[date]:
    if args.week:
        return week_dates(date.fromisoformat(args.date) if args.date else chicago_today())
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    if start or end:
        if not start or not end:
            raise SystemExit("use both --start and --end, or --week")
        if end < start:
            raise SystemExit("--end must be on or after --start")
        days = []
        cursor = start
        while cursor <= end:
            days.append(cursor)
            cursor += timedelta(days=1)
        return days
    return [date.fromisoformat(args.date) if args.date else chicago_today()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD (default: today in America/Chicago)")
    parser.add_argument("--office", choices=["morning", "midday", "evening", "compline"])
    parser.add_argument(
        "--week",
        action="store_true",
        help="Generate Sunday on or after --date through the following Saturday",
    )
    parser.add_argument("--start", help="First date YYYY-MM-DD (use with --end)")
    parser.add_argument("--end", help="Last date YYYY-MM-DD (use with --start)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if an MP3 already exists")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without synthesizing")
    parser.add_argument(
        "--tts",
        choices=["chatterbox", "kokoro", "qwen3", "leo"],
        help="Voice backend (default: chatterbox Multilingual v3, or tts.json)",
    )
    parser.add_argument("--voice", help="Optional Kokoro voice or Qwen speaker")
    parser.add_argument("--tts-ref", help="Optional reference WAV for Chatterbox / Qwen clone")
    parser.add_argument("--tts-device", choices=["auto", "cpu", "cuda"], help="Inference device")
    args = parser.parse_args()
    global SETTINGS
    SETTINGS = TtsSettings.from_sources(
        provider=args.tts,
        voice=args.voice,
        device=args.tts_device,
        reference=args.tts_ref,
    )
    days = dates_from_args(args)
    wanted = [args.office] if args.office else None
    print(
        f"generating {days[0].isoformat()} .. {days[-1].isoformat()} "
        f"({len(days)} day(s)) tts={SETTINGS.summary()}",
        flush=True,
    )
    if args.dry_run:
        for day in days:
            offices = offices_for(day)
            keys = wanted or list(offices)
            print(f"{day.isoformat()} {liturgical_day(day)['spoken']}", flush=True)
            for key in keys:
                office = offices[key]
                if not office["lessons"] and not office["psalms"]:
                    print(f"  {key}: no lessons", flush=True)
                elif already_recorded(day, key, office, args.force):
                    print(f"  {key}: already recorded", flush=True)
                else:
                    print(f"  {key}: would generate {office['filename']}", flush=True)
        print("dry-run done", flush=True)
        return
    require_ffmpeg()
    errors: list[str] = []
    for day in days:
        errors.extend(generate_day(day, wanted=wanted, force=args.force))
    if errors:
        print(f"finished with {len(errors)} error(s):", flush=True)
        for item in errors:
            print(f"  {item}", flush=True)
        raise SystemExit(1)
    print("done", flush=True)


if __name__ == "__main__":
    main()
