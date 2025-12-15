# -*- coding: utf-8 -*-
"""
Services pour le traitement des ordonnances et l'extraction de médicaments.
"""
import os
import io
import re
import logging
import base64
import requests
from typing import List, Dict, Tuple, Optional
from google.cloud import vision
from fuzzywuzzy import fuzz
from PIL import Image

from .models import Medication

logger = logging.getLogger(__name__)


# ============================================================================
# DICTIONNAIRE DE SYNONYMES MÉDICAUX
# ============================================================================
# Mapping DCI (Dénomination Commune Internationale) → Noms commerciaux
MEDICATION_SYNONYMS = {
    'paracetamol': ['paracetamol', 'paracétamol', 'doliprane', 'dafalgan', 'efferalgan', 'dolko'],
    'ibuprofene': ['ibuprofene', 'ibuprofène', 'advil', 'nurofen', 'brufen', 'antarène'],
    'amoxicilline': ['amoxicilline', 'clamoxyl', 'amodex', 'amoxil'],
    'aspirine': ['aspirine', 'aspégic', 'aspegic', 'kardégic', 'kardegic'],
    'azithromycine': ['azithromycine', 'zithromax'],
    'omeprazole': ['omeprazole', 'oméprazole', 'mopral', 'zoltum'],
    'metformine': ['metformine', 'glucophage', 'stagid'],
    'atorvastatine': ['atorvastatine', 'tahor'],
    'loratadine': ['loratadine', 'clarityne'],
    'cetirizine': ['cetirizine', 'cétirizine', 'zyrtec', 'virlix'],
}

# Mapping inverse : Nom commercial → DCI
BRAND_TO_DCI = {}
for dci, brands in MEDICATION_SYNONYMS.items():
    for brand in brands:
        BRAND_TO_DCI[brand.lower()] = dci


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def normalize_medication_name(name: str) -> str:
    """
    Normalise un nom de médicament vers sa DCI (Dénomination Commune Internationale).

    Exemples:
        "DOLIPRANE" → "paracetamol"
        "Advil" → "ibuprofene"
        "Paracétamol" → "paracetamol"

    Args:
        name: Nom du médicament (commercial ou DCI)

    Returns:
        str: DCI normalisée (minuscules, sans accents pour matching)
    """
    name_lower = name.lower().strip()

    # Supprimer les accents pour le matching
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'ô': 'o', 'ö': 'o',
        'î': 'i', 'ï': 'i',
    }
    for accented, normal in replacements.items():
        name_lower = name_lower.replace(accented, normal)

    # Chercher dans le dictionnaire de synonymes
    for dci, synonyms in MEDICATION_SYNONYMS.items():
        for synonym in synonyms:
            # Normaliser aussi le synonyme pour comparaison
            syn_normalized = synonym.lower()
            for accented, normal in replacements.items():
                syn_normalized = syn_normalized.replace(accented, normal)

            if syn_normalized in name_lower or name_lower in syn_normalized:
                return dci

    # Si pas trouvé dans le dictionnaire, retourner le nom normalisé
    return name_lower


