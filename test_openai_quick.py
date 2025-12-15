#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test rapide OpenAI Vision avec une vraie cle API
"""
import os
import sys

# Verifier que la cle API est definie
api_key = os.environ.get('OPENAI_API_KEY', '')

if not api_key or api_key == 'YOUR_KEY_HERE':
    print("\n" + "="*70)
    print("ERREUR: OPENAI_API_KEY non configuree")
    print("="*70)
    print("\nPour configurer votre cle:")
    print("  Windows: set OPENAI_API_KEY=sk-votre-cle")
    print("  Linux:   export OPENAI_API_KEY=sk-votre-cle")
    print("\nOu editez test_with_real_key.bat et executez-le")
    print("="*70 + "\n")
    sys.exit(1)

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')

import django
django.setup()

from api.services import OCRServiceOpenAI
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
import io

print("\n" + "="*70)
print("TEST OPENAI VISION - AVEC VRAIE CLE API")
print("="*70)

# Infos de config
model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')
print(f"\nConfiguration:")
print(f"  Cle API: {api_key[:10]}...{api_key[-4:]}")
print(f"  Modele:  {model}")
print(f"  Mode:    {getattr(settings, 'GOOGLE_VISION_MODE', 'mock')}")

# Creer le service OpenAI
print("\n" + "-"*70)
print("Initialisation du service OpenAI...")
print("-"*70)

try:
    service = OCRServiceOpenAI(api_key, model=model)
    print("[OK] Service initialise avec succes")
except Exception as e:
    print(f"[ERREUR] Impossible d'initialiser le service: {e}")
    sys.exit(1)

# Creer une image de test avec du texte
print("\n" + "-"*70)
print("Creation d'une image de test avec texte...")
print("-"*70)

# Image blanche avec du texte
img = Image.new('RGB', (600, 400), color='white')
draw = ImageDraw.Draw(img)

# Texte de l'ordonnance simulee
ordonnance_text = """
    ORDONNANCE MEDICALE

    Dr. NGUEMA Jean
    Medecin Generaliste
    Libreville, Gabon

    Patient: M. MBEMBA
    Date: 02/12/2025

    DOLIPRANE 1000mg
    1 comprime matin et soir
    Pendant 5 jours

    AMOXICILLINE 500mg
    3 fois par jour
    Pendant 7 jours
"""

# Dessiner le texte (police par defaut)
y_position = 20
for line in ordonnance_text.strip().split('\n'):
    draw.text((20, y_position), line.strip(), fill='black')
    y_position += 25

# Convertir en bytes
img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
img_bytes = img_bytes.getvalue()

print(f"[OK] Image creee: {len(img_bytes)} bytes (PNG 600x400)")

# Test de l'extraction OCR
print("\n" + "-"*70)
print("APPEL A OPENAI VISION API...")
print("-"*70)
print(f"Modele: {model}")
print("Envoi de l'image... (cela peut prendre 2-5 secondes)")
print()

try:
    text = service.extract_text_from_image(img_bytes)

    print("\n" + "="*70)
    print("RESULTAT DE L'EXTRACTION OCR")
    print("="*70)
    print(f"\nTexte extrait ({len(text)} caracteres):\n")
    print("-"*70)
    print(text)
    print("-"*70)

    # Verifier que des mots cles sont presents
    keywords = ['doliprane', 'amoxicilline', '1000mg', '500mg']
    found = [kw for kw in keywords if kw.lower() in text.lower()]

    print(f"\nMots-cles trouves: {found}")

    if len(found) >= 2:
        print("\n[OK] L'OCR fonctionne correctement !")
    else:
        print("\n[WARNING] Peu de mots-cles detectes, verifiez la qualite")

    print("\n" + "="*70)
    print("TEST TERMINE AVEC SUCCES")
    print("="*70)
    print("\nProchaines etapes:")
    print("  1. Testez avec une vraie photo d'ordonnance")
    print("  2. Lancez le serveur: python manage.py runserver 0.0.0.0:3001")
    print("  3. Allez sur: http://localhost:8080/scan")
    print("="*70 + "\n")

except Exception as e:
    print("\n" + "="*70)
    print("ERREUR LORS DE L'APPEL API")
    print("="*70)
    print(f"\nErreur: {str(e)}")
    print("\nCauses possibles:")
    print("  - Cle API invalide ou expiree")
    print("  - Quota depasse")
    print("  - Probleme de connexion internet")
    print("  - Modele non disponible")
    print("\nVerifiez sur: https://platform.openai.com/")
    print("="*70 + "\n")
    sys.exit(1)
