
import json
from rest_framework import serializers
from django.utils import timezone
from .models import Pharmacie, Medication, PharmacyMedication
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

class PharmacyCreateSerializer(serializers.ModelSerializer):
    assurances_acceptees = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Pharmacie
        fields = [
            'nom', 'adresse', 'telephone', 'opening_time', 'closing_time', 
            'assurances_acceptees'
        ]

    def create(self, validated_data):
        # Geocode address
        geolocator = Nominatim(user_agent="umbrella-app")
        latitude, longitude = None, None
        try:
            location = geolocator.geocode(validated_data['adresse'])
            if location:
                latitude, longitude = location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderUnavailable):
            # Handle geocoding errors, maybe log them
            pass

        # Handle insurances
        insurances_str = validated_data.pop('assurances_acceptees', '')
        insurances_list = [ins.strip() for ins in insurances_str.split(',') if ins.strip()]

        pharmacy = Pharmacie.objects.create(
            **validated_data,
            latitude=latitude,
            longitude=longitude,
            assurances_acceptees=insurances_list
        )
        return pharmacy

class PharmacieSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    opening_time = serializers.TimeField(format='%H:%M', read_only=True)
    closing_time = serializers.TimeField(format='%H:%M', read_only=True)
    medication_price = serializers.SerializerMethodField(help_text="Price in FCFA cents")
    medication_stock = serializers.SerializerMethodField()
    assurances_acceptees = serializers.SerializerMethodField()

    class Meta:
        model = Pharmacie
        fields = [
            'id', 'nom', 'adresse', 'telephone', 'opening_time', 'closing_time',
            'is_open', 'latitude', 'longitude', 'note', 'assurances_acceptees',
            'assurance_speciale', 'distance_km', 'medication_price', 'medication_stock'
        ]

    def get_assurances_acceptees(self, obj):
        assurances = obj.assurances_acceptees
        if isinstance(assurances, str):
            try:
                return json.loads(assurances)
            except json.JSONDecodeError:
                # If it's a simple string, wrap it in a list
                return [assurances]
        return assurances if assurances is not None else []

    def get_is_open(self, obj):
        if not obj.opening_time or not obj.closing_time:
            return None  # Or False, if you prefer
        
        # Assumes server is in a consistent timezone (e.g., UTC, configured in settings.py)
        current_time = timezone.localtime(timezone.now()).time()

        # Handles overnight case (e.g., 22:00 to 06:00)
        if obj.opening_time > obj.closing_time:
            return current_time >= obj.opening_time or current_time <= obj.closing_time
        # Normal case (e.g., 08:00 to 20:00)
        else:
            return obj.opening_time <= current_time <= obj.closing_time

    def get_distance_km(self, obj):
        # The distance is expected to be annotated on the object by the view.
        distance = getattr(obj, 'distance_km', None)
        return round(distance, 2) if distance is not None else None
        
    def get_medication_price(self, obj):
        # Safely get the annotated attribute
        return getattr(obj, 'medication_price', None)

    def get_medication_stock(self, obj):
        # Safely get the annotated attribute
        return getattr(obj, 'medication_stock', None)

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

class PharmacyMedicationSerializer(serializers.ModelSerializer):
    nom = serializers.CharField(source='medication.nom', read_only=True)
    description = serializers.CharField(source='medication.description', read_only=True)
    dosage = serializers.CharField(source='medication.dosage', read_only=True)
    categorie = serializers.CharField(source='medication.categorie', read_only=True)
    prix = serializers.IntegerField(source='medication.prix', read_only=True)
    stock = serializers.IntegerField(source='stock_disponible')
    pharmacy_medication_price = serializers.IntegerField(source='prix_unitaire')

    class Meta:
        model = PharmacyMedication
        fields = ['id', 'medication', 'nom', 'description', 'dosage', 'categorie', 'prix', 'stock', 'pharmacy_medication_price']