def extract_dosages_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extrait tous les dosages détectés dans un texte OCR.

    Exemples détectés:
        - "1000mg", "1000 mg", "1000MG"
        - "1g", "1 g", "2.5g"
        - "500mcg", "500 mcg"
        - "10ml", "10 ml"

    Args:
        text: Texte OCR brut

    Returns:
        List[Dict]: [{'value': '1000', 'unit': 'mg', 'full': '1000mg'}, ...]
    """
    dosage_patterns = [
        (r'(\d+(?:\.\d+)?)\s*(mg)', 'mg'),      # milligrammes
        (r'(\d+(?:\.\d+)?)\s*(g)(?!\w)', 'g'),  # grammes (mais pas "mg")
        (r'(\d+(?:\.\d+)?)\s*(ml)', 'ml'),      # millilitres
        (r'(\d+(?:\.\d+)?)\s*(mcg|µg)', 'mcg'), # microgrammes
        (r'(\d+(?:\.\d+)?)\s*(ui)', 'ui'),      # unités internationales
    ]

    dosages = []
    for pattern, unit in dosage_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            dosages.append({
                'value': match.group(1),
                'unit': unit,
                'full': match.group(0).strip()
            })

    return dosages


def extract_frequency_from_text(text: str) -> Optional[str]:
    """
    Extrait la fréquence de prise depuis un texte.

    Exemples:
        "matin et soir" → "matin_soir"
        "3 fois par jour" → "3x_par_jour"
        "avant repas" → "avant_repas"

    Args:
        text: Texte OCR

    Returns:
        str: Code de fréquence détecté, ou None
    """
    frequency_patterns = {
        'matin_soir': r'matin\s+(?:et\s+)?soir',
        'fois_par_jour': r'(\d+)\s*fois?\s+par\s+jour',
        'avant_repas': r'avant\s+(?:le\s+)?repas',
        'apres_repas': r'apr[eè]s\s+(?:le\s+)?repas',
        'au_coucher': r'au\s+coucher',
        'matin': r'\bmatin\b',
        'soir': r'\bsoir\b',
    }

    text_lower = text.lower()
    for key, pattern in frequency_patterns.items():
        match = re.search(pattern, text_lower)
        if match:
            if key == 'fois_par_jour':
                return f"{match.group(1)}x_par_jour"
            return key

    return None


def adaptive_similarity_threshold(word_length: int) -> int:
    """
    Retourne un seuil de similarité adaptatif selon la longueur du mot.

    Les mots courts nécessitent un matching plus strict (moins de tolérance aux erreurs)
    car une faute sur un mot de 4 lettres est plus grave que sur un mot de 15 lettres.

    Args:
        word_length: Longueur du mot à matcher

    Returns:
        int: Seuil de similarité recommandé (0-100)
    """
    if word_length <= 4:
        return 90  # Très strict pour mots très courts
    elif word_length <= 6:
        return 85  # Strict pour mots courts
    elif word_length <= 10:
        return 80  # Standard
    elif word_length <= 15:
        return 75  # Un peu plus permissif
    else:
        return 70  # Plus permissif pour mots très longs


class MockOCRService:
    """
    Service OCR simulé pour développement sans Google Cloud.
    Retourne du texte de test pour tester le flow.
    """

    def __init__(self):
        self.client = True  # Simuler qu'on a un client
        logger.info("Mock OCR Service initialisé (mode développement)")

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Retourne du texte de test simulant une ordonnance"""
        logger.info("Mode MOCK: Retourne du texte de test")
        return """
        ORDONNANCE MÉDICALE

        Dr. Jean NGUEMA
        Médecin Généraliste
        Libreville, Gabon

        Patient: M. Dupont
        Date: 01/12/2025

        DOLIPRANE 1000mg
        1 comprimé matin et soir
        Pendant 5 jours

        AMOXICILLINE 500mg
        1 gélule 3 fois par jour
        Pendant 7 jours

        EFFERALGAN 500mg
        En cas de douleur

        PARACETAMOL 500mg
        Si fièvre
        """


