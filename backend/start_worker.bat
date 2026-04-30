@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting Clario Celery worker (solo pool for Windows)...
echo.
celery -A app.tasks.celery_app.celery_app worker --loglevel=info --pool=solo
