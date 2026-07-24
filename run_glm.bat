@echo off

cd /d "%~dp0"

if "%~1"=="" (

  echo Usage: run_glm.bat archive\freMTPL2freq.csv [optional: --sev archive\freMTPL2sev.csv]

  exit /b 1

)

python fremtpl_glm.py %*

