#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script pour démarrer le serveur Django avec OpenAI configuré"""
import os
import sys

# Configurer la clé OpenAI depuis les variables d'environnement
# Définissez OPENAI_API_KEY dans votre environnement avant d'exécuter ce script
if not os.environ.get('OPENAI_API_KEY'):
    print("ERREUR: Variable d'environnement OPENAI_API_KEY non définie")
    print("Utilisez: set OPENAI_API_KEY=votre-clé (Windows) ou export OPENAI_API_KEY=votre-clé (Linux/Mac)")
    sys.exit(1)
os.environ.setdefault('OPENAI_MODEL', 'gpt-4o')

print("========================================")
print("DEMARRAGE UMBRELLA avec OpenAI Vision")
print("========================================")
print()
print("[OK] Clé OpenAI configurée")
print("[OK] Modèle: GPT-4o")
print()
print("Le serveur va démarrer sur http://localhost:3001")
print()
print("Ouvrez votre navigateur sur:")
print("  http://localhost:8080/scan")
print()
print("Appuyez sur CTRL+C pour arrêter")
print()

# Démarrer Django
os.system('python manage.py runserver 0.0.0.0:3001')
