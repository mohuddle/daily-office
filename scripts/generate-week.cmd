@echo off
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
if exist .venv\Scripts\python.exe (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=py -3.13
)
echo ===== %DATE% %TIME% =====>> logs\generate-week.log
%PY% scripts\generate_office_audio.py --week --tts qwen3 >> logs\generate-week.log 2>&1
exit /b %ERRORLEVEL%
