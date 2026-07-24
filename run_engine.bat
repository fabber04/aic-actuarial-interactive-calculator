@echo off

cd /d "%~dp0"

if "%~1"=="" (

  echo Demo: Brown and Gottlieb sample output

  python engine_model.py

) else (

  python engine_model.py %*

)

