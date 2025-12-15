#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test avec nouvelle cle OpenAI"""
import os
import sys

# Cle API OpenAI - A definir dans les variables d'environnement
# IMPORTANT: Définissez OPENAI_API_KEY dans votre environnement
if not os.environ.get('OPENAI_API_KEY'):
    print("ERREUR: Variable d'environnement OPENAI_API_KEY non définie")
    print("Utilisez: set OPENAI_API_KEY=votre-clé (Windows) ou export OPENAI_API_KEY=votre-clé (Linux/Mac)")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')

import django
django.setup()

from api.services import OCRServiceOpenAI
from django.conf import settings
from PIL import Image, ImageDraw
import io
import time

print("\n" + "="*70)
print("TEST OPENAI VISION OCR - GPT-4o")
print("="*70)

api_key = os.environ.get('OPENAI_API_KEY', '')
model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')

print(f"\nConfiguration:")
print(f"  Cle API: {api_key[:15]}...{api_key[-6:]}")
print(f"  Modele:  {model}")

# Initialiser le service
print("\n" + "-"*70)
print("1. Initialisation OCRServiceOpenAI")
print("-"*70)

try:
    service = OCRServiceOpenAI(api_key, model=model)
    print("[OK] Service initialise avec succes")
except Exception as e:
    print(f"[ERREUR] {e}")
    sys.exit(1)

# Creer une image de test avec texte d'ordonnance
print("\n" + "-"*70)
print("2. Creation d'une image de test (ordonnance simulee)")
print("-"*70)

img = Image.new('RGB', (700, 500), color='white')
draw = ImageDraw.Draw(img)

ordonnance_text = """
        ORDONNANCE MEDICALE

        Dr. Jean NGUEMA
        Medecin Generaliste
        Centre Medical de Libreville
        Gabon

        Patient: M. MBEMBA Pierre
        Date: 02 decembre 2025

        DOLIPRANE 1000mg
        1 comprime matin et soir
        Pendant 5 jours

        AMOXICILLINE 500mg
        1 gelule 3 fois par jour
        Pendant 7 jours

        EFFERALGAN 500mg
        En cas de douleur
        Maximum 3 par jour
"""

y_pos = 30
for line in ordonnance_text.strip().split('\n'):
    draw.text((30, y_pos), line.strip(), fill='black')
    y_pos += 28

img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
img_bytes = img_bytes.getvalue()

print(f"[OK] Image creee: {len(img_bytes)} bytes (PNG 700x500)")
print(f"[OK] Contenu: Ordonnance avec DOLIPRANE, AMOXICILLINE, EFFERALGAN")

# Test OCR avec OpenAI Vision
print("\n" + "-"*70)
print("3. APPEL A OPENAI VISION API")
print("-"*70)
print(f"Modele: {model}")
print("Envoi de l'image a GPT-4o...")
print("(Cela peut prendre 3-5 secondes)")

start_time = time.time()

try:
    text = service.extract_text_from_image(img_bytes)
    elapsed = time.time() - start_time

    print(f"\n[OK] Reponse recue en {elapsed:.2f} secondes")

    print("\n" + "="*70)
    print("RESULTAT DE L'EXTRACTION OCR")
    print("="*70)
    print(f"\nTexte extrait ({len(text)} caracteres):\n")
    print("-"*70)
    print(text)
    print("-"*70)

    # Analyser le resultat
    print("\n" + "-"*70)
    print("4. ANALYSE DU RESULTAT")
    print("-"*70)

    keywords = {
        'doliprane': False,
        'amoxicilline': False,
        'efferalgan': False,
        '1000': False,
        '500': False,
        'matin': False,
        'soir': False,
        '3 fois': False
    }

    text_lower = text.lower()
    for keyword in keywords:
        if keyword in text_lower:
            keywords[keyword] = True
            print(f"[OK] '{keyword}' detecte")
        else:
            print(f"[--] '{keyword}' non detecte")

    found_count = sum(keywords.values())
    total_count = len(keywords)

    print(f"\nScore: {found_count}/{total_count} mots-cles detectes")

    # Verdict
    print("\n" + "="*70)
    if found_count >= 6:
        print("RESULTAT: EXCELLENT !")
        print("="*70)
        print("\nOpenAI Vision fonctionne parfaitement !")
        print("L'OCR a correctement extrait les informations de l'ordonnance.")
    elif found_count >= 4:
        print("RESULTAT: BON")
        print("="*70)
        print("\nOpenAI Vision fonctionne bien.")
        print("La plupart des informations ont ete extraites.")
    else:
        print("RESULTAT: MOYEN")
        print("="*70)
        print("\nCertaines informations n'ont pas ete detectees.")

    print("\n" + "="*70)
    print("PROCHAINES ETAPES")
    print("="*70)
    print("\n1. Testez avec une VRAIE photo d'ordonnance")
    print("   - Prenez une photo d'ordonnance avec votre telephone")
    print("   - Lancez le serveur: python manage.py runserver 0.0.0.0:3001")
    print("   - Allez sur: http://localhost:8080/scan")
    print("   - Uploadez la photo")
    print("\n2. Comparez la qualite avec le mode Mock")
    print("\n3. Verifiez vos couts sur: https://platform.openai.com/usage")
    print("   - Cout estime de ce test: ~$0.002 (0.2 cents)")
    print("="*70 + "\n")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n[ERREUR] Echec apres {elapsed:.2f} secondes")
    print("\n" + "="*70)
    print("ERREUR API OPENAI")
    print("="*70)
    print(f"\n{type(e).__name__}: {str(e)}\n")

    if "insufficient_quota" in str(e):
        print("CAUSE: Quota depasse")
        print("  - Le compte n'a plus de credit")
        print("  - Verifiez: https://platform.openai.com/usage")
    elif "invalid_api_key" in str(e):
        print("CAUSE: Cle API invalide")
        print("  - Verifiez que la cle est correcte")
    elif "rate_limit" in str(e):
        print("CAUSE: Trop de requetes")
        print("  - Attendez quelques secondes et reessayez")
    else:
        print("CAUSE: Erreur inconnue")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")
    sys.exit(1)
