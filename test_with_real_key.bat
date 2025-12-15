@echo off
REM Script de test OpenAI Vision avec une vraie cle API
REM Usage: Editer ce fichier et remplacer YOUR_KEY par votre cle, puis executer

echo ========================================
echo TEST OPENAI VISION - Configuration
echo ========================================
echo.

REM REMPLACER 'YOUR_KEY_HERE' par votre vraie cle OpenAI
set OPENAI_API_KEY=YOUR_KEY_HERE

if "%OPENAI_API_KEY%"=="YOUR_KEY_HERE" (
    echo [ERREUR] Vous devez d'abord editer ce fichier et mettre votre cle API !
    echo.
    echo 1. Ouvrir test_with_real_key.bat avec un editeur de texte
    echo 2. Remplacer YOUR_KEY_HERE par votre cle sk-...
    echo 3. Sauvegarder et relancer ce script
    echo.
    pause
    exit /b 1
)

echo [OK] Cle API configuree: %OPENAI_API_KEY:~0,10%...
echo.

REM Optionnel : Choisir le modele (gpt-4o ou gpt-4o-mini)
set OPENAI_MODEL=gpt-4o
echo [OK] Modele: %OPENAI_MODEL%
echo.

echo ========================================
echo TEST 1: Verification de l'integration
echo ========================================
python test_openai_simple.py

if errorlevel 1 (
    echo.
    echo [ERREUR] Le test a echoue
    pause
    exit /b 1
)

echo.
echo ========================================
echo TEST 2: Demarrer le serveur Django
echo ========================================
echo.
echo Le serveur va demarrer sur http://localhost:3001
echo Ouvrez votre navigateur sur http://localhost:8080/scan pour tester
echo.
echo Appuyez sur CTRL+C pour arreter le serveur
echo.
pause

python manage.py runserver 0.0.0.0:3001
