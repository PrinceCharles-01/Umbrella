@echo off
echo Installation des dependances dans le venv...
cd /d "%~dp0"
venv\Scripts\pip.exe install -r requirements.txt
echo.
echo Terminé !
pause
