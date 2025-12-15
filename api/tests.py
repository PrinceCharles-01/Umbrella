# -*- coding: utf-8 -*-
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from .models import Pharmacie, Medication, PharmacyMedication


class PharmacieAPITestCase(TestCase):
    """Tests pour API Pharmacie"""

    def setUp(self):
        self.client = APIClient()
        self.pharmacy1 = Pharmacie.objects.create(
            nom="Pharmacie du Centre",
            adresse="123 Rue de la Paix, Libreville",
            telephone="+24177000001",
            latitude=Decimal('0.4162'),
            longitude=Decimal('9.4673'),
            note=Decimal('4.5'),
            assurances_acceptees=["CNAMGS", "CNSS"],
            opening_time="08:00:00",
            closing_time="20:00:00"
        )

    def test_get_all_pharmacies(self):
        response = self.client.get('/api/pharmacies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_get_pharmacy_by_id(self):
        response = self.client.get(f'/api/pharmacies/{self.pharmacy1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], "Pharmacie du Centre")


class MedicationAPITestCase(TestCase):
    """Tests pour API Medicament"""

    def setUp(self):
        self.client = APIClient()
        self.medication1 = Medication.objects.create(
            nom="Doliprane 1000mg",
            description="Antalgique",
            dosage="1000mg",
            categorie="Antalgique",
            prix=250
        )

    def test_get_all_medications(self):
        response = self.client.get('/api/medications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_get_medication_by_id(self):
        response = self.client.get(f'/api/medications/{self.medication1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], "Doliprane 1000mg")


class PharmacyMedicationSearchTestCase(TestCase):
    """Tests pour recherche medicaments"""

    def setUp(self):
        self.client = APIClient()
        self.pharmacy = Pharmacie.objects.create(
            nom="Pharmacie Test",
            adresse="Test Address",
            latitude=Decimal('0.4162'),
            longitude=Decimal('9.4673'),
            note=Decimal('4.5')
        )
        self.med1 = Medication.objects.create(
            nom="Doliprane 1000mg",
            categorie="Antalgique",
            prix=250
        )
        PharmacyMedication.objects.create(
            pharmacy=self.pharmacy,
            medication=self.med1,
            stock_disponible=50,
            prix_unitaire=250
        )

    def test_find_pharmacy_by_single_medication(self):
        response = self.client.get(f'/api/pharmacies/?medication_id={self.med1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_find_pharmacies_by_multiple_medications(self):
        data = {'medication_ids': [self.med1.id]}
        response = self.client.post('/api/pharmacies/find-by-medications/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OCRServicesTestCase(TestCase):
    """Tests pour les services OCR et extraction de medicaments"""

    def setUp(self):
        """Creer des medicaments de test"""
        self.doliprane = Medication.objects.create(
            nom="Doliprane 1000mg",
            dosage="1000mg",
            categorie="Antalgique",
            prix=250
        )
        self.amoxicilline = Medication.objects.create(
            nom="Amoxicilline 500mg",
            dosage="500mg",
            categorie="Antibiotique",
            prix=500
        )
        self.paracetamol = Medication.objects.create(
            nom="Paracetamol 500mg",
            dosage="500mg",
            categorie="Antalgique",
            prix=200
        )
        self.advil = Medication.objects.create(
            nom="Advil 400mg",
            dosage="400mg",
            categorie="Anti-inflammatoire",
            prix=300
        )

    def test_mock_ocr_service(self):
        """Test que le MockOCRService retourne du texte"""
        from .services import MockOCRService

        service = MockOCRService()
        text = service.extract_text_from_image(b"fake_image_bytes")

        self.assertIsNotNone(text)
        self.assertGreater(len(text), 0)
        self.assertIn("DOLIPRANE", text.upper())

    def test_medication_extractor_basic(self):
        """Test extraction basique de medicaments"""
        from .services import MedicationExtractor

        text = """
        ORDONNANCE
        DOLIPRANE 1000mg
        1 comprime matin et soir
        """

        extractor = MedicationExtractor(similarity_threshold=75)
        results = extractor.extract_medications_from_text(text)

        # Devrait trouver au moins 1 medicament
        self.assertGreater(len(results), 0)

        # Verifier qu'un des resultats est Doliprane
        medication_names = [med['nom'] for med in results]
        self.assertTrue(any('Doliprane' in name for name in medication_names))

    def test_medication_extractor_with_typos(self):
        """Test fuzzy matching avec fautes de frappe"""
        from .services import MedicationExtractor

        # "DOLIPRNE" au lieu de "DOLIPRANE" (faute de frappe)
        text = "DOLIPRNE 1000mg"

        extractor = MedicationExtractor(similarity_threshold=75)
        results = extractor.extract_medications_from_text(text)

        # Devrait quand meme trouver Doliprane malgre la faute
        self.assertGreater(len(results), 0)

    def test_medication_extractor_with_synonyms(self):
        """Test que les synonymes fonctionnent (PARACETAMOL = DOLIPRANE)"""
        from .services import MedicationExtractor

        # Le texte dit "PARACETAMOL" mais on a "Paracetamol 500mg" en DB
        text = "PARACETAMOL 500mg pour la fievre"

        extractor = MedicationExtractor(similarity_threshold=75)
        results = extractor.extract_medications_from_text(text)

        # Devrait trouver Paracetamol
        self.assertGreater(len(results), 0)
        medication_ids = [med['id'] for med in results]
        self.assertIn(self.paracetamol.id, medication_ids)

    def test_dosage_extraction(self):
        """Test extraction des dosages"""
        from .services import extract_dosages_from_text

        text = "DOLIPRANE 1000mg et AMOXICILLINE 500 mg"

        dosages = extract_dosages_from_text(text)

        # Devrait trouver 2 dosages
        self.assertEqual(len(dosages), 2)

        # Verifier les valeurs
        values = [d['value'] for d in dosages]
        self.assertIn('1000', values)
        self.assertIn('500', values)

        # Verifier les unites
        units = [d['unit'] for d in dosages]
        self.assertEqual(units, ['mg', 'mg'])

    def test_dosage_extraction_various_formats(self):
        """Test extraction avec differents formats de dosage"""
        from .services import extract_dosages_from_text

        text = "1000mg, 2.5g, 10ml, 500mcg"
        dosages = extract_dosages_from_text(text)

        # Devrait trouver 4 dosages
        self.assertEqual(len(dosages), 4)

        # Verifier les unites variees
        units = [d['unit'] for d in dosages]
        self.assertIn('mg', units)
        self.assertIn('g', units)
        self.assertIn('ml', units)
        self.assertIn('mcg', units)

    def test_frequency_extraction(self):
        """Test extraction de la frequence de prise"""
        from .services import extract_frequency_from_text

        text1 = "1 comprime matin et soir"
        text2 = "3 fois par jour"
        text3 = "avant repas"

        freq1 = extract_frequency_from_text(text1)
        freq2 = extract_frequency_from_text(text2)
        freq3 = extract_frequency_from_text(text3)

        self.assertEqual(freq1, 'matin_soir')
        self.assertEqual(freq2, '3x_par_jour')
        self.assertEqual(freq3, 'avant_repas')

    def test_adaptive_similarity_threshold(self):
        """Test seuils adaptatifs selon longueur"""
        from .services import adaptive_similarity_threshold

        # Mots courts -> seuil eleve
        threshold_short = adaptive_similarity_threshold(4)
        self.assertGreaterEqual(threshold_short, 85)

        # Mots longs -> seuil plus bas
        threshold_long = adaptive_similarity_threshold(15)
        self.assertLessEqual(threshold_long, 75)

    def test_normalize_medication_name(self):
        """Test normalisation vers DCI"""
        from .services import normalize_medication_name

        # DOLIPRANE doit etre normalise vers "paracetamol"
        normalized1 = normalize_medication_name("DOLIPRANE")
        self.assertEqual(normalized1, "paracetamol")

        # ADVIL doit etre normalise vers "ibuprofene"
        normalized2 = normalize_medication_name("Advil")
        self.assertEqual(normalized2, "ibuprofene")

        # Nom avec accents
        normalized3 = normalize_medication_name("Paracétamol")
        self.assertEqual(normalized3, "paracetamol")

    def test_medication_extractor_detects_dosage_and_frequency(self):
        """Test que l'extracteur detecte dosage et frequence"""
        from .services import MedicationExtractor

        text = """
        DOLIPRANE 1000mg
        1 comprime matin et soir
        """

        extractor = MedicationExtractor(similarity_threshold=75)
        results = extractor.extract_medications_from_text(text)

        # Devrait avoir trouve Doliprane
        self.assertGreater(len(results), 0)

        # Verifier que dosage_detected et frequency sont presents
        first_result = results[0]
        self.assertIn('dosage_detected', first_result)
        self.assertIn('frequency', first_result)

        # Le dosage detecte devrait etre "1000mg"
        if first_result['dosage_detected']:
            self.assertIn('1000', first_result['dosage_detected'])

    def test_image_validator(self):
        """Test validation d'images"""
        from .services import ImageValidator
        from PIL import Image
        import io

        # Creer une fausse image valide (100x100 JPEG)
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        valid_image_bytes = img_bytes.getvalue()

        is_valid, error = ImageValidator.validate_image(valid_image_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_image_validator_too_small(self):
        """Test validation rejette images trop petites"""
        from .services import ImageValidator
        from PIL import Image
        import io

        # Image trop petite (50x50)
        img = Image.new('RGB', (50, 50), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        small_image_bytes = img_bytes.getvalue()

        is_valid, error = ImageValidator.validate_image(small_image_bytes)
        self.assertFalse(is_valid)
        self.assertIn("petite", error.lower())

    def test_image_validator_empty(self):
        """Test validation rejette images vides"""
        from .services import ImageValidator

        is_valid, error = ImageValidator.validate_image(b"")
        self.assertFalse(is_valid)
        self.assertIn("vide", error.lower())
