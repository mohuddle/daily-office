# Windows 11 LAN server

Serve the Daily Office on your LAN so phones and PCs can open it. The site is the `web` folder. You do not need Grok Build.

Do not port-forward the office on your router. Keep it on the private network only.

## 1. Put the files on the PC

Clone or copy this repo to a stable path, for example `C:\DailyOffice`.

```powershell
git clone https://github.com/mohuddle/daily-office.git C:\DailyOffice
```

## 2. Install Python

Install [Python 3.10 or newer](https://www.python.org/downloads/windows/). On the installer, check **Add python.exe to PATH**. Python 3.13 works well (`py -3.13`). An older `python` 3.9 on PATH cannot run the local TTS stack.

Confirm in PowerShell:

```powershell
py -3.13 --version
```

## 3. Try it once

From the repo root:

```powershell
cd C:\DailyOffice
py -3.13 scripts\serve_lan.py --host 0.0.0.0 --ports 8765
```

On this PC open http://127.0.0.1:8765/

On a phone on the same Wi‑Fi, open `http://<this-pc-ipv4>:8765/`

Find the PC address with:

```powershell
ipconfig
```

Use the IPv4 address of the active Ethernet or Wi‑Fi adapter (often `192.168.1.x`).

Stop the test server with Ctrl+C.

## 4. Allow the port on the Private network

1. Open **Windows Defender Firewall** → **Advanced settings** → **Inbound Rules** → **New Rule…**
2. Port → TCP → **8765**
3. Allow the connection
4. Check **Private** only. Leave Domain and Public unchecked.
5. Name it `Daily Office LAN`

## 5. Start at boot with Task Scheduler

1. Open **Task Scheduler** → **Create Task…** (not Create Basic Task).
2. **General**
   - Name: `Daily Office LAN`
   - **Run whether user is logged on or not**
   - **Run with highest privileges** can stay off
   - Configure for: Windows 10
3. **Triggers** → New → **At startup** → OK
4. **Actions** → New
   - Program/script: `C:\DailyOffice\.venv\Scripts\python.exe` (or `py` if you are not using a venv yet)
   - Add arguments: `scripts\serve_lan.py --host 0.0.0.0 --ports 8765`
   - Start in: `C:\DailyOffice`
5. **Conditions**
   - Uncheck **Start the task only if the computer is on AC power** if this is a desktop you want up after outages
6. **Settings**
   - Check **If the task fails, restart every** `1 minute`
   - Uncheck **Stop the task if it runs longer than**
7. OK. Windows may ask for your account password so it can run at startup.

Reboot once and confirm http://127.0.0.1:8765/ still loads before anyone is signed in.

## 6. Optional second port

`serve_lan.py` can listen on more than one port:

```powershell
.\.venv\Scripts\python.exe scripts\serve_lan.py --host 0.0.0.0 --ports 8765,8080
```

Add a matching firewall rule for 8080 if you use it.

## 7. Office recordings (Qwen3-TTS)

The website does not record itself. Generate audio locally with **Qwen3-TTS** and, optionally, a custom cloned voice (a short WAV you own, set as `reference` in `tts.json`). No paid TTS API is required.

1. Install [ffmpeg](https://www.gyan.dev/ffmpeg/builds/) and add it to PATH. In a new PowerShell window:

```powershell
ffmpeg -version
```

2. Create the venv and install the TTS stack (once):

```powershell
cd C:\DailyOffice
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tts.txt
```

Use this venv. That install also includes `tzdata`; Windows Python has no timezone database. A CUDA GPU (float16) is what makes Qwen practical.

3. Generate today, or the whole week:

```powershell
cd C:\DailyOffice
scripts\generate-today.cmd
scripts\generate-today.cmd --force
.\.venv\Scripts\python.exe scripts\generate_office_audio.py --week --dry-run
.\.venv\Scripts\python.exe scripts\generate_office_audio.py --week
```

`generate-today.cmd` records Morning, Midday, Evening, and Compline for today in America/Chicago. A single day does **not** use `--week`. `--week` is Sunday on or after `--date` through Saturday. Generated MP3s stay in `web\audio\` and are not committed. Already-made days are skipped unless you pass `--force`.

4. Task Scheduler → **Create Task…**
   - Name: `Daily Office weekly audio`
   - **Run whether user is logged on or not**
   - **Triggers** → New → **Weekly** → Sunday → `6:00:00 AM`
   - **Actions** → New
     - Program/script: `C:\DailyOffice\scripts\generate-week.cmd`
     - Start in: `C:\DailyOffice`
   - **Settings**
     - Check **Run task as soon as possible after a scheduled start is missed**
     - Uncheck **Stop the task if it runs longer than**
     - Check **If the task fails, restart every** `10 minutes`, up to 3 times

Already-made days are skipped, so a rerun only fills gaps. Log: `logs\generate-week.log`.

## Updating later

```powershell
cd C:\DailyOffice
git pull
```

Then restart the LAN task: Task Scheduler → Daily Office LAN → **End** → **Run**. The PWA files update immediately. Phones may need a refresh to leave an old service-worker cache. Generated MP3s in `web\audio\` are local and will not come from GitHub.
