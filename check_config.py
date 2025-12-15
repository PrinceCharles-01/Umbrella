# -*- coding: utf-8 -*-
"""
Script de vérification rapide de la configuration.
Vérifie que tout est prêt pour les tests.

Usage:
    python check_config.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umbrella_api.settings')
django.setup()

from django.conf import settings
from api.services import OCRService, MockOCRService
from api.ocr_logger import scan_logger


def check_credentials():
    """Vérifie les credentials Google Vision."""
    print("\n" + "=" * 80)
    print("1. VÉRIFICATION CREDENTIALS GOOGLE VISION")
    print("=" * 80)

    creds_path = os.path.join(settings.BASE_DIR, 'google-vision-credentials.json')

    if os.path.exists(creds_path):
        print(f"✅ Fichier trouvé: {creds_path}")
        print(f"   Taille: {os.path.getsize(creds_path)} bytes")

        # Tester le client
        try:
            service = OCRService()
            if service.client:
                print("✅ Client Google Vision initialisé avec succès")
                print(f"   Mode: PRODUCTION (Google Vision)")
                return True
            else:
                print("❌ Client Google Vision non initialisé")
                return False
        except Exception as e:
            print(f"❌ Erreur initialisation: {str(e)}")
            return False
    else:
        print(f"⚠️  Fichier non trouvé: {creds_path}")
        print(f"   Mode: MOCK (développement)")
        print()
        print("   Pour activer Google Vision:")
        print("   1. Placez google-vision-credentials.json dans django-backend/")
        print("   2. Redémarrez le serveur")
        return False


def check_directories():
    """Vérifie que les dossiers nécessaires existent."""
    print("\n" + "=" * 80)
    print("2. VÉRIFICATION DOSSIERS")
    print("=" * 80)

    directories = {
        'test_images': 'Ordonnances de test',
        'ocr_logs': 'Logs automatiques'
    }

    all_ok = True
    for dirname, description in directories.items():
        path = os.path.join(settings.BASE_DIR, dirname)
        if os.path.exists(path):
            count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            print(f"✅ {dirname:20s} - {description} ({count} fichiers)")
        else:
            print(f"⚠️  {dirname:20s} - Création...")
            os.makedirs(path, exist_ok=True)
            print(f"   ✅ Dossier créé: {path}")
            all_ok = False

    return all_ok


def check_dependencies():
    """Vérifie les dépendances Python."""
    print("\n" + "=" * 80)
    print("3. VÉRIFICATION DÉPENDANCES")
    print("=" * 80)

    dependencies = [
        ('google.cloud.vision', 'Google Cloud Vision'),
        ('PIL', 'Pillow (traitement images)'),
        ('fuzzywuzzy', 'FuzzyWuzzy (matching)'),
        ('Levenshtein', 'python-Levenshtein (distance)')
    ]

    all_ok = True
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            print(f"✅ {module_name:25s} - {description}")
        except ImportError:
            print(f"❌ {module_name:25s} - MANQUANT")
            all_ok = False

    if not all_ok:
        print("\nInstallez les dépendances manquantes:")
        print("pip install google-cloud-vision Pillow fuzzywuzzy python-Levenshtein")

    return all_ok


def check_database():
    """Vérifie que la base de données contient des médicaments."""
    print("\n" + "=" * 80)
    print("4. VÉRIFICATION BASE DE DONNÉES")
    print("=" * 80)

    from api.models import Medication, Pharmacie, PharmacyMedication

    med_count = Medication.objects.count()
    pharm_count = Pharmacie.objects.count()
    stock_count = PharmacyMedication.objects.count()

    print(f"   Médicaments: {med_count}")
    print(f"   Pharmacies: {pharm_count}")
    print(f"   Stocks: {stock_count}")

    if med_count == 0:
        print("\n⚠️  ATTENTION: Aucun médicament en base de données")
        print("   Importez des données de test ou utilisez l'admin Django")
        return False
    else:
        print(f"\n✅ Base de données OK ({med_count} médicaments)")
        return True


def check_logs():
    """Vérifie les logs existants."""
    print("\n" + "=" * 80)
    print("5. VÉRIFICATION LOGS")
    print("=" * 80)

    try:
        stats = scan_logger.get_statistics()

        if stats.get('total_scans', 0) > 0:
            print(f"✅ Logs existants: {stats['total_scans']} scans enregistrés")
            print(f"   Taux de succès: {stats['success_rate']:.2f}%")
            print(f"   Confiance moyenne: {stats['avg_confidence_global']:.2f}%")
            print(f"   Temps moyen: {stats['avg_processing_time_ms']:.0f}ms")
        else:
            print("ℹ️  Aucun scan enregistré pour le moment")
            print("   Les logs seront créés automatiquement lors du premier scan")

        # Vérifier fichiers
        log_dir = os.path.join(settings.BASE_DIR, 'ocr_logs')
        files = ['all_scans.jsonl', 'metrics.csv', 'test_results.json']

        print("\n   Fichiers:")
        for filename in files:
            path = os.path.join(log_dir, filename)
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"   ✅ {filename:25s} ({size} bytes)")
            else:
                print(f"   ℹ️  {filename:25s} (sera créé)")

    except Exception as e:
        print(f"⚠️  Erreur lecture logs: {str(e)}")
        return False

    return True


def main():
    """Lance toutes les vérifications."""
    print("""
