from django.contrib import admin
from .models import Pharmacie, Medication, PharmacyMedication

# Register your models here.
admin.site.register(Pharmacie)
admin.site.register(Medication)
admin.site.register(PharmacyMedication)
