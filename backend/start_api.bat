@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting Clario FastAPI server on http://localhost:8000
echo Docs: http://localhost:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
