@echo off

cd /d "%~dp0"

python -m pytest test_engine_model.py test_fremtpl_glm.py -v

if errorlevel 1 (

  python test_engine_model.py -v

  python test_fremtpl_glm.py -v

)

