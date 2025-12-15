
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def home(request):
    """Page d'accueil de l'API Umbrella"""
    return JsonResponse({
        'status': 'online',
        'service': 'Umbrella API',
        'version': '1.0.0',
        'endpoints': {
            'api': '/api/',
            'admin': '/admin/',
            'pharmacies': '/api/pharmacies/',
            'medications': '/api/medications/',
            'scan': '/api/scan/',
            'health': '/health/',
        },
        'documentation': 'https://github.com/PrinceCharles-01/Umbrella'
    })

@require_http_methods(["GET"])
def health_check(request):
    """Endpoint de santé pour Railway"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'umbrella-api'
    })

urlpatterns = [
    path('', home, name='home'),
    path('health/', health_check, name='health'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
