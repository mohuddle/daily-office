@echo off
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
if exist .venv\Scripts\python.exe (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=py -3.13
)
echo ===== %DATE% %TIME% today =====>> logs\generate-today.log
%PY% scripts\generate_office_audio.py --tts qwen3 %* >> logs\generate-today.log 2>&1
exit /b %ERRORLEVEL%