===============================================================================
                   VERIFICATION CONFIGURATION OCR
===============================================================================
    """)

    checks = [
        ("Credentials Google Vision", check_credentials),
        ("Dossiers", check_directories),
        ("Dépendances", check_dependencies),
        ("Base de données", check_database),
        ("Logs", check_logs)
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ ERREUR lors de la vérification {name}: {str(e)}")
            results[name] = False

    # Résumé
    print("\n" + "=" * 80)
    print("RESUME")
    print("=" * 80)

    for name, result in results.items():
        status = "[OK]" if result else "[A CONFIGURER]"
        print(f"{status:20s} - {name}")

    # Recommandations
    print("\n" + "=" * 80)
    print("PROCHAINES ETAPES")
    print("=" * 80)

    if not results["Credentials Google Vision"]:
        print("\n1. Placer google-vision-credentials.json")
        print("   -> Voir: PLACEZ_CREDENTIALS_ICI.md")

    if not results["Dépendances"]:
        print("\n2. Installer dependances manquantes")
        print("   pip install google-cloud-vision Pillow fuzzywuzzy python-Levenshtein")

    if not results["Base de données"]:
        print("\n3. Importer des medicaments de test")
        print("   -> Utiliser l'admin Django ou fixtures")

    # Prêt ou pas ?
    all_critical_ok = (
        results["Dépendances"] and
        results["Base de données"] and
        results["Dossiers"]
    )

    if all_critical_ok:
        if results["Credentials Google Vision"]:
            print("\n" + "=" * 80)
            print("CONFIGURATION COMPLETE !")
            print("=" * 80)
            print("\nVous etes pret a:")
            print("1. Lancer le serveur: python manage.py runserver 0.0.0.0:3001")
            print("2. Scanner des ordonnances: http://localhost:8080/scan")
            print("3. Lancer des tests: python test_ocr_batch.py")
        else:
            print("\n" + "=" * 80)
            print("MODE MOCK - Pret pour tests de developpement")
            print("=" * 80)
            print("\nVous pouvez:")
            print("1. Tester en mode mock (sans vraies ordonnances)")
            print("2. Configurer Google Vision pour tester avec vraies ordonnances")
    else:
        print("\n" + "=" * 80)
        print("CONFIGURATION INCOMPLETE")
        print("=" * 80)
        print("\nVeuillez corriger les problemes ci-dessus.")

    print("\n")


if __name__ == '__main__':
    main()