class OCRService:
    """
    Service pour l'OCR (Optical Character Recognition) via Google Cloud Vision.
    """

    def __init__(self):
        """
        Initialise le client Google Vision.
        Note: Les credentials doivent être configurés via GOOGLE_APPLICATION_CREDENTIALS
        """
        try:
            self.client = vision.ImageAnnotatorClient()
            logger.info("Google Vision client initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur initialisation Google Vision: {str(e)}")
            self.client = None

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extrait le texte d'une image via Google Cloud Vision OCR.

        Args:
            image_bytes: Contenu binaire de l'image

        Returns:
            str: Texte extrait de l'image

        Raises:
            Exception: Si l'OCR échoue
        """
        if not self.client:
            raise Exception("Client Google Vision non initialisé. Vérifiez vos credentials.")

        try:
            # Créer l'objet image pour Vision API
            image = vision.Image(content=image_bytes)

            # Appel à l'API pour la détection de texte
            response = self.client.text_detection(image=image)

            # Vérifier les erreurs
            if response.error.message:
                raise Exception(f"Erreur Google Vision: {response.error.message}")

            # Récupérer le texte détecté
            texts = response.text_annotations
            if texts:
                # Le premier élément contient tout le texte détecté
                full_text = texts[0].description
                logger.info(f"Texte extrait: {len(full_text)} caractères")
                return full_text
            else:
                logger.warning("Aucun texte détecté dans l'image")
                return ""

        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de texte: {str(e)}")
            raise


class OCRServiceWithApiKey:
    """
    Service pour l'OCR (Optical Character Recognition) via Google Cloud Vision API REST.
    Utilise une API Key au lieu d'un service account.
    """

    def __init__(self, api_key: str):
        """
        Initialise le service avec une API Key.

        Args:
            api_key: Clé API Google Cloud Vision
        """
        self.api_key = api_key
        self.api_url = 'https://vision.googleapis.com/v1/images:annotate'
        self.client = True  # Indicateur pour compatibilité
        logger.info("Google Vision API Key service initialisé avec succès")

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extrait le texte d'une image via Google Cloud Vision API REST.

        Args:
            image_bytes: Contenu binaire de l'image

        Returns:
            str: Texte extrait de l'image

        Raises:
            Exception: Si l'OCR échoue
        """
        try:
            # Encoder l'image en base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Préparer la requête pour l'API
            request_body = {
                'requests': [
                    {
                        'image': {
                            'content': image_base64
                        },
                        'features': [
                            {
                                'type': 'TEXT_DETECTION'
                            }
                        ]
                    }
                ]
            }

            # Appel à l'API REST
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=request_body,
                timeout=30
            )

            # Vérifier le statut de la réponse
            if response.status_code != 200:
                error_msg = f"Erreur API Google Vision (status {response.status_code}): {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Parser la réponse
            result = response.json()

            # Vérifier s'il y a des erreurs dans la réponse
            if 'error' in result:
                raise Exception(f"Erreur Google Vision: {result['error']}")

            # Extraire le texte
            responses = result.get('responses', [])
            if responses and 'textAnnotations' in responses[0]:
                text_annotations = responses[0]['textAnnotations']
                if text_annotations:
                    # Le premier élément contient tout le texte
                    full_text = text_annotations[0].get('description', '')
                    logger.info(f"Texte extrait via API Key: {len(full_text)} caractères")
                    return full_text

            logger.warning("Aucun texte détecté dans l'image")
            return ""

        except requests.exceptions.RequestException as e:
            logger.exception(f"Erreur réseau lors de l'appel à Google Vision API: {str(e)}")
            raise Exception(f"Erreur réseau: {str(e)}")
        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de texte: {str(e)}")
            raise


