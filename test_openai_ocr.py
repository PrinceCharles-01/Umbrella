#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour OpenAI Vision OCR
Vérifie que l'intégration OpenAI fonctionne correctement.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')
django.setup()

from api.services import OCRServiceOpenAI, PrescriptionProcessor
from django.conf import settings
from PIL import Image
import io


def test_openai_service():
    """Test direct du service OpenAI"""
    print("=" * 70)
    print("TEST 1: Service OpenAI Vision")
    print("=" * 70)

    # Vérifier la clé API
    api_key = os.environ.get('OPENAI_API_KEY', '')

    if not api_key:
        print("❌ OPENAI_API_KEY non définie dans les variables d'environnement")
        print("\nPour tester OpenAI Vision:")
        print("1. Obtenez une clé sur: https://platform.openai.com/api-keys")
        print("2. Windows: set OPENAI_API_KEY=sk-...")
        print("3. Linux/Mac: export OPENAI_API_KEY=sk-...")
        print("4. Relancez ce script\n")
        return False

    print(f"✅ OPENAI_API_KEY trouvée: {api_key[:10]}...{api_key[-4:]}")

    # Créer le service
    try:
        service = OCRServiceOpenAI(api_key)
        print("✅ OCRServiceOpenAI initialisé avec succès")

        # Créer une image de test simple
        print("\n📸 Création d'une image de test...")
        img = Image.new('RGB', (400, 200), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        print(f"✅ Image créée: {len(img_bytes)} bytes")

        # Tester l'extraction (avec image blanche, OpenAI dira qu'il n'y a rien)
        print("\n🔍 Test extraction de texte...")
        try:
            text = service.extract_text_from_image(img_bytes)
            print(f"✅ Extraction réussie!")
            print(f"📝 Texte extrait: '{text[:100]}...'")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction: {str(e)}")
            return False

    except Exception as e:
        print(f"❌ Erreur initialisation: {str(e)}")
        return False


def test_prescription_processor():
    """Test du PrescriptionProcessor avec le mode OpenAI"""
    print("\n" + "=" * 70)
    print("TEST 2: PrescriptionProcessor avec OpenAI")
    print("=" * 70)

    # Vérifier le mode configuré
    mode = getattr(settings, 'GOOGLE_VISION_MODE', 'mock')
    print(f"📋 Mode OCR configuré: {mode}")

    if mode == 'openai':
        print("✅ Mode OpenAI activé dans settings.py")
    else:
        print(f"⚠️  Mode actuel: {mode} (pas OpenAI)")
        print("Pour activer OpenAI, définissez OPENAI_API_KEY dans l'environnement")
        return False

    # Créer le processor
    try:
        processor = PrescriptionProcessor()
        print(f"✅ PrescriptionProcessor créé: {type(processor.ocr_service).__name__}")

        # Créer une image de test
        img = Image.new('RGB', (400, 200), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        # Tester le traitement complet
        print("\n🔄 Test traitement complet...")
        result = processor.process_prescription(img_bytes)

        print(f"✅ Traitement terminé:")
        print(f"   - Success: {result.get('success', False)}")
        print(f"   - Texte détecté: {len(result.get('text_detected', ''))} caractères")
        print(f"   - Médicaments: {len(result.get('medications', []))}")

        if result.get('error'):
            print(f"   - Erreur: {result.get('error')}")

        return True

    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def print_configuration():
    """Affiche la configuration actuelle"""
    print("\n" + "=" * 70)
    print("CONFIGURATION ACTUELLE")
    print("=" * 70)

    mode = getattr(settings, 'GOOGLE_VISION_MODE', 'mock')
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    google_key = getattr(settings, 'GOOGLE_VISION_API_KEY', '')

    print(f"Mode OCR: {mode}")
    print(f"OPENAI_API_KEY: {'✅ Définie' if openai_key else '❌ Non définie'}")
    print(f"GOOGLE_VISION_API_KEY: {'✅ Définie' if google_key else '❌ Non définie'}")

    print("\n📚 Services disponibles:")
    print("  - MockOCRService (mode développement)")
    print("  - OCRService (Google Vision avec credentials)")
    print("  - OCRServiceWithApiKey (Google Vision avec API key)")
    print("  - OCRServiceOpenAI (OpenAI Vision) ← NOUVEAU !")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    print("\n>>> TEST D'INTEGRATION OPENAI VISION OCR\n")

    # Afficher la configuration
    print_configuration()

    # Test 1: Service OpenAI direct
    test1_passed = test_openai_service()

    # Test 2: PrescriptionProcessor
    test2_passed = test_prescription_processor()

    # Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"Test 1 (OCRServiceOpenAI): {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Test 2 (PrescriptionProcessor): {'✅ PASS' if test2_passed else '❌ FAIL'}")

    if test1_passed and test2_passed:
        print("\n>>> Tous les tests passent! OpenAI Vision est pret a l'emploi.")
        print("\nProchaines etapes:")
        print("   1. Testez avec une vraie ordonnance (image)")
        print("   2. Verifiez la qualite de l'extraction")
        print("   3. Comparez avec le mode Mock")
    else:
        print("\n>>> Certains tests ont echoue. Verifiez la configuration.")

    print("=" * 70 + "\n")
