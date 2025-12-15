
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    PharmacieViewSet,
    MedicationViewSet,
    PharmacyMedicationViewSet,
    FindPharmaciesByMedicationsView,
    RouteView,
    scan_prescription_view,
    extract_medications_from_text_view,
    ocr_statistics_view
)
from orders.views import OrderViewSet

router = DefaultRouter()
router.register(r'pharmacies', PharmacieViewSet, basename='pharmacie')
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'pharmacy-medications', PharmacyMedicationViewSet, basename='pharmacy-medication')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('pharmacies/<int:pk>/route/', RouteView.as_view(), name='pharmacy-route'),
    path('pharmacies/find-by-medications/', FindPharmaciesByMedicationsView.as_view(), name='find-pharmacies-by-medications'),
    path('scan-prescription/', scan_prescription_view, name='scan-prescription'),
    path('extract-medications-from-text/', extract_medications_from_text_view, name='extract-medications-from-text'),
    path('ocr-statistics/', ocr_statistics_view, name='ocr-statistics'),
] + router.urls
