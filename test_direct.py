#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test direct avec cle API en dur"""
import os
import sys

# Definir la cle AVANT d'importer Django
# IMPORTANT: Définissez OPENAI_API_KEY dans votre environnement
if not os.environ.get('OPENAI_API_KEY'):
    print("ERREUR: Variable d'environnement OPENAI_API_KEY non définie")
    print("Utilisez: set OPENAI_API_KEY=votre-clé (Windows) ou export OPENAI_API_KEY=votre-clé (Linux/Mac)")
    sys.exit(1)

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')

import django
django.setup()

from api.services import OCRServiceOpenAI
from django.conf import settings
from PIL import Image, ImageDraw
import io

print("\n" + "="*70)
print("TEST OPENAI VISION - GPT-4o")
print("="*70)

api_key = os.environ.get('OPENAI_API_KEY', '')
model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')

print(f"\nConfiguration:")
print(f"  Cle API: {api_key[:10]}...{api_key[-4:]}")
print(f"  Modele:  {model}")

# Creer le service
print("\n" + "-"*70)
print("Initialisation OCRServiceOpenAI...")
print("-"*70)

try:
    service = OCRServiceOpenAI(api_key, model=model)
    print("[OK] Service initialise")
except Exception as e:
    print(f"[ERREUR] {e}")
    sys.exit(1)

# Creer une image de test
print("\n" + "-"*70)
print("Creation image de test...")
print("-"*70)

img = Image.new('RGB', (600, 400), color='white')
draw = ImageDraw.Draw(img)

ordonnance = """
    ORDONNANCE MEDICALE

    Dr. NGUEMA Jean
    Libreville, Gabon
    02/12/2025

    DOLIPRANE 1000mg
    1 comprime matin et soir
    Pendant 5 jours

    AMOXICILLINE 500mg
    3 fois par jour
    Pendant 7 jours
"""

y = 20
for line in ordonnance.strip().split('\n'):
    draw.text((20, y), line.strip(), fill='black')
    y += 25

img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
img_bytes = img_bytes.getvalue()

print(f"[OK] Image creee: {len(img_bytes)} bytes")

# Test OCR
print("\n" + "-"*70)
print("APPEL A OPENAI VISION API (GPT-4o)...")
print("-"*70)
print("Envoi de l'image... (peut prendre 3-5 secondes)")

try:
    text = service.extract_text_from_image(img_bytes)

    print("\n" + "="*70)
    print("RESULTAT OCR")
    print("="*70)
    print(f"\nTexte extrait ({len(text)} caracteres):\n")
    print(text)
    print("\n" + "="*70)

    # Verifier mots-cles
    keywords = ['doliprane', 'amoxicilline', '1000', '500']
    found = [k for k in keywords if k.lower() in text.lower()]

    print(f"\nMots-cles detectes: {found}")

    if len(found) >= 3:
        print("\n[SUCCES] OpenAI Vision fonctionne parfaitement !")
        print("\nProchaines etapes:")
        print("  1. Testez avec une vraie photo d'ordonnance")
        print("  2. Comparez la qualite avec le mode Mock")
        print("  3. Lancez: python manage.py runserver 0.0.0.0:3001")
    else:
        print("\n[WARNING] Peu de mots detectes")

    print("="*70 + "\n")

except Exception as e:
    print("\n" + "="*70)
    print("ERREUR API")
    print("="*70)
    print(f"\n{type(e).__name__}: {str(e)}\n")

    import traceback
    traceback.print_exc()

    print("\nCauses possibles:")
    print("  - Cle API invalide")
    print("  - Quota depasse")
    print("  - Modele non disponible")
    print("\nVerifiez: https://platform.openai.com/")
    print("="*70 + "\n")
    sys.exit(1)
