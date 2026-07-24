@echo off
cd /d "%~dp0"
echo Starting AIC CT Flex product API on http://127.0.0.1:8000
echo   Docs: http://127.0.0.1:8000/docs
echo.
".venv\Scripts\python.exe" ct_flex_api.py --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo venv python not found — trying system python...
  python ct_flex_api.py --host 127.0.0.1 --port 8000
)
