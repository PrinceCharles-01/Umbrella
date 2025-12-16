"""
Command de seed SÉCURISÉ - Ne supprime PAS les données existantes
Utiliser : python manage.py seed_data_safe
"""

import json
from datetime import time
from django.core.management.base import BaseCommand
from api.models import Pharmacie, Medication, PharmacyMedication

class Command(BaseCommand):
    help = 'Seeds the database ONLY if empty (safe for production).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking database...'))

        # Vérifier si la base contient déjà des données
        med_count = Medication.objects.count()
        pharm_count = Pharmacie.objects.count()

        if med_count > 0 or pharm_count > 0:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Database already contains data ({med_count} medications, {pharm_count} pharmacies).'
            ))
            self.stdout.write(self.style.WARNING('Seeding aborted to prevent data loss.'))
            self.stdout.write(self.style.SUCCESS('Use --force to seed anyway (will DELETE existing data).'))
            return

        self.stdout.write(self.style.SUCCESS('Database is empty. Starting safe seed...'))

        # --- Pharmacies ---
        pharmacies_data = [
            {
                'nom': 'Pharmacie de la Paix',
                'adresse': '12 Boulevard Leon M\'ba, Libreville',
                'telephone': '+241 01 43 57 89',
                'opening_time': time(8, 0),
                'closing_time': time(20, 0),
                'latitude': 0.42200,
                'longitude': 9.44750,
                'note': 4.5,
                'assurances_acceptees': json.dumps(["CNAMGS", "CNSS", "Mutuelle"]),
                'assurance_speciale': 'CNAMGS'
            },
            {
                'nom': 'Pharmacie Saint-Antoine',
                'adresse': '45 Avenue du Colonel Parant, Libreville',
                'telephone': '+241 01 43 67 23',
                'opening_time': time(8, 30),
                'closing_time': time(19, 30),
                'latitude': 0.38520,
                'longitude': 9.44740,
                'note': 4.2,
                'assurances_acceptees': json.dumps(["CNSS", "Mutuelle"]),
                'assurance_speciale': None
            },
            {
                'nom': 'Pharmacie Moderne',
                'adresse': '78 Rue de la Sobraga, Libreville',
                'telephone': '+241 01 43 48 91',
                'opening_time': time(9, 0),
                'closing_time': time(19, 0),
                'latitude': 0.3925,
                'longitude': 9.4534,
                'note': 4.0,
                'assurances_acceptees': json.dumps(["CNAMGS", "CNSS"]),
                'assurance_speciale': 'CNAMGS'
            },
        ]
        for data in pharmacies_data:
            Pharmacie.objects.create(**data)
        self.stdout.write(self.style.SUCCESS(f'Created {len(pharmacies_data)} pharmacies.'))

        # --- Medications ---
        medications_data = [
            {'nom': 'Doliprane 1000mg', 'description': 'Antalgique et antipyrétique à base de paracétamol', 'dosage': '1000mg - 8 comprimés', 'categorie': 'Antalgique', 'prix': 175000},
            {'nom': 'Aspirine 500mg', 'description': 'Anti-inflammatoire non stéroïdien, antalgique et antipyrétique', 'dosage': '500mg - 20 comprimés', 'categorie': 'AINS', 'prix': 190000},
            {'nom': 'Ibuprofène 400mg', 'description': 'Anti-inflammatoire non stéroïdien pour douleurs et fièvre', 'dosage': '400mg - 12 comprimés', 'categorie': 'AINS', 'prix': 145000},
            {'nom': 'Dafalgan 500mg', 'description': 'Antalgique à base de paracétamol', 'dosage': '500mg - 16 comprimés', 'categorie': 'Antalgique', 'prix': 125000},
            {'nom': 'Advil 200mg', 'description': 'Anti-inflammatoire à base d\'ibuprofène', 'dosage': '200mg - 24 comprimés', 'categorie': 'AINS', 'prix': 165000},
            {'nom': 'Spasfon 80mg', 'description': 'Antispasmodique pour crampes et douleurs', 'dosage': '80mg - 30 comprimés', 'categorie': 'Antispasmodique', 'prix': 210000},
            {'nom': 'Amoxicilline 500mg', 'description': 'Antibiotique pour infections bactériennes', 'dosage': '500mg - 12 gélules', 'categorie': 'Antibiotique', 'prix': 350000},
            {'nom': 'Cetirizine 10mg', 'description': 'Antihistaminique pour allergies', 'dosage': '10mg - 15 comprimés', 'categorie': 'Antihistaminique', 'prix': 280000},
            {'nom': 'Lexomil 6mg', 'description': 'Anxiolytique pour troubles de l\'anxiété', 'dosage': '6mg - 30 comprimés', 'categorie': 'Anxiolytique', 'prix': 420000},
            {'nom': 'Prednisone 20mg', 'description': 'Corticoïde anti-inflammatoire stéroïdien', 'dosage': '20mg - 20 comprimés', 'categorie': 'Corticoïde', 'prix': 550000},
            {'nom': 'Ventoline 100µg', 'description': 'Bronchodilatateur pour l\'asthme', 'dosage': '100µg/dose - 200 doses', 'categorie': 'Bronchodilatateur', 'prix': 680000},
            {'nom': 'Smecta', 'description': 'Antidiarrhéique, pansement digestif', 'dosage': '3g - 18 sachets', 'categorie': 'Antidiarrhéique', 'prix': 320000},
            {'nom': 'Gaviscon', 'description': 'Antiacide pour reflux gastro-œsophagien', 'dosage': 'Suspension buvable 24 sachets', 'categorie': 'Antiacide', 'prix': 450000},
            {'nom': 'Tardyferon 80mg', 'description': 'Antianémique pour carence en fer', 'dosage': '80mg - 30 comprimés', 'categorie': 'Antianémique', 'prix': 290000},
            {'nom': 'Imodium 2mg', 'description': 'Antidiarrhéique pour diarrhée aiguë', 'dosage': '2mg - 12 gélules', 'categorie': 'Antidiarrhéique', 'prix': 240000},
            {'nom': 'Xanax 0.25mg', 'description': 'Anxiolytique pour anxiété et attaques de panique', 'dosage': '0.25mg - 30 comprimés', 'categorie': 'Anxiolytique', 'prix': 380000},
        ]
        for data in medications_data:
            Medication.objects.create(**data)
        self.stdout.write(self.style.SUCCESS(f'Created {len(medications_data)} medications.'))

        # --- PharmacyMedications (Stock) ---
        pharmacie_paix = Pharmacie.objects.get(nom='Pharmacie de la Paix')
        pharmacie_saint_antoine = Pharmacie.objects.get(nom='Pharmacie Saint-Antoine')
        pharmacie_moderne = Pharmacie.objects.get(nom='Pharmacie Moderne')

        medications_map = {med.nom: med for med in Medication.objects.all()}

        pharmacy_medications_data = [
            # Pharmacie de la Paix
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Doliprane 1000mg'], 'stock_disponible': 25, 'prix_unitaire': 175000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Aspirine 500mg'], 'stock_disponible': 15, 'prix_unitaire': 190000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Ibuprofène 400mg'], 'stock_disponible': 30, 'prix_unitaire': 145000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Dafalgan 500mg'], 'stock_disponible': 20, 'prix_unitaire': 125000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Advil 200mg'], 'stock_disponible': 18, 'prix_unitaire': 165000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Spasfon 80mg'], 'stock_disponible': 22, 'prix_unitaire': 210000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Amoxicilline 500mg'], 'stock_disponible': 12, 'prix_unitaire': 350000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Cetirizine 10mg'], 'stock_disponible': 30, 'prix_unitaire': 280000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Lexomil 6mg'], 'stock_disponible': 5, 'prix_unitaire': 420000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Prednisone 20mg'], 'stock_disponible': 10, 'prix_unitaire': 550000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Ventoline 100µg'], 'stock_disponible': 15, 'prix_unitaire': 680000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Smecta'], 'stock_disponible': 40, 'prix_unitaire': 320000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Gaviscon'], 'stock_disponible': 25, 'prix_unitaire': 450000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Tardyferon 80mg'], 'stock_disponible': 14, 'prix_unitaire': 290000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Imodium 2mg'], 'stock_disponible': 10, 'prix_unitaire': 240000},
            {'pharmacy': pharmacie_paix, 'medication': medications_map['Xanax 0.25mg'], 'stock_disponible': 8, 'prix_unitaire': 380000},

            # Pharmacie Saint-Antoine
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Doliprane 1000mg'], 'stock_disponible': 10, 'prix_unitaire': 175000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Aspirine 500mg'], 'stock_disponible': 8, 'prix_unitaire': 195000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Dafalgan 500mg'], 'stock_disponible': 15, 'prix_unitaire': 130000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Spasfon 80mg'], 'stock_disponible': 20, 'prix_unitaire': 215000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Amoxicilline 500mg'], 'stock_disponible': 8, 'prix_unitaire': 355000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Cetirizine 10mg'], 'stock_disponible': 10, 'prix_unitaire': 285000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Ventoline 100µg'], 'stock_disponible': 5, 'prix_unitaire': 690000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Gaviscon'], 'stock_disponible': 12, 'prix_unitaire': 455000},
            {'pharmacy': pharmacie_saint_antoine, 'medication': medications_map['Imodium 2mg'], 'stock_disponible': 18, 'prix_unitaire': 245000},

            # Pharmacie Moderne
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Ibuprofène 400mg'], 'stock_disponible': 5, 'prix_unitaire': 150000},
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Advil 200mg'], 'stock_disponible': 12, 'prix_unitaire': 170000},
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Lexomil 6mg'], 'stock_disponible': 15, 'prix_unitaire': 425000},
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Prednisone 20mg'], 'stock_disponible': 8, 'prix_unitaire': 555000},
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Smecta'], 'stock_disponible': 20, 'prix_unitaire': 325000},
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Tardyferon 80mg'], 'stock_disponible': 10, 'prix_unitaire': 295000},
            {'pharmacy': pharmacie_moderne, 'medication': medications_map['Xanax 0.25mg'], 'stock_disponible': 4, 'prix_unitaire': 385000},
        ]
        for data in pharmacy_medications_data:
            PharmacyMedication.objects.create(**data)
        self.stdout.write(self.style.SUCCESS(f'Created {len(pharmacy_medications_data)} pharmacy-medication links.'))

        self.stdout.write(self.style.SUCCESS('✅ Safe seeding complete!'))
