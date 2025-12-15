# -*- coding: utf-8 -*-
"""
Module de matching intelligent pour associer les médicaments extraits
avec la base de données centrale.
"""
import re
import logging
from typing import List, Dict, Tuple, Optional
from fuzzywuzzy import fuzz

from .models import Medication

logger = logging.getLogger(__name__)

# Import du dictionnaire de synonymes depuis services.py
from .services import BRAND_TO_DCI


class IntelligentMedicationMatcher:
    """
    Système de matching intelligent pour associer les médicaments extraits
    (par OpenAI ou OCR) avec la base de données centrale Medication.

    Utilise fuzzy matching + vérification dosage + synonymes DCI + déduplication.
    """

    def __init__(self, min_confidence_score: int = 70):
        """
        Args:
            min_confidence_score: Score minimum (0-100) pour accepter un match
        """
        self.min_confidence_score = min_confidence_score

    def match_extracted_medications(self, extracted_meds: List[Dict]) -> Tuple[List[Dict], List[int]]:
        """
        Matche les médicaments extraits (OpenAI/OCR) avec la base de données centrale.

        Args:
            extracted_meds: Liste de médicaments extraits par OpenAI
                Format: [{"name": "Doliprane", "dosage": "1000mg", "frequency": "..."}]

        Returns:
            Tuple[List[Dict], List[int]]:
                - Liste enrichie avec IDs et infos DB
                - Liste des medication_ids (pour recherche pharmacies)
        """
        logger.info(f"🔍 Début matching intelligent pour {len(extracted_meds)} médicaments...")

        # Récupérer tous les médicaments de la DB
        all_medications = list(Medication.objects.all())
        logger.info(f"📚 Base de données: {len(all_medications)} médicaments disponibles")

        matched_medications = []
        matched_ids = set()  # Pour éviter les doublons

        for extracted_med in extracted_meds:
            name = extracted_med.get('name', '').strip()
            dosage = extracted_med.get('dosage', '').strip()
            frequency = extracted_med.get('frequency', '')

            if not name:
                logger.warning("⚠️ Médicament sans nom ignoré")
                continue

            # Chercher le meilleur match dans la DB
            best_match = self._find_best_match(name, dosage, all_medications)

            if best_match and best_match['score'] >= self.min_confidence_score:
                med_id = best_match['medication'].id

                # Éviter les doublons (ex: Doliprane ET Paracétamol)
                if med_id in matched_ids:
                    logger.info(f"🔁 Doublon détecté: {name} → déjà matché (ID: {med_id})")
                    continue

                matched_ids.add(med_id)

                # Construire l'objet enrichi
                matched_medications.append({
                    'id': med_id,
                    'nom': best_match['medication'].nom,
                    'dci': getattr(best_match['medication'], 'dci', '') or '',
                    'dosage': best_match['medication'].dosage or '',
                    'dosage_detected': dosage,
                    'frequency': frequency,
                    'confidence': best_match['score'],
                    'matched_text': name,
                    'categorie': getattr(best_match['medication'], 'categorie', ''),
                    'description': getattr(best_match['medication'], 'description', ''),
                })

                logger.info(f"✅ Matché: '{name}' → {best_match['medication'].nom} (score: {best_match['score']})")
            else:
                score = best_match['score'] if best_match else 0
                logger.warning(f"❌ Pas de match: '{name}' (meilleur score: {score})")

        medication_ids = list(matched_ids)
        logger.info(f"🎯 Matching terminé: {len(matched_medications)} médicaments matchés (IDs: {medication_ids})")

        return matched_medications, medication_ids

    def _find_best_match(self, name: str, dosage: str, all_medications: List) -> Optional[Dict]:
        """
        Trouve le meilleur match pour un nom de médicament dans la base de données.

        Scoring multi-critères:
        - Nom exact: 100 points
        - DCI exact: 95 points
        - Fuzzy nom > 85%: 80-95 points
        - Dosage match: +10 points
        - Dosage mismatch: -30 points

        Returns:
            Dict: {'medication': Medication, 'score': int} ou None
        """
        name_normalized = self._normalize_name(name)
        dosage_normalized = self._normalize_dosage(dosage)

        best_match = None
        best_score = 0

        for med in all_medications:
            score = 0

            med_name = med.nom.lower()
            med_name_normalized = self._normalize_name(med.nom)
            med_dci = (med.dci or '').lower()
            med_dosage = self._normalize_dosage(med.dosage or '')

            # Extraire le premier mot du nom du médicament en DB
            # Ex: "Doliprane 1000mg" → "doliprane"
            med_name_first_word = med_name_normalized.split()[0] if med_name_normalized else ''

            # 1. Vérifier correspondance exacte (nom complet)
            if name_normalized == med_name_normalized:
                score = 100

            # 1b. Vérifier correspondance exacte (premier mot)
            elif name_normalized == med_name_first_word:
                score = 100

            # 1c. Vérifier si le nom cherché est contenu dans le nom DB
            elif name_normalized in med_name_normalized or med_name_first_word in name_normalized:
                score = 95

            # 2. Vérifier correspondance exacte (DCI)
            elif med_dci and name_normalized == self._normalize_name(med_dci):
                score = 95

            # 3. Vérifier les synonymes (via dictionnaire)
            elif name_normalized in BRAND_TO_DCI:
                # Le nom détecté est une marque connue
                dci_detected = BRAND_TO_DCI[name_normalized]
                if med_dci and self._normalize_name(med_dci) == dci_detected:
                    score = 95
                elif dci_detected in med_name_normalized or dci_detected in med_name_first_word:
                    score = 90

            # 4. Fuzzy matching sur le nom
            else:
                # Comparer avec le nom complet ET le premier mot
                similarity_full = fuzz.token_sort_ratio(name_normalized, med_name_normalized)
                similarity_first_word = fuzz.ratio(name_normalized, med_name_first_word)
                similarity_partial = fuzz.partial_ratio(name_normalized, med_name_normalized)
                similarity_dci = fuzz.token_sort_ratio(name_normalized, med_dci) if med_dci else 0

                # Prendre la meilleure similarité
                max_similarity = max(similarity_full, similarity_first_word, similarity_partial, similarity_dci)

                if max_similarity >= 75:  # Seuil abaissé de 85 à 75
                    score = max_similarity
                else:
                    continue  # Pas assez similaire, ignorer

            # 5. Bonus/Malus selon le dosage
            if dosage_normalized and med_dosage:
                if dosage_normalized == med_dosage:
                    score += 10  # Bonus si dosage exact
                elif self._dosage_compatible(dosage_normalized, med_dosage):
                    score += 5   # Petit bonus si compatible
                else:
                    score -= 30  # Malus si dosage incompatible
            elif dosage_normalized and not med_dosage:
                # Dosage détecté mais pas dans la DB, vérifier si c'est dans le nom
                if dosage_normalized in med_name_normalized:
                    score += 10

            # Mettre à jour le meilleur match
            if score > best_score:
                best_score = score
                best_match = {
                    'medication': med,
                    'score': min(score, 100)  # Limiter à 100
                }

        return best_match

    def _normalize_name(self, name: str) -> str:
        """Normalise un nom de médicament (minuscules, sans accents, sans espaces)."""
        if not name:
            return ''

        name = name.lower().strip()

        # Supprimer les accents
        replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ô': 'o', 'ö': 'o',
            'î': 'i', 'ï': 'i',
            'ç': 'c'
        }
        for accented, normal in replacements.items():
            name = name.replace(accented, normal)

        # Supprimer les espaces multiples et trimmer
        name = ' '.join(name.split())

        return name

    def _normalize_dosage(self, dosage: str) -> str:
        """
        Normalise un dosage pour comparaison.
        Ex: "1000 mg" → "1000mg", "1g" → "1000mg"
        """
        if not dosage:
            return ''

        dosage = dosage.lower().strip().replace(' ', '')

        # Conversion g → mg
        match_g = re.match(r'^(\d+(?:\.\d+)?)g$', dosage)
        if match_g:
            value = float(match_g.group(1))
            dosage = f"{int(value * 1000)}mg"

        return dosage

    def _dosage_compatible(self, dosage1: str, dosage2: str) -> bool:
        """
        Vérifie si deux dosages sont compatibles (même ordre de grandeur).
        Ex: "1000mg" et "1g" sont compatibles
        """
        if not dosage1 or not dosage2:
            return False

        # Extraire les valeurs numériques
        match1 = re.match(r'^(\d+(?:\.\d+)?)(mg|g|ml|mcg|ui)', dosage1)
        match2 = re.match(r'^(\d+(?:\.\d+)?)(mg|g|ml|mcg|ui)', dosage2)

        if not match1 or not match2:
            return False

        val1, unit1 = float(match1.group(1)), match1.group(2)
        val2, unit2 = float(match2.group(1)), match2.group(2)

        # Unités différentes mais valeurs proches (tolérance 20%)
        if unit1 == unit2:
            ratio = val1 / val2 if val2 > 0 else 0
            return 0.8 <= ratio <= 1.2

        return False
