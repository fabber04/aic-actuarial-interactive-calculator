@echo off

cd /d "%~dp0\.."

python -m pytest tests -v

if errorlevel 1 (

  python -m unittest discover -s tests -v

)


