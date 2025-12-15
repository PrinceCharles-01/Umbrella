#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test simple pour OpenAI Vision OCR
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')
django.setup()

from api.services import OCRServiceOpenAI, PrescriptionProcessor
from django.conf import settings
from PIL import Image
import io


def main():
    print("\n" + "="*70)
    print("TEST INTEGRATION OPENAI VISION OCR")
    print("="*70)

    # Verifier la configuration
    mode = getattr(settings, 'GOOGLE_VISION_MODE', 'mock')
    openai_key = os.environ.get('OPENAI_API_KEY', '')

    print(f"\nMode OCR: {mode}")
    print(f"OPENAI_API_KEY: {'Definie' if openai_key else 'NON definie'}")

    if not openai_key:
        print("\n[!] OPENAI_API_KEY non definie")
        print("\nPour tester OpenAI Vision:")
        print("  Windows: set OPENAI_API_KEY=sk-...")
        print("  Linux:   export OPENAI_API_KEY=sk-...")
        print("\nObtenir une cle: https://platform.openai.com/api-keys")
        print("\n[!] Mode Mock utilise par defaut")
        return

    # Test du service OpenAI
    print("\n" + "-"*70)
    print("Test 1: Service OCRServiceOpenAI")
    print("-"*70)

    try:
        service = OCRServiceOpenAI(openai_key)
        print("[OK] Service initialise")

        # Creer une image de test
        img = Image.new('RGB', (400, 200), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        print(f"[OK] Image de test creee: {len(img_bytes)} bytes")

        # Tester l'extraction
        print("[...] Appel a OpenAI Vision API...")
        text = service.extract_text_from_image(img_bytes)
        print(f"[OK] Texte extrait: {len(text)} caracteres")
        if text:
            print(f"      Preview: {text[:100]}")

    except Exception as e:
        print(f"[ERREUR] {str(e)}")
        return

    # Test du PrescriptionProcessor
    print("\n" + "-"*70)
    print("Test 2: PrescriptionProcessor avec mode OpenAI")
    print("-"*70)

    try:
        processor = PrescriptionProcessor()
        print(f"[OK] Processor cree: {type(processor.ocr_service).__name__}")

        # Test complet
        print("[...] Traitement d'une ordonnance de test...")
        result = processor.process_prescription(img_bytes)

        print(f"[OK] Traitement termine")
        print(f"     Success: {result.get('success')}")
        print(f"     Texte: {len(result.get('text_detected', ''))} caracteres")
        print(f"     Medicaments: {len(result.get('medications', []))}")

        if result.get('error'):
            print(f"     Erreur: {result.get('error')}")

    except Exception as e:
        print(f"[ERREUR] {str(e)}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*70)
    print("TESTS TERMINES")
    print("="*70)
    print("\nOpenAI Vision est pret! Prochaines etapes:")
    print("  1. Testez avec une vraie image d'ordonnance")
    print("  2. Comparez la qualite vs mode Mock")
    print("  3. Verifiez les couts sur: https://platform.openai.com/usage")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
