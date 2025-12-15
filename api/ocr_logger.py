# -*- coding: utf-8 -*-
"""
Logger détaillé pour les scans OCR.
Enregistre chaque scan avec métriques de performance.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class OCRScanLogger:
    """
    Logger spécialisé pour les scans d'ordonnances.
    Enregistre chaque scan dans un fichier JSON pour analyse ultérieure.
    """

    def __init__(self):
        self.log_dir = os.path.join(settings.BASE_DIR, 'ocr_logs')
        os.makedirs(self.log_dir, exist_ok=True)

        # Fichier pour tous les scans
        self.all_scans_file = os.path.join(self.log_dir, 'all_scans.jsonl')

        # Fichier CSV pour métriques rapides
        self.metrics_file = os.path.join(self.log_dir, 'metrics.csv')

        # Initialiser le fichier CSV si n'existe pas
        if not os.path.exists(self.metrics_file):
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                f.write('timestamp,scan_id,mode,medications_detected,avg_confidence,min_confidence,max_confidence,has_low_confidence,processing_time_ms,image_size_bytes,text_length\n')

    def log_scan(self, scan_data: Dict[str, Any]) -> str:
        """
        Enregistre un scan complet avec toutes les métriques.

        Args:
            scan_data: {
                'mode': 'production' ou 'mock',
                'image_size': taille en bytes,
                'text_detected': texte OCR,
                'medications': liste des médicaments détectés,
                'processing_time': temps en ms,
                'success': bool,
                'error': str (si erreur)
            }

        Returns:
            str: ID du scan (timestamp)
        """
        scan_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

        # Calculer métriques
        medications = scan_data.get('medications', [])
        confidences = [med.get('confidence', 0) for med in medications]

        metrics = {
            'scan_id': scan_id,
            'timestamp': datetime.now().isoformat(),
            'mode': scan_data.get('mode', 'unknown'),
            'success': scan_data.get('success', False),
            'error': scan_data.get('error', ''),

            # Métriques image
            'image_size_bytes': scan_data.get('image_size', 0),

            # Métriques OCR
            'text_detected': scan_data.get('text_detected', ''),
            'text_length': len(scan_data.get('text_detected', '')),

            # Métriques extraction
            'medications_count': len(medications),
            'medications': medications,

            # Métriques confiance
            'avg_confidence': round(sum(confidences) / len(confidences), 2) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'has_low_confidence': any(c < 80 for c in confidences),

            # Performance
            'processing_time_ms': scan_data.get('processing_time', 0),
        }

        # Enregistrer dans le fichier JSONL (JSON Lines)
        with open(self.all_scans_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metrics, ensure_ascii=False) + '\n')

        # Enregistrer dans le fichier CSV pour analyse rapide
        with open(self.metrics_file, 'a', encoding='utf-8') as f:
            f.write(f"{metrics['timestamp']},{scan_id},{metrics['mode']},{metrics['medications_count']},{metrics['avg_confidence']},{metrics['min_confidence']},{metrics['max_confidence']},{metrics['has_low_confidence']},{metrics['processing_time_ms']},{metrics['image_size_bytes']},{metrics['text_length']}\n")

        logger.info(f"Scan {scan_id} enregistré: {metrics['medications_count']} médicaments, confiance moyenne: {metrics['avg_confidence']}%")

        return scan_id

    def get_scan_by_id(self, scan_id: str) -> Dict[str, Any]:
        """Récupère un scan par son ID."""
        with open(self.all_scans_file, 'r', encoding='utf-8') as f:
            for line in f:
                scan = json.loads(line)
                if scan['scan_id'] == scan_id:
                    return scan
        return {}

    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les N derniers scans."""
        scans = []
        with open(self.all_scans_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                scans.append(json.loads(line))
        return scans[::-1]  # Plus récent en premier

    def get_statistics(self) -> Dict[str, Any]:
        """Calcule des statistiques globales sur tous les scans."""
        scans = []
        with open(self.all_scans_file, 'r', encoding='utf-8') as f:
            for line in f:
                scans.append(json.loads(line))

        if not scans:
            return {'total_scans': 0}

        total = len(scans)
        successful = sum(1 for s in scans if s['success'])

        all_meds = [med for s in scans for med in s['medications']]
        all_confidences = [med['confidence'] for med in all_meds]

        return {
            'total_scans': total,
            'successful_scans': successful,
            'failed_scans': total - successful,
            'success_rate': round(successful / total * 100, 2),

            'total_medications_detected': len(all_meds),
            'avg_medications_per_scan': round(len(all_meds) / total, 2),

            'avg_confidence_global': round(sum(all_confidences) / len(all_confidences), 2) if all_confidences else 0,
            'min_confidence_global': min(all_confidences) if all_confidences else 0,
            'max_confidence_global': max(all_confidences) if all_confidences else 0,

            'scans_with_low_confidence': sum(1 for s in scans if s['has_low_confidence']),
            'avg_processing_time_ms': round(sum(s['processing_time_ms'] for s in scans) / total, 2),
        }


class OCRTestReporter:
    """
    Générateur de rapports de tests OCR.
    Compare résultats attendus vs obtenus.
    """

    def __init__(self):
        self.log_dir = os.path.join(settings.BASE_DIR, 'ocr_logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.test_results_file = os.path.join(self.log_dir, 'test_results.json')

    def test_scan(
        self,
        image_name: str,
        expected_medications: List[str],
        detected_medications: List[Dict[str, Any]],
        ocr_text: str
    ) -> Dict[str, Any]:
        """
        Compare résultats attendus vs détectés et génère un rapport.

        Args:
            image_name: Nom de l'image testée
            expected_medications: Liste des noms de médicaments attendus
            detected_medications: Liste des médicaments détectés par le système
            ocr_text: Texte OCR complet

        Returns:
            Dict avec métriques de précision
        """
        detected_names = [med['nom'].lower() for med in detected_medications]
        expected_lower = [name.lower() for name in expected_medications]

        # Calculer les métriques
        true_positives = []
        false_positives = []
        false_negatives = []

        # True Positives: médicaments détectés qui sont dans la liste attendue
        for detected in detected_medications:
            name_lower = detected['nom'].lower()
            matched = False
            for expected in expected_lower:
                # Fuzzy match simple: si un mot de expected est dans detected
                if any(word in name_lower for word in expected.split()) or any(word in expected for word in name_lower.split()):
                    true_positives.append({
                        'expected': expected,
                        'detected': detected['nom'],
                        'confidence': detected['confidence']
                    })
                    matched = True
                    break
            if not matched:
                false_positives.append(detected['nom'])

        # False Negatives: médicaments attendus non détectés
        for expected in expected_lower:
            matched = False
            for detected in detected_medications:
                name_lower = detected['nom'].lower()
                if any(word in name_lower for word in expected.split()) or any(word in expected for word in name_lower.split()):
                    matched = True
                    break
            if not matched:
                false_negatives.append(expected)

        # Calculer métriques
        precision = len(true_positives) / (len(true_positives) + len(false_positives)) if (len(true_positives) + len(false_positives)) > 0 else 0
        recall = len(true_positives) / (len(true_positives) + len(false_negatives)) if (len(true_positives) + len(false_negatives)) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        result = {
            'timestamp': datetime.now().isoformat(),
            'image_name': image_name,
            'expected_count': len(expected_medications),
            'detected_count': len(detected_medications),
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'precision': round(precision * 100, 2),
            'recall': round(recall * 100, 2),
            'f1_score': round(f1_score * 100, 2),
            'ocr_text_preview': ocr_text[:200] + '...' if len(ocr_text) > 200 else ocr_text,
        }

        # Sauvegarder
        self._save_test_result(result)

        return result

    def _save_test_result(self, result: Dict[str, Any]):
        """Sauvegarde un résultat de test."""
        results = []
        if os.path.exists(self.test_results_file):
            with open(self.test_results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

        results.append(result)

        with open(self.test_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def generate_summary_report(self) -> str:
        """Génère un rapport texte lisible de tous les tests."""
        if not os.path.exists(self.test_results_file):
            return "Aucun test effectué."

        with open(self.test_results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)

        if not results:
            return "Aucun test effectué."

        report = []
        report.append("=" * 80)
        report.append("RAPPORT DE TESTS OCR")
        report.append("=" * 80)
        report.append(f"Total de tests: {len(results)}")
        report.append("")

        # Statistiques globales
        avg_precision = sum(r['precision'] for r in results) / len(results)
        avg_recall = sum(r['recall'] for r in results) / len(results)
        avg_f1 = sum(r['f1_score'] for r in results) / len(results)

        report.append("MÉTRIQUES GLOBALES:")
        report.append(f"  Précision moyenne: {avg_precision:.2f}%")
        report.append(f"  Rappel moyen: {avg_recall:.2f}%")
        report.append(f"  F1-Score moyen: {avg_f1:.2f}%")
        report.append("")

        # Détail de chaque test
        for i, result in enumerate(results, 1):
            report.append("-" * 80)
            report.append(f"TEST #{i} - {result['image_name']}")
            report.append(f"Date: {result['timestamp']}")
            report.append("")
            report.append(f"Médicaments attendus: {result['expected_count']}")
            report.append(f"Médicaments détectés: {result['detected_count']}")
            report.append("")
            report.append(f"✅ Vrais Positifs ({len(result['true_positives'])}):")
            for tp in result['true_positives']:
                report.append(f"   - Attendu: {tp['expected']}")
                report.append(f"     Détecté: {tp['detected']} (confiance: {tp['confidence']}%)")

            if result['false_positives']:
                report.append(f"\n❌ Faux Positifs ({len(result['false_positives'])}):")
                for fp in result['false_positives']:
                    report.append(f"   - {fp} (détecté à tort)")

            if result['false_negatives']:
                report.append(f"\n⚠️  Faux Négatifs ({len(result['false_negatives'])}):")
                for fn in result['false_negatives']:
                    report.append(f"   - {fn} (non détecté)")

            report.append(f"\n📊 Métriques:")
            report.append(f"   Précision: {result['precision']:.2f}%")
            report.append(f"   Rappel: {result['recall']:.2f}%")
            report.append(f"   F1-Score: {result['f1_score']:.2f}%")
            report.append("")

        report.append("=" * 80)

        return '\n'.join(report)


# Instances globales
scan_logger = OCRScanLogger()
test_reporter = OCRTestReporter()
