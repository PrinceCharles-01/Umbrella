@echo off
echo ========================================
echo DEMARRAGE UMBRELLA avec OpenAI Vision
echo ========================================
echo.

REM Configuration de la cle OpenAI
REM IMPORTANT: Definissez votre cle API dans les variables d'environnement ou modifiez cette ligne
REM set OPENAI_API_KEY=votre-cle-openai-ici
if not defined OPENAI_API_KEY (
    echo ERREUR: Variable OPENAI_API_KEY non definie
    echo Modifiez ce fichier ou definissez la variable d'environnement
    pause
    exit /b 1
)

echo [OK] Cle OpenAI configuree
echo [OK] Modele: GPT-4o
echo.
echo ========================================
echo Demarrage du serveur Django...
echo ========================================
echo.
echo Le serveur va demarrer sur http://localhost:3001
echo.
echo Ouvrez votre navigateur sur:
echo   http://localhost:8080/scan
echo.
echo Appuyez sur CTRL+C pour arreter
echo.

cd /d "%~dp0"
python manage.py runserver 0.0.0.0:3001
