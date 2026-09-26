@echo off
chcp 65001 >nul
echo === Shorts Studio kurulumu ===
python --version >nul 2>&1
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org/downloads/ adresinden kurun
  echo ve kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
  pause
  exit /b 1
)
python -m pip install --upgrade pip
python -m pip install imageio-ffmpeg faster-whisper
echo.
echo Test: Almanca promptlar uretiliyor...
python studio.py prompts episodes\ep001_tomaten.json --lang de >nul && echo Kurulum tamam. Promptlar: out\ep001\flow_prompts_de.txt
pause
