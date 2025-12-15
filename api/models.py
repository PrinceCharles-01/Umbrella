
from django.db import models

class Pharmacie(models.Model):
    nom = models.CharField(max_length=255, db_index=True)  # Index pour recherche rapide
    adresse = models.TextField()
    telephone = models.CharField(max_length=20, blank=True, null=True)
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True, db_index=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True, db_index=True)
    note = models.DecimalField(max_digits=2, decimal_places=1, default=0.0, db_index=True)  # Index pour tri par note
    assurances_acceptees = models.JSONField(blank=True, null=True)
    assurance_speciale = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']  # Ordre alphabétique par défaut
        verbose_name = 'Pharmacie'
        verbose_name_plural = 'Pharmacies'
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='location_idx'),
            models.Index(fields=['note'], name='rating_idx'),
        ]

    def __str__(self):
        return self.nom

class Medication(models.Model):
    nom = models.CharField(max_length=255, db_index=True)  # Index pour recherche rapide
    dci = models.CharField('Dénomination Commune Internationale', max_length=255, blank=True, null=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    categorie = models.CharField(max_length=100, blank=True, null=True, db_index=True)  # Index pour filtrer par catégorie
    # Storing price in cents to avoid floating point issues
    prix = models.IntegerField()  # In FCFA cents
    min_stock = models.IntegerField(default=0)  # New field for minimum stock
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']  # Ordre alphabétique par défaut
        verbose_name = 'Médicament'
        verbose_name_plural = 'Médicaments'
        indexes = [
            models.Index(fields=['nom'], name='medication_name_idx'),
            models.Index(fields=['categorie'], name='medication_category_idx'),
        ]

    def __str__(self):
        return self.nom

class PharmacyMedication(models.Model):
    pharmacy = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name='stock_items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='pharmacy_stocks')
    stock_disponible = models.IntegerField(default=0, db_index=True)  # Index pour filtrer les stocks > 0
    # Storing price in cents to avoid floating point issues
    prix_unitaire = models.IntegerField()  # In FCFA cents

    class Meta:
        unique_together = ('pharmacy', 'medication')
        verbose_name = 'Stock Pharmacie-Médicament'
        verbose_name_plural = 'Stocks Pharmacie-Médicament'
        indexes = [
            models.Index(fields=['pharmacy', 'medication'], name='pharmacy_med_idx'),
            models.Index(fields=['stock_disponible'], name='stock_idx'),
        ]

    def __str__(self):
        return f'{self.medication.nom} at {self.pharmacy.nom}'
