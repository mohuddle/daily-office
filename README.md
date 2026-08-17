# Daily Office

A phone-friendly web app / PWA of daily Scripture lessons (Morning, Midday, Evening, Compline) with locally generated Qwen3-TTS audio.

## What this is

A first version that matches the existing daily-lessons workflow, not a full Book of Common Prayer app yet:

- **Morning / Evening** — psalms and lessons from *Daily Readings for the Christian Year* (The Trinity Mission)
- **Midday** — fixed Monday–Saturday cycle from the Trinity Mission midday lessons
- **Compline** — short weekly bedtime lessons (1928 BCP / traditional night-prayer texts)
- **Scripture** — Berean Standard Bible ([bsb.txt](https://bereanbible.com/bsb.txt))
- **Audio** — generated locally with [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) and an optional custom cloned voice. Generated MP3s are not stored in git.
- **Liturgical style** — traditional 1662 / 1928 / REC season names (Trinitytide from Trinity Sunday 31 May 2026; Advent begins 29 Nov 2026)
- **Daily confession** — Westminster in the morning; Heidelberg then Belgic cycling in the evening; a Confessional Echo when a morning or evening lesson overlaps the Reformed Dogmatika plan
- **Benediction** — after the daily confession, Morning and Evening close with a rotating 1662 / 1928 / scriptural blessing
- **Target** — static PWA that works on Linux, Windows 11, and phone, offline once loaded

v1 does **not** include full office prayers, canticles, creed, or collects.

## Prayer times (America/Chicago)

| Office   | Time  |
|----------|-------|
| Morning  | 07:30 |
| Midday   | 11:30 |
| Evening  | 17:30 |
| Compline | 22:00 |

## Data files

| File | Role |
|------|------|
| `web/data/lectionary.json` | 365 days keyed `MM-DD`: morning/evening psalms and lessons |
| `web/data/midday.json` | Fixed weekday midday lessons (no Sunday in the source card) |
| `web/data/compline.json` | Weekly compline lessons + classic fixed 1928 options |
| `web/data/sentences.json` | Rotating 1662/BSB opening sentences |
| `web/data/confessions/corpus.json` | WCF, WSC, WLC, Heidelberg, Belgic texts |
| `web/data/confessions/westminster_daily.json` | Morning calendar keyed `MM-DD` |
| `web/data/confessions/echoes.json` | Dogmatika Confessional Echo mappings |
| `web/data/confessions/benedictions.json` | Rotating 1662 / 1928 / scriptural benedictions |
| `data/Daily_Lectionary_Christian_Year.pdf` | Source lectionary tables |
| `data/Midday_Prayer_Lessons_Card.pdf` | Printable midday card |
| `data/morning_and_evening_sentences_bsb.md` | 1662 / BSB opening-sentence notes |

Sample lookup for 15 August (St. Mary):

```json
{
  "psalms_morning": "75–77",
  "psalms_evening": "78",
  "morning_lessons": ["Isa 61:10–11", "Luke 1:46–55"],
  "evening_lessons": ["Song 2:8–13", "John 19:25–27"],
  "liturgical_name": "St. Mary"
}
```

## Run the PWA

From the repo root:

```bash
python3 scripts/serve_lan.py --host 0.0.0.0 --ports 8765
```

Or, from `web/`:

```bash
python3 -m http.server 8765
```

Then open http://127.0.0.1:8765/ on this machine or your phone on the same network. It is installable from the browser and caches for offline use after the first load.

To keep it running on a Windows 11 PC after reboots, see [WINDOWS.md](WINDOWS.md). You do not need Grok Build on that machine.

Today (15 August 2026) shows Saturday in the week following the Tenth Sunday after Trinity, the feast of Saint Mary the Virgin.

## Audio

Office recordings are synthesized locally with **Qwen3-TTS** (1.7B, GPU) and an optional custom cloned voice (a short WAV you own in `voices/`). Settings live in `tts.json`. MP3s are written to `web/audio/` and are gitignored. Chatterbox remains an optional `--tts chatterbox` backend.

Each file starts with “Welcome to Morning Prayer” (or Midday, Evening, Compline), then the date and liturgical day. Morning and Evening then invite a four-second silence and read one rotating 1662/BSB opening sentence (`web/data/sentences.json`) before the psalms and lessons. Selah is spoken with a pause before and after. Every office ends with “The Word of the Lord. Thanks be to God.” Morning and Evening then pause, introduce the daily confession (“A reading from …”), read it, pause, and close with a rotating 1662 / 1928 / scriptural benediction. The player stays fixed at the bottom while you scroll.

## Daily confession

Morning uses the [Westminster Daily](https://reformedconfessions.com/westminster-daily/reading-plan) calendar (Shorter Catechism, Larger Catechism, and Confession of Faith by month-day). Evening reads Heidelberg Catechism Q1–129, then Belgic Confession Articles 1–37, then repeats that cycle by day of year.

If a morning or evening *lesson* (not the psalms) shares a chapter with a Confessional Echo in the [Reformed Dogmatika Bible Reading plan](https://reformeddogmatika.com/wp-content/uploads/2025/12/Reformed-Dogmatika-Bible-Reading-PREMIUM_HIRES.pdf), that echo replaces the sequential reading for that office. Canons of Dort and “Confessional Anchor — Belgic Confession” rows are skipped.

Rebuild the confession corpus, Westminster Daily calendar, and echo map with:

```bash
python3 scripts/prepare_confessions.py
```

Generate another day, or this Sunday through Saturday:

```bash
# Linux / macOS (Python 3.10+)
python3 -m pip install -r requirements-tts.txt
python3 scripts/generate_office_audio.py --week --dry-run
python3 scripts/generate_office_audio.py --week

# Windows 11 — use the venv
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tts.txt
.\.venv\Scripts\python.exe scripts\generate_office_audio.py --week --dry-run
.\.venv\Scripts\python.exe scripts\generate_office_audio.py --tts qwen3 --office compline --date 2026-08-15
.\.venv\Scripts\python.exe scripts\generate_office_audio.py --week

# Today's four offices only
scripts\generate-today.cmd
scripts\generate-today.cmd --force
```

`--week` starts on the Sunday on or after `--date` (default: today in America/Chicago) and records through Saturday. `scripts\generate-today.cmd` records only today. Existing MP3s are skipped unless you pass `--force`. ffmpeg is required. On Windows see [WINDOWS.md](WINDOWS.md).

Refresh the Berean Standard Bible text:

```bash
python3 scripts/prepare_data.py
```

## Credits and inspiration

This is a small Daily Office app. It is not affiliated with the projects below. Their work guided the lectionary, the phone-friendly reading layout, and the confession plan:

- [The Trinity Mission](https://thetrinitymission.org/) — *Daily Readings for the Christian Year* and the midday prayer card, which supply the morning, evening, and midday lessons
- [Daily Office 2019](https://www.dailyoffice2019.com/) — a clear, usable modern office that helped set the aim of this app
- [Daily Office For All](https://dailyofficeforall.com/) — appearance, seasonal color, and a simple reading layout we learned from
- [Westminster Daily](https://reformedconfessions.com/westminster-daily/reading-plan) — the morning calendar through the Westminster Standards
- [Reformed Dogmatika Bible Reading Plan](https://reformeddogmatika.com/reformed-bible-reading-plan/) — Confessional Echo pairings used when our lessons overlap that plan
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — local office recordings
- [Chatterbox](https://github.com/resemble-ai/chatterbox) by Resemble AI — optional alternate local backend

Scripture text is the [Berean Standard Bible](https://bereanbible.com/).
