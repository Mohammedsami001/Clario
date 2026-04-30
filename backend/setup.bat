@echo off
echo ============================================================
echo  Clario — Backend Setup Script
echo ============================================================

cd /d "%~dp0"

echo.
echo [1/4] Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo [2/4] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/4] Installing dependencies...
pip install -r requirements.txt

echo.
echo [4/4] Installing faster-whisper CUDA (for RTX 3050)...
pip install ctranslate2 --upgrade

echo.
echo ============================================================
echo  Setup complete!
echo  Next: run start_api.bat in one terminal
echo        run start_worker.bat in another terminal
echo ============================================================
pause
