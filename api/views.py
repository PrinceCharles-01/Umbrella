
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db.models import Count, F, OuterRef, Subquery
from geopy.distance import geodesic
import openrouteservice
import requests
import json
import logging

from .models import Pharmacie, Medication, PharmacyMedication
from .serializers import PharmacieSerializer, MedicationSerializer, PharmacyMedicationSerializer, PharmacyCreateSerializer
from .pagination import StandardResultsSetPagination, LargeResultsSetPagination
from .services import PrescriptionProcessor
from .ocr_logger import scan_logger
import time

# Configuration du logger
logger = logging.getLogger(__name__)

class PharmacieViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les pharmacies.
    Supporte la pagination et le filtrage par médicament et localisation.
    """
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return PharmacyCreateSerializer
        return PharmacieSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned pharmacies to a given user's
        location, by filtering against a `lat` and `lon` query parameter
        in the URL.
        
        Also filters for a specific `medication_id` if provided, and annotates
        the price and stock for that medication.
        """
        queryset = Pharmacie.objects.all()
        lat = self.request.query_params.get('lat')
        lon = self.request.query_params.get('lon')
        medication_id = self.request.query_params.get('medication_id')

        if medication_id:
            # Create subqueries to get price and stock for the specific medication
            price_subquery = PharmacyMedication.objects.filter(
                pharmacy=OuterRef('pk'),
                medication_id=medication_id
            ).values('prix_unitaire')[:1]

            stock_subquery = PharmacyMedication.objects.filter(
                pharmacy=OuterRef('pk'),
                medication_id=medication_id
            ).values('stock_disponible')[:1]

            # Filter pharmacies that have the medication and annotate the price and stock
            queryset = queryset.filter(
                stock_items__medication_id=medication_id,
                stock_items__stock_disponible__gt=0  # Only show if in stock
            ).annotate(
                medication_price=Subquery(price_subquery),
                medication_stock=Subquery(stock_subquery)
            )

        if lat and lon:
            try:
                user_location = (float(lat), float(lon))
                # The queryset is now a Django QuerySet, not a list, so we can't iterate here
                # The distance calculation needs to happen after the main queryset is built
                # We will do it on the evaluated queryset
                
                # Evaluate the queryset to a list
                pharmacies_list = list(queryset)

                for pharmacie in pharmacies_list:
                    if pharmacie.latitude and pharmacie.longitude:
                        pharmacie_location = (pharmacie.latitude, pharmacie.longitude)
                        pharmacie.distance_km = geodesic(user_location, pharmacie_location).km
                    else:
                        pharmacie.distance_km = None
                
                # Filter out pharmacies without a calculated distance and sort
                pharmacies_list = [p for p in pharmacies_list if p.distance_km is not None]
                pharmacies_list.sort(key=lambda p: p.distance_km)
                
                return pharmacies_list # Return the sorted list

            except (ValueError, TypeError):
                # Ignore invalid lat/lon parameters
                pass
        
        return queryset

    @action(detail=True, methods=['get'])
    def stocks(self, request, pk=None):
        """
        Return the stock for a specific pharmacy.
        """
        pharmacy = self.get_object()
        queryset = PharmacyMedication.objects.filter(pharmacy=pharmacy)
        serializer = PharmacyMedicationSerializer(queryset, many=True)
        return Response(serializer.data)

