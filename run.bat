@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo -^> Creating Python virtual environment ...
    py -3.13 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python 3.13 was not found. Install Python 3.13 and rerun run.bat.
        exit /b 1
    )
    if errorlevel 1 exit /b 1
)

set "PYTHON=%CD%\.venv\Scripts\python.exe"

for /f "usebackq delims=" %%V in (`"%PYTHON%" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"`) do set "PY_VERSION=%%V"
if not "%PY_VERSION%"=="3.13" (
    echo ERROR: .venv is using Python %PY_VERSION%, but this project is configured for Python 3.13.
    echo Move or remove .venv, then rerun run.bat to recreate it with Python 3.13.
    exit /b 1
)

echo -^> Installing Python package from %CD% ...
"%PYTHON%" -m pip install -e ".[dev]" -q
if errorlevel 1 exit /b 1

where npm >nul 2>nul
if errorlevel 1 (
    echo ERROR: npm was not found. Install Node.js 20 LTS or newer to use the BDE scraper.
    exit /b 1
)

echo -^> Installing BDE scraper runtime dependencies ...
"%PYTHON%" -m bde_xbrl_editor.taxonomy_catalog.scraper --setup-only
if errorlevel 1 exit /b 1

echo -^> Clearing stale pycache ...
for /d /r "src" %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D"

echo -^> Launching BDE XBRL Editor ...
"%PYTHON%" -m bde_xbrl_editor

endlocal
