@echo off
setlocal

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Starting NEET PG Merger at http://127.0.0.1:5000
python app.py

pause