class RouteView(APIView):
    """
    Vue pour obtenir l'itinéraire entre l'utilisateur et une pharmacie.
    Utilise l'API OpenRouteService.
    """
    def get(self, request, pk, *args, **kwargs):
        try:
            pharmacy = Pharmacie.objects.get(pk=pk)
        except Pharmacie.DoesNotExist:
            logger.warning(f"Tentative d'accès à une pharmacie inexistante: {pk}")
            return Response(
                {'error': 'Pharmacie introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_lat = request.query_params.get('lat')
        user_lon = request.query_params.get('lon')
        api_key = settings.OPENROUTESERVICE_API_KEY

        # Validation des paramètres
        if not all([user_lat, user_lon]):
            return Response(
                {'error': 'Votre position est requise pour calculer l\'itinéraire'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not all([pharmacy.latitude, pharmacy.longitude]):
            logger.error(f"Pharmacie {pk} n'a pas de coordonnées GPS")
            return Response(
                {'error': 'Les coordonnées de cette pharmacie ne sont pas disponibles'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not api_key or api_key == 'YOUR_ORS_API_KEY':
            logger.critical("Clé API OpenRouteService non configurée")
            return Response(
                {'error': 'Service d\'itinéraire temporairement indisponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            # Validation des coordonnées
            try:
                user_lat_float = float(user_lat)
                user_lon_float = float(user_lon)
            except ValueError:
                return Response(
                    {'error': 'Coordonnées invalides'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            client = openrouteservice.Client(key=api_key)

            coords = (
                (float(pharmacy.longitude), float(pharmacy.latitude)),
                (user_lon_float, user_lat_float)
            )

            routes = client.directions(
                coordinates=coords,
                profile='driving-car',
                format='geojson'
            )

            # Extraction de la géométrie
            if 'features' in routes and len(routes['features']) > 0:
                geometry = routes['features'][0]['geometry']
                return Response({'geometry': geometry}, status=status.HTTP_200_OK)
            else:
                logger.error("Réponse OpenRouteService invalide")
                return Response(
                    {'error': 'Impossible de calculer l\'itinéraire'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except openrouteservice.exceptions.ApiError as e:
            logger.error(f"Erreur API OpenRouteService: {str(e)}")
            return Response(
                {'error': 'Service d\'itinéraire temporairement indisponible'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.exception(f"Erreur inattendue lors du calcul d'itinéraire: {str(e)}")
            return Response(
                {'error': 'Une erreur inattendue s\'est produite'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MedicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les médicaments.
    Supporte la pagination et la recherche.
    """
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer
    pagination_class = LargeResultsSetPagination

class PharmacyMedicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les associations pharmacie-médicament.
    Optimisé avec select_related pour éviter les requêtes N+1.
    """
    serializer_class = PharmacyMedicationSerializer

    def get_queryset(self):
        # Optimisation: charger les pharmacies et médicaments en une seule requête
        return PharmacyMedication.objects.select_related(
            'pharmacy',
            'medication'
        ).all()

class FindPharmaciesByMedicationsView(APIView):
    """
    API view to find and sort pharmacies based on a list of medications.
    Accepts a POST request with a list of medication IDs.
    """
    def post(self, request, *args, **kwargs):
        medication_ids = request.data.get('medication_ids', [])

        # Validation des données
        if not medication_ids:
            return Response(
                {'error': 'Veuillez sélectionner au moins un médicament'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(medication_ids, list):
            return Response(
                {'error': 'Le format de la liste de médicaments est invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que les IDs sont valides
        try:
            medication_ids = [int(mid) for mid in medication_ids]
        except (ValueError, TypeError):
            return Response(
                {'error': 'Identifiants de médicaments invalides'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Try to find pharmacies that have ALL requested medications
            all_meds_pharmacies = Pharmacie.objects.filter(
                stock_items__medication_id__in=medication_ids,
                stock_items__stock_disponible__gt=0
            ).annotate(
                distinct_med_count=Count('stock_items__medication_id', distinct=True)
            ).filter(distinct_med_count=len(medication_ids))

            if all_meds_pharmacies.exists():
                pharmacies_to_serialize = all_meds_pharmacies
            else:
                # 2. If no pharmacies have all, find pharmacies with MOST requested medications
                pharmacies_to_serialize = Pharmacie.objects.filter(
                    stock_items__medication_id__in=medication_ids,
                    stock_items__stock_disponible__gt=0
                ).annotate(
                    match_count=Count('stock_items__medication_id', distinct=True)
                ).order_by('-match_count')

            # Vérifier si on a trouvé des résultats
            if not pharmacies_to_serialize.exists():
                logger.info(f"Aucune pharmacie trouvée pour les médicaments: {medication_ids}")
                return Response(
                    {
                        'message': 'Aucune pharmacie ne possède ces médicaments en stock',
                        'results': []
                    },
                    status=status.HTTP_200_OK
                )

            # Serialize the data
            serializer = PharmacieSerializer(pharmacies_to_serialize, many=True)

            # Add the match_count and medication details to each pharmacy in the serialized data
            response_data = []
            pharmacy_meds = PharmacyMedication.objects.filter(
                pharmacy__in=pharmacies_to_serialize,
                medication_id__in=medication_ids
            ).select_related('medication')

            pharmacies_data = serializer.data

            for pharmacy_data in pharmacies_data:
                pharmacy_instance = next((p for p in pharmacies_to_serialize if p.id == pharmacy_data['id']), None)
                if pharmacy_instance:
                    count_attribute = getattr(pharmacy_instance, 'match_count', getattr(pharmacy_instance, 'distinct_med_count', 0))
                    pharmacy_data['match_count'] = count_attribute
                    pharmacy_data['total_meds_in_search'] = len(medication_ids)

                    # Attach medications found in this pharmacy
                    meds_in_pharmacy = [pm for pm in pharmacy_meds if pm.pharmacy_id == pharmacy_instance.id]
                    pharmacy_data['medications'] = PharmacyMedicationSerializer(meds_in_pharmacy, many=True).data

                response_data.append(pharmacy_data)

            logger.info(f"Trouvé {len(response_data)} pharmacies pour {len(medication_ids)} médicaments")
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Erreur lors de la recherche multi-médicaments: {str(e)}")
            return Response(
                {'error': 'Une erreur est survenue lors de la recherche'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def scan_prescription_view(request):
    """
    Endpoint pour scanner une ordonnance et extraire les médicaments.
    
    Accepte une image (multipart/form-data) et retourne:
    - Le texte détecté par OCR
    - Les médicaments extraits
    - Les pharmacies qui ont ces médicaments
    
    POST /api/scan-prescription/
    Body (form-data):
        - image: File (JPEG, PNG, max 10MB)
    
    Returns:
        {
            "success": true,
            "text_detected": "...",
            "medications": [
                {
                    "id": 1,
                    "nom": "Doliprane 1000mg",
                    "dosage": "1000mg",
                    "categorie": "Antalgique",
                    "confidence": 95,
                    "matched_text": "DOLIPRANE"
                }
            ],
            "pharmacies": [...],  # Pharmacies qui ont ces médicaments
            "message": "3 médicaments détectés"
        }
    """
    logger.info("Requête de scan d'ordonnance reçue")
    
    # Vérifier qu'une image a été envoyée
    if 'image' not in request.FILES:
        logger.warning("Aucune image dans la requête")
        return Response(
            {'error': 'Aucune image fournie. Veuillez envoyer un fichier image.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    image_file = request.FILES['image']
    
    try:
        # Lire le contenu de l'image
        image_bytes = image_file.read()
        logger.info(f"Image reçue: {image_file.name}, taille: {len(image_bytes)} bytes")

        # Démarrer le chronomètre
        start_time = time.time()

        # Traiter l'ordonnance
        processor = PrescriptionProcessor()
        result = processor.process_prescription(image_bytes)

        # Calculer le temps de traitement
        processing_time = int((time.time() - start_time) * 1000)  # en ms
        
        # Si erreur pendant le traitement
        if not result['success']:
            logger.warning(f"Aucun médicament matché: {result['error']}")

            # Si on a au moins extrait du texte OCR, c'est quand même un succès partiel
            text_detected = result.get('text_detected', '')

            # Logger le scan
            from django.conf import settings
            scan_logger.log_scan({
                'mode': getattr(settings, 'GOOGLE_VISION_MODE', 'mock'),
                'image_size': len(image_bytes),
                'text_detected': text_detected,
                'medications': [],
                'processing_time': processing_time,
                'success': bool(text_detected),  # Succès si texte extrait
                'error': result['error'] if not text_detected else None
            })

            # Si vraiment aucun texte n'a été extrait, erreur
            if not text_detected:
                return Response(
                    {
                        'success': False,
                        'error': result['error'],
                        'text_detected': '',
                        'medications': [],
                        'medication_ids': []
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Sinon, retourner succès avec texte mais sans médicaments matchés
            return Response(
                {
                    'success': True,
                    'text_detected': text_detected,
                    'medications': [],
                    'medication_ids': [],
                    'message': 'Texte extrait avec succès, mais aucun médicament correspondant trouvé dans la base de données.',
                    'warning': result['error']
                },
                status=status.HTTP_200_OK
            )
        
        # Rechercher les pharmacies qui ont ces médicaments
        medication_ids = result['medication_ids']
        pharmacies = []
        
        if medication_ids:
            try:
                # Réutiliser la logique de recherche multi-médicaments
                pharmacies_queryset = Pharmacie.objects.filter(
                    stock_items__medication_id__in=medication_ids,
                    stock_items__stock_disponible__gt=0
                ).annotate(
                    match_count=Count('stock_items__medication_id', distinct=True)
                ).order_by('-match_count')
                
                # Sérialiser
                pharmacy_serializer = PharmacieSerializer(pharmacies_queryset, many=True)
                
                # Enrichir avec les médicaments
                pharmacy_meds = PharmacyMedication.objects.filter(
                    pharmacy__in=pharmacies_queryset,
                    medication_id__in=medication_ids
                ).select_related('medication')
                
                pharmacies = pharmacy_serializer.data
                for pharmacy_data in pharmacies:
                    pharmacy_instance = next(
                        (p for p in pharmacies_queryset if p.id == pharmacy_data['id']),
                        None
                    )
                    if pharmacy_instance:
                        match_count = getattr(pharmacy_instance, 'match_count', 0)
                        pharmacy_data['match_count'] = match_count
                        pharmacy_data['total_meds_in_search'] = len(medication_ids)
                        
                        # Médicaments dans cette pharmacie
                        meds_in_pharmacy = [
                            pm for pm in pharmacy_meds 
                            if pm.pharmacy_id == pharmacy_instance.id
                        ]
                        pharmacy_data['medications'] = PharmacyMedicationSerializer(
                            meds_in_pharmacy, 
                            many=True
                        ).data
                
                logger.info(f"Trouvé {len(pharmacies)} pharmacies pour les médicaments détectés")
            
            except Exception as e:
                logger.exception(f"Erreur recherche pharmacies: {str(e)}")
                # On continue quand même, on retourne juste les médicaments sans pharmacies
        
        # Construire la réponse finale
        response_data = {
            'success': True,
            'text_detected': result['text_detected'],
            'medications': result['medications'],
            'medication_ids': medication_ids,
            'pharmacies': pharmacies,
            'message': f"{len(result['medications'])} médicament(s) détecté(s)"
        }

        # Logger le scan pour analyse
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

        logger.info(f"Scan réussi: {len(result['medications'])} médicaments, {len(pharmacies)} pharmacies, {processing_time}ms")
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors du scan: {str(e)}")
        return Response(
            {
                'success': False,
                'error': f"Erreur lors du traitement de l'ordonnance: {str(e)}",
                'medications': []
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def extract_medications_from_text_view(request):
    """
    Endpoint pour extraire les médicaments depuis un texte OCR validé.

    Accepte un texte (JSON) et retourne les médicaments extraits.

    POST /api/extract-medications-from-text/
    Body (JSON):
        {
            "text": "DOLIPRANE 1000mg\n1 comprimé matin et soir\n..."
        }

    Returns:
        {
            "success": true,
            "text_detected": "...",
            "medications": [...],
            "medication_ids": [1, 2, 3],
            "message": "3 médicament(s) détecté(s)"
        }
    """
    logger.info("Requête d'extraction de médicaments depuis texte reçue")

    # Vérifier que le texte est fourni
    text = request.data.get('text', '')

    if not text or not text.strip():
        logger.warning("Aucun texte fourni")
        return Response(
            {'error': 'Aucun texte fourni. Veuillez envoyer du texte.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Démarrer le chronomètre
        start_time = time.time()

        # Parser le texte pour extraire les noms de médicaments
        # Le texte vient soit d'OpenAI (format: "Nom dosage - ...") soit de l'utilisateur
        import re
        lines = text.strip().split('\n')
        extracted_meds = []

        for line in lines:
            # Format OpenAI: "Doliprane 1000mg - fréquence"
            # Format utilisateur: "DOLIPRANE 1000mg"
            match = re.match(r'^([A-Za-zéèêëàâäùûüôöîïç\s]+)\s*(\d+\s*(?:mg|g|ml|mcg|ui))?', line.strip())
            if match:
                name = match.group(1).strip()
                dosage = match.group(2).strip() if match.group(2) else ""
                if name and len(name) > 2:  # Ignorer les lignes trop courtes
                    extracted_meds.append({
                        "name": name,
                        "dosage": dosage,
                        "frequency": ""
                    })

        # Utiliser le matcher intelligent
        from .intelligent_matcher import IntelligentMedicationMatcher
        matcher = IntelligentMedicationMatcher(min_confidence_score=70)
        medications, medication_ids = matcher.match_extracted_medications(extracted_meds)

        # Calculer le temps de traitement
        processing_time = int((time.time() - start_time) * 1000)  # en ms

        # Construire la réponse
        response_data = {
            'success': True,
            'text_detected': text,
            'medications': medications,
            'medication_ids': medication_ids,
            'message': f"{len(medications)} médicament(s) détecté(s)" if medications else "Aucun médicament détecté"
        }

        logger.info(f"Extraction réussie: {len(medications)} médicaments extraits en {processing_time}ms")
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"Erreur inattendue lors de l'extraction: {str(e)}")
        return Response(
            {
                'success': False,
                'error': f"Erreur lors de l'extraction des médicaments: {str(e)}",
                'medications': []
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def ocr_statistics_view(request):
    """
    Endpoint pour obtenir les statistiques OCR.

    GET /api/ocr-statistics/

    Query params:
        - recent: nombre de scans récents à afficher (défaut: 10)

    Returns:
        {
            "statistics": {
                "total_scans": 42,
                "successful_scans": 40,
                "failed_scans": 2,
                "success_rate": 95.24,
                "total_medications_detected": 120,
                "avg_medications_per_scan": 2.86,
                "avg_confidence_global": 87.5,
                "avg_processing_time_ms": 2340
            },
            "recent_scans": [...]
        }
    """
    try:
        # Obtenir le nombre de scans récents demandés
        recent_count = int(request.GET.get('recent', 10))

        # Obtenir les statistiques
        statistics = scan_logger.get_statistics()

        # Obtenir les scans récents
        recent_scans = scan_logger.get_recent_scans(limit=recent_count)

        return Response({
            'statistics': statistics,
            'recent_scans': recent_scans
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"Erreur récupération statistiques OCR: {str(e)}")
        return Response(
            {'error': f"Erreur lors de la récupération des statistiques: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
