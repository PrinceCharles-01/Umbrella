# -*- coding: utf-8 -*-
"""
Script de test batch pour l'OCR.
Permet de tester plusieurs ordonnances et générer un rapport complet.

Usage:
    python test_ocr_batch.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')
django.setup()

from api.services import PrescriptionProcessor
from api.ocr_logger import test_reporter, scan_logger
import time


# =============================================================================
# TESTS À EXÉCUTER
# =============================================================================
# Format: (chemin_image, [liste médicaments attendus])

TESTS = [
    # Test 1: Ordonnance imprimée simple
    {
        'name': 'ordonnance_imprimee_1.jpg',
        'path': 'test_images/ordonnance_imprimee_1.jpg',
        'expected': ['Doliprane 1000mg', 'Amoxicilline 500mg']
    },

    # Test 2: Ordonnance manuscrite
    {
        'name': 'ordonnance_manuscrite_1.jpg',
        'path': 'test_images/ordonnance_manuscrite_1.jpg',
        'expected': ['Doliprane', 'Efferalgan']
    },

    # Test 3: Ordonnance avec synonymes
    {
        'name': 'ordonnance_synonymes.jpg',
        'path': 'test_images/ordonnance_synonymes.jpg',
        'expected': ['Paracetamol', 'Ibuprofene']
    },

    # Ajoutez vos propres tests ici...
]


# =============================================================================
# FONCTIONS
# =============================================================================

def test_single_image(test_config):
    """
    Teste une seule image.

    Args:
        test_config: Dict avec 'name', 'path', 'expected'

    Returns:
        Dict avec résultats du test
    """
    image_path = test_config['path']
    expected = test_config['expected']
    name = test_config['name']

    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    print(f"Fichier: {image_path}")
    print(f"Médicaments attendus: {', '.join(expected)}")
    print()

    # Vérifier que l'image existe
    if not os.path.exists(image_path):
        print(f"❌ ERREUR: Image non trouvée: {image_path}")
        print("   Créez un dossier 'test_images/' et placez vos images dedans.")
        return None

    # Charger l'image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    print(f"📷 Image chargée: {len(image_bytes)} bytes")

    # Traiter
    start_time = time.time()
    processor = PrescriptionProcessor()
    result = processor.process_prescription(image_bytes)
    processing_time = int((time.time() - start_time) * 1000)

    print(f"⏱️  Temps de traitement: {processing_time}ms")
    print()

    if not result['success']:
        print(f"❌ ERREUR: {result['error']}")
        return None

    # Afficher résultats
    print(f"📝 Texte OCR détecté ({len(result['text_detected'])} caractères):")
    print("-" * 80)
    print(result['text_detected'][:300] + '...' if len(result['text_detected']) > 300 else result['text_detected'])
    print("-" * 80)
    print()

    print(f"💊 Médicaments détectés: {len(result['medications'])}")
    for med in result['medications']:
        print(f"   - {med['nom']}")
        print(f"     Confiance: {med['confidence']}%")
        print(f"     Dosage DB: {med.get('dosage', 'N/A')}")
        print(f"     Dosage détecté: {med.get('dosage_detected', 'N/A')}")
        print(f"     Fréquence: {med.get('frequency', 'N/A')}")
        print(f"     Méthode: {med.get('match_method', 'N/A')}")
        print()

    # Générer rapport de test
    test_result = test_reporter.test_scan(
        image_name=name,
        expected_medications=expected,
        detected_medications=result['medications'],
        ocr_text=result['text_detected']
    )

    # Afficher métriques
    print(f"📊 MÉTRIQUES:")
    print(f"   Précision: {test_result['precision']:.2f}%")
    print(f"   Rappel: {test_result['recall']:.2f}%")
    print(f"   F1-Score: {test_result['f1_score']:.2f}%")
    print()

    if test_result['true_positives']:
        print(f"✅ Vrais Positifs ({len(test_result['true_positives'])}):")
        for tp in test_result['true_positives']:
            print(f"   - {tp['detected']} (confiance: {tp['confidence']}%)")

    if test_result['false_positives']:
        print(f"\n❌ Faux Positifs ({len(test_result['false_positives'])}):")
        for fp in test_result['false_positives']:
            print(f"   - {fp}")

    if test_result['false_negatives']:
        print(f"\n⚠️  Faux Négatifs ({len(test_result['false_negatives'])}):")
        for fn in test_result['false_negatives']:
            print(f"   - {fn}")

    # Logger le scan
    from django.conf import settings
    scan_logger.log_scan({
        'mode': getattr(settings, 'GOOGLE_VISION_MODE', 'mock'),
        'image_size': len(image_bytes),
        'text_detected': result['text_detected'],
        'medications': result['medications'],
        'processing_time': processing_time,
        'success': True,
        'error': ''
    })

    return test_result


def run_all_tests():
    """Exécute tous les tests et génère un rapport final."""
    print("\n" + "=" * 80)
    print("🧪 LANCEMENT DES TESTS OCR BATCH")
    print("=" * 80)

    # Vérifier que le dossier test_images existe
    if not os.path.exists('test_images'):
        print("\n⚠️  ATTENTION: Le dossier 'test_images/' n'existe pas.")
        print("   Création du dossier...")
        os.makedirs('test_images', exist_ok=True)
        print("   ✅ Dossier créé.")
        print("\n📝 Placez vos images de test dans le dossier 'test_images/' et relancez le script.")
        print("   Format attendu:")
        for test in TESTS:
            print(f"   - {test['path']}")
        return

    # Exécuter tous les tests
    results = []
    for test_config in TESTS:
        result = test_single_image(test_config)
        if result:
            results.append(result)
        time.sleep(0.5)  # Petite pause entre tests

    # Rapport final
    print("\n" + "=" * 80)
    print("📊 RAPPORT FINAL")
    print("=" * 80)

    if not results:
        print("❌ Aucun test exécuté avec succès.")
        return

    avg_precision = sum(r['precision'] for r in results) / len(results)
    avg_recall = sum(r['recall'] for r in results) / len(results)
    avg_f1 = sum(r['f1_score'] for r in results) / len(results)

    print(f"\nTests exécutés: {len(results)}/{len(TESTS)}")
    print(f"\nMétriques moyennes:")
    print(f"  Précision: {avg_precision:.2f}%")
    print(f"  Rappel: {avg_recall:.2f}%")
    print(f"  F1-Score: {avg_f1:.2f}%")

    # Afficher les statistiques globales
    print("\n" + "=" * 80)
    print("📈 STATISTIQUES GLOBALES (tous les scans)")
    print("=" * 80)
    stats = scan_logger.get_statistics()
    print(f"\nTotal de scans effectués: {stats.get('total_scans', 0)}")
    print(f"Scans réussis: {stats.get('successful_scans', 0)}")
    print(f"Scans échoués: {stats.get('failed_scans', 0)}")
    print(f"Taux de succès: {stats.get('success_rate', 0):.2f}%")
    print(f"\nMédicaments détectés au total: {stats.get('total_medications_detected', 0)}")
    print(f"Moyenne par scan: {stats.get('avg_medications_per_scan', 0):.2f}")
    print(f"\nConfiance moyenne: {stats.get('avg_confidence_global', 0):.2f}%")
    print(f"Temps de traitement moyen: {stats.get('avg_processing_time_ms', 0):.2f}ms")

    # Générer rapport texte complet
    print("\n" + "=" * 80)
    print("📄 GÉNÉRATION DU RAPPORT DÉTAILLÉ")
    print("=" * 80)

    report_text = test_reporter.generate_summary_report()
    report_file = 'ocr_logs/test_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n✅ Rapport sauvegardé: {report_file}")
    print("\n💡 Consultez aussi:")
    print("   - ocr_logs/all_scans.jsonl (tous les scans en JSON)")
    print("   - ocr_logs/metrics.csv (métriques en CSV)")
    print("   - ocr_logs/test_results.json (résultats de tests)")


# =============================================================================
# MODE INTERACTIF
# =============================================================================

def interactive_mode():
    """Mode interactif pour tester une seule image."""
    print("\n" + "=" * 80)
    print("🔍 MODE INTERACTIF - Test d'une seule image")
    print("=" * 80)

    image_path = input("\nChemin de l'image à tester: ").strip()

    if not os.path.exists(image_path):
        print(f"❌ Fichier non trouvé: {image_path}")
        return

    expected_input = input("Médicaments attendus (séparés par des virgules): ").strip()
    expected = [med.strip() for med in expected_input.split(',') if med.strip()]

    if not expected:
        print("⚠️  Aucun médicament attendu spécifié. Le test continuera sans comparaison.")

    test_config = {
        'name': os.path.basename(image_path),
        'path': image_path,
        'expected': expected
    }

    test_single_image(test_config)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                         TESTS OCR - UMBRELLA                              ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)

    print("Choisissez un mode:")
    print("  1. Exécuter tous les tests batch")
    print("  2. Mode interactif (une seule image)")
    print("  3. Afficher les statistiques")
    print("  4. Quitter")

    choice = input("\nVotre choix (1-4): ").strip()

    if choice == '1':
        run_all_tests()
    elif choice == '2':
        interactive_mode()
    elif choice == '3':
        stats = scan_logger.get_statistics()
        print("\n" + "=" * 80)
        print("📈 STATISTIQUES GLOBALES")
        print("=" * 80)
        for key, value in stats.items():
            print(f"{key}: {value}")

        print("\n📊 10 derniers scans:")
        recent = scan_logger.get_recent_scans(10)
        for scan in recent:
            print(f"\n  {scan['scan_id']} ({scan['timestamp']})")
            print(f"    Mode: {scan['mode']}, Meds: {scan['medications_count']}, Confiance: {scan['avg_confidence']}%")
    else:
        print("Au revoir!")
