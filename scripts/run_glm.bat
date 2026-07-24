@echo off

cd /d "%~dp0\.."

if "%~1"=="" (

  echo Usage: scripts\run_glm.bat archive\freMTPL2freq.csv [optional: --sev ...]

  exit /b 1

)

python fremtpl_glm.py %*


