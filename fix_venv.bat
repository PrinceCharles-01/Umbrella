@echo off
echo ========================================
echo Installation des packages dans le venv
echo ========================================
cd /d "%~dp0"

echo.
echo Installation de google-cloud-vision...
venv\Scripts\python.exe -m pip install google-cloud-vision

echo.
echo Installation de openai...
venv\Scripts\python.exe -m pip install openai

echo.
echo Installation de toutes les dependances...
venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo ========================================
echo TERMINE !
echo ========================================
echo.
echo Vous pouvez maintenant lancer:
echo   python manage.py runserver 0.0.0.0:3001
echo.
pause
