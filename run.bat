@echo off
cd /d "%~dp0"
echo Checking Python dependencies...
python -c "import pdfplumber" 2>nul
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install dependencies. Please run: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo Loading job feed (first fetch may take ~15s)...
python scripts\refresh_jobs_cache.py

echo Starting FresherFlow — jobs refresh automatically every 2 hours while this runs.
python scripts\serve.py
pause