class OCRServiceOpenAI:
    """
    Service pour l'OCR et l'extraction de données structurées via OpenAI Vision API.
    Utilise GPT-4 Vision pour extraire directement un JSON de médicaments.
    """

    def __init__(self, api_key: str, model: str = 'gpt-4o'):
        try:
            from openai import OpenAI
            import json
            self.client = OpenAI(api_key=api_key)
            self.json = json
            self.model = model
            logger.info(f"OpenAI Vision service initialisé avec succès (modèle: {model})")
        except ImportError:
            logger.error("Le package 'openai' n'est pas installé. Installez-le avec: pip install openai")
            self.client = None
        except Exception as e:
            logger.error(f"Erreur initialisation OpenAI: {str(e)}")
            self.client = None

    def extract_structured_data_from_image(self, image_bytes: bytes) -> Dict:
        """
        Extrait les informations structurées d'une image d'ordonnance via OpenAI Vision
        en demandant une réponse JSON.

        Args:
            image_bytes: Contenu binaire de l'image

        Returns:
            Dict: Un dictionnaire contenant le texte brut et la liste structurée des médicaments.
                  Ex: {'raw_text': "...", 'medications': [{'name': 'Doliprane', 'dosage': '1000mg', 'frequency': '1 matin et soir'}]}

        Raises:
            Exception: Si l'extraction échoue.
        """
        if not self.client:
            raise Exception("Client OpenAI non initialisé. Vérifiez votre API key.")

        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image = Image.open(io.BytesIO(image_bytes))
            image_format = image.format.lower()
            mime_type = f"image/{image_format}" if image_format in ['jpeg', 'png', 'webp', 'gif'] else "image/jpeg"

            logger.info(f"Envoi de l'image à OpenAI Vision pour extraction JSON (format: {mime_type})")

            # Nouveau prompt pour demander un JSON
            prompt = """
            Vous êtes un assistant expert en pharmacie. Analysez l'image de cette ordonnance.
            Votre objectif est d'extraire tous les médicaments prescrits.

            Retournez votre réponse sous la forme d'un objet JSON unique contenant une seule clé "medications".
            La valeur de "medications" doit être une liste d'objets, où chaque objet représente un médicament et contient les clés suivantes : "name", "dosage", "frequency".
            - "name": Le nom du médicament.
            - "dosage": Le dosage (ex: "1000mg", "500 mg / 5 ml"). Si non spécifié, laissez une chaîne vide.
            - "frequency": La posologie ou fréquence de prise (ex: "1 comprimé 3 fois par jour", "matin et soir pendant 5 jours"). Si non spécifié, laissez une chaîne vide.

            Si vous ne trouvez aucun médicament, retournez une liste vide pour la clé "medications".
            Ne retournez aucun texte ou explication en dehors de l'objet JSON.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},  # Activer le mode JSON
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )

            response_content = response.choices[0].message.content
            logger.info("Réponse JSON reçue d'OpenAI.")
            
            # Parser le JSON
            data = self.json.loads(response_content)
            
            # Construire un texte brut à partir des données extraites pour le logging et le retour
            raw_text_parts = []
            if 'medications' in data:
                for med in data['medications']:
                    raw_text_parts.append(f"{med.get('name', '')} {med.get('dosage', '')} - {med.get('frequency', '')}")
            
            return {
                "raw_text": "\n".join(raw_text_parts),
                "medications": data.get('medications', [])
            }

        except Exception as e:
            logger.exception(f"Erreur lors de l'extraction de données structurées via OpenAI: {str(e)}")
            raise Exception(f"Erreur OpenAI Vision (JSON Mode): {str(e)}")


class MedicationExtractor:
    """
    Service pour extraire les noms de médicaments depuis un texte OCR.
    Utilise fuzzy matching, dictionnaire de synonymes, et seuils adaptatifs.
    """

    def __init__(self, similarity_threshold: int = 80, use_adaptive_threshold: bool = True):
        """
        Args:
            similarity_threshold: Seuil de base pour le fuzzy matching (0-100)
            use_adaptive_threshold: Si True, utilise des seuils adaptatifs selon la longueur du mot
        """
        self.base_similarity_threshold = similarity_threshold
        self.use_adaptive_threshold = use_adaptive_threshold

    def extract_medications_from_text(self, text: str) -> List[Dict]:
        """
        Extrait les médicaments d'un texte en utilisant un matching intelligent.
        """
        logger.info("Début de l'extraction des médicaments...")
        
        # Normaliser le texte
        text = text.lower()
        text_lines = text.split('\n')  # Traiter ligne par ligne
        medications_found = []
        processed_meds = set()
        
        # Liste noire des faux positifs
        BLACKLIST = {'par', 'pour', 'avec', 'sans', 'comprimes', 'gélules'}
        
        # Récupérer tous les médicaments avec leur DCI
        all_medications = list(Medication.objects.all())
        logger.info(f"Nombre de médicaments dans la base: {len(all_medications)}")
        
        # Parcourir chaque ligne du texte
        for line in text_lines:
            line = line.strip()
            if not line:
                continue
                
            words = line.split()
            for i, word in enumerate(words):
                if len(word) < 4 or word in BLACKLIST:
                    continue
                    
                # Vérifier chaque médicament
                for med in all_medications:
                    if med.id in processed_meds:
                        continue
                        
                    med_name = med.nom.lower()
                    dci = med.dci.lower() if med.dci else ""
                    
                    # 1. Vérifier la correspondance exacte en premier
                    if word == med_name:
                        dosage = self._extract_dosage_nearby(words, i)
                        self._add_medication(medications_found, med, word, 100, dosage)
                        processed_meds.add(med.id)
                        break
                        
                    # 2. Vérifier la DCI exacte
                    if dci and word == dci:
                        dosage = self._extract_dosage_nearby(words, i)
                        self._add_medication(medications_found, med, word, 95, dosage)
                        processed_meds.add(med.id)
                        break
                        
                    # 3. Vérifier les noms similaires (plus strict)
                    similarity = fuzz.token_sort_ratio(word, med_name)
                    if similarity > 90:  # Seuil très élevé pour éviter les confusions
                        # Vérifier le contexte de la ligne
                        if any(bad in line for bad in ['sans', 'pas de', 'arrêt']):
                            continue
                            
                        dosage = self._extract_dosage_nearby(words, i)
                        if self._validate_detection(words, i, med_name, dosage):
                            self._add_medication(medications_found, med, word, similarity, dosage)
                            processed_meds.add(med.id)
                            break
        
        logger.info(f"Médicaments trouvés: {[m['nom'] for m in medications_found]}")
        return medications_found
        
    def _add_medication(self, medications: List[Dict], med, matched_text: str, 
                       confidence: int, dosage: str = None) -> None:
        """Ajoute un médicament à la liste des résultats."""
        medications.append({
            'id': med.id,
            'nom': med.nom,
            'dci': getattr(med, 'dci', '') or "",
            'dosage': med.dosage,
            'dosage_detected': dosage or med.dosage or "",
            'frequency': self._extract_frequency_nearby(matched_text),
            'confidence': confidence,
            'matched_text': matched_text
        })
    
    def _extract_dosage_nearby(self, words: List[str], position: int, window: int = 2) -> str:
        """Extrait un dosage à proximité du mot détecté."""
        # Recherche dans une petite fenêtre autour du mot
        start = max(0, position - window)
        end = min(len(words), position + window + 1)
        
        for i in range(start, end):
            word = words[i].lower()
            # Format: 500mg, 1g, etc.
            if re.match(r'^\d+\s*(mg|g|ml|µg|ui|%|mcg)\b', word):
                return word
        return ""
    
    def _extract_frequency_nearby(self, matched_text: str) -> str:
        """Extrait la fréquence de prise à partir du contexte."""
        # Implémentation simplifiée - à améliorer
        if 'matin' in matched_text.lower() and 'soir' in matched_text.lower():
            return 'Matin et soir'
        elif 'jour' in matched_text.lower():
            return '1 fois par jour'
        return 'Selon prescription'
    
    def _validate_detection(self, words: List[str], position: int, 
                          med_name: str, dosage: str) -> bool:
        """Valide qu'une détection est valide."""
        # Vérifier que le mot est bien isolé ou fait partie d'une expression connue
        context = ' '.join(words[max(0, position-2):position+3]).lower()
        
        # Liste des expressions à exclure
        invalid_expressions = [
            'sans ' + med_name,
            'pas de ' + med_name,
            'arrêt ' + med_name,
            'ne pas prendre ' + med_name
        ]
        
        if any(expr in context for expr in invalid_expressions):
            return False
            
        # Vérifier que le dosage est cohérent
        if dosage:
            # Si le médicament contient un dosage dans son nom, vérifier qu'il correspond
            med_name_lower = med_name.lower()
            if any(unit in med_name_lower for unit in ['mg', 'g', 'ml']):
                # Extraire le dosage du nom du médicament
                med_dosage_match = re.search(r'(\d+)\s*(mg|g|ml)', med_name_lower)
                if med_dosage_match:
                    med_dosage = med_dosage_match.group(1)
                    detected_dosage = re.search(r'(\d+)\s*(mg|g|ml)', dosage.lower())
                    if detected_dosage and med_dosage != detected_dosage.group(1):
                        return False
                        
        return True

    def extract_with_keywords(self, text: str) -> List[str]:
        """
        Méthode alternative: extraction basée sur des mots-clés médicaux.
        Utile en complément du fuzzy matching.

        Args:
            text: Texte brut

        Returns:
            List[str]: Mots-clés médicaux détectés
        """
        # Mots-clés indicateurs de médicaments
        medical_keywords = [
            'mg', 'ml', 'comprimé', 'gélule', 'sirop', 'ampoule',
            'suppositoire', 'injectable', 'cp', 'cpr', 'gel',
            'fois par jour', 'matin', 'soir', 'avant repas', 'après repas'
        ]

        text_lower = text.lower()
        detected_keywords = []

        for keyword in medical_keywords:
            if keyword in text_lower:
                detected_keywords.append(keyword)

        return detected_keywords


