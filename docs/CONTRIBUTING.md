# Contributing to Daily Office

Static PWA in `web/` (vanilla HTML/JS/CSS, no framework, no bundler) plus standalone Python 3.10+ scripts in `scripts/` that generate its data and audio. Verify changes by serving the site (`python3 scripts/serve_lan.py` from repo root; serves `web/` on ports 8765 and 8080) and exercising the affected office/day.

```bash
python3 tests/test_safeio.py
```

## Deploy

Push to `master` deploys `web/` to GitHub Pages (`.github/workflows/pages.yml`). Only `web/` ships — `scripts/`, `data/`, `voices/` never reach the live site.

## Logic exists twice: Python and JS

The liturgical calendar and confession selection are deliberately duplicated so spoken audio matches the displayed text:

- Calendar: `scripts/liturgical.py` ↔ `web/js/liturgical.js`
- Confessions: `scripts/confession.py` ↔ `web/js/confession.js`

A change to one side must be mirrored in the other. All date logic is hardcoded to `America/Chicago` on both sides — keep it that way.

## Service worker cache

`web/sw.js` precaches a fixed file list under `CACHE = "daily-office-vN"`. Bump the version string whenever you change any precached file (JS, CSS, data JSON), or returning clients keep stale content. New data files must be added to the precache list too.

## Generated data files

Do not hand-edit these; regenerate instead:

- `web/data/bsb.json` — `python3 scripts/prepare_data.py` (downloads the BSB from bereanbible.com over HTTPS, size-capped)
- `web/data/confessions/*.json` — `python3 scripts/prepare_confessions.py`

Creed sources for the confession builder live in `data/creeds/` and the Dogmatika plan in `data/dogmatika-plan.txt`. Do not read those from `/tmp`.

Hand-maintained: `lectionary.json`, `midday.json`, `compline.json`, `sentences.json`.

File reads and writes in the Python scripts go through `scripts/safeio.py` (`O_NOFOLLOW`, size cap, atomic replace).

## Audio pipeline

- `scripts/generate_office_audio.py` synthesizes MP3s with Qwen3-TTS into `web/audio/` (gitignored — recordings stay local, not on Pages) and writes the index `web/data/audio.json`, which **is** committed.
- Requires ffmpeg and the heavy stack in `requirements-tts.txt`; Qwen is only practical on CUDA. Config (voice clone, speed, pronunciation hints) lives in `tts.json`; the reference WAV lives in `voices/` (gitignored).
- Existing MP3s are skipped unless `--force`. `--week` = Sunday on or after `--date` through Saturday; a single day does not use `--week`. Always try `--dry-run` first.
