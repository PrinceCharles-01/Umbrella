@echo off
REM IMPORTANT: Definissez votre cle API dans les variables d'environnement ou modifiez cette ligne
REM set OPENAI_API_KEY=votre-cle-openai-ici
if not defined OPENAI_API_KEY (
    echo ERREUR: Variable OPENAI_API_KEY non definie
    echo Modifiez ce fichier ou definissez la variable d'environnement
    pause
    exit /b 1
)
python test_openai_quick.py