class ImageValidator:
    """
    Service pour valider les images uploadées.
    """

    # Formats acceptés
    ALLOWED_FORMATS = ['JPEG', 'JPG', 'PNG', 'WEBP']

    # Taille max: 10 MB
    MAX_SIZE_MB = 10
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

    @staticmethod
    def validate_image(image_bytes: bytes) -> Tuple[bool, str]:
        """
        Valide une image (format, taille, etc.)

        Args:
            image_bytes: Contenu binaire de l'image

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Vérifier la taille
        if len(image_bytes) > ImageValidator.MAX_SIZE_BYTES:
            return False, f"Image trop grande. Maximum: {ImageValidator.MAX_SIZE_MB}MB"

        if len(image_bytes) == 0:
            return False, "Image vide"

        try:
            # Ouvrir l'image avec Pillow pour vérifier le format
            image = Image.open(io.BytesIO(image_bytes))

            # Vérifier le format
            if image.format not in ImageValidator.ALLOWED_FORMATS:
                return False, f"Format non supporté. Formats acceptés: {', '.join(ImageValidator.ALLOWED_FORMATS)}"

            # Vérifier les dimensions (au moins 100x100)
            width, height = image.size
            if width < 100 or height < 100:
                return False, "Image trop petite. Minimum: 100x100 pixels"

            logger.info(f"Image validée: {image.format}, {width}x{height}, {len(image_bytes)} bytes")
            return True, ""

        except Exception as e:
            logger.error(f"Erreur validation image: {str(e)}")
            return False, f"Image invalide ou corrompue: {str(e)}"


class PrescriptionProcessor:
    """
    Service principal pour traiter une ordonnance complète.
    Orchestre l'OCR et l'extraction de médicaments.
    """

    def __init__(self):
        # Choisir entre Mock, Google Vision et OpenAI selon la configuration
        from django.conf import settings
        vision_mode = getattr(settings, 'GOOGLE_VISION_MODE', 'mock')
        openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)

        self.ocr_service = None
        self.is_openai = False

        if vision_mode == 'openai' and openai_api_key:
            openai_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')
            self.ocr_service = OCRServiceOpenAI(openai_api_key, model=openai_model)
            self.is_openai = True
            logger.info(f"Mode OCR: OpenAI Vision (modèle: {openai_model})")
        else:
            # Fallback vers les anciens services si nécessaire (non implémenté ici pour la clarté)
            self.ocr_service = MockOCRService()
            logger.warning("Mode OCR: Mock (Clé OpenAI manquante ou mode non configuré)")
        
        self.medication_extractor = MedicationExtractor(similarity_threshold=75)
        self.image_validator = ImageValidator()


    def process_prescription(self, image_bytes: bytes) -> Dict:
        """
        Traite une ordonnance complète: validation, OCR, et extraction structurée.
        """
        result = {
            'success': False,
            'text_detected': '',
            'medications': [],
            'medication_ids': [], # La correspondance se fera plus tard
            'error': ''
        }

        try:
            # 1. Valider l'image
            is_valid, error_msg = self.image_validator.validate_image(image_bytes)
            if not is_valid:
                result['error'] = error_msg
                return result

            # 2. Extraire les données (méthode OpenAI ou ancienne méthode)
            if self.is_openai:
                logger.info("Début extraction structurée via OpenAI...")
                openai_result = self.ocr_service.extract_structured_data_from_image(image_bytes)
                
                result['text_detected'] = openai_result.get('raw_text', '')
                
                # OpenAI retourne directement la liste des médicaments
                extracted_meds = openai_result.get('medications', [])

                # NOUVEAU: Matcher les médicaments avec la base de données centrale
                logger.info("Matching des médicaments avec la base de données...")
                from .intelligent_matcher import IntelligentMedicationMatcher
                matcher = IntelligentMedicationMatcher(min_confidence_score=70)
                matched_meds, medication_ids = matcher.match_extracted_medications(extracted_meds)

                result['medications'] = matched_meds
                result['medication_ids'] = medication_ids

            else: # Ancienne méthode (Mock/Google Vision + Fuzzy Search)
                logger.info("Début extraction OCR (ancienne méthode)...")
                text = self.ocr_service.extract_text_from_image(image_bytes)
                result['text_detected'] = text

                if not text:
                    result['error'] = "Aucun texte détecté dans l'image. Vérifiez la qualité de la photo."
                    return result

                logger.info("Début extraction médicaments (ancienne méthode)...")
                medications = self.medication_extractor.extract_medications_from_text(text)
                result['medications'] = medications
                result['medication_ids'] = [med['id'] for med in medications]

            # 3. Vérifier si des médicaments ont été trouvés
            if not result['medications']:
                # Si c'est OpenAI qui n'a rien trouvé, le message est différent
                if self.is_openai:
                     result['error'] = "OpenAI n'a reconnu aucun médicament sur l'ordonnance."
                else:
                     result['error'] = "Aucun médicament reconnu dans l'ordonnance. Vérifiez le texte détecté."
                return result

            # Succès
            result['success'] = True
            logger.info(f"Traitement réussi: {len(result['medications'])} médicaments trouvés via {'OpenAI' if self.is_openai else 'ancienne méthode'}")

        except Exception as e:
            logger.exception(f"Erreur traitement ordonnance: {str(e)}")
            result['error'] = f"Erreur lors du traitement: {str(e)}"

        return result

