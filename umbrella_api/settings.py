
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-a-dummy-key-for-development'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'corsheaders',

    # Local apps
    'api',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'umbrella_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'umbrella_api.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': r'C:\Users\Charles\Desktop\Umbrella-1\django-backend\db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'Africa/Libreville'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# OpenRouteService API Key
# Get your key from https://openrouteservice.org/
OPENROUTESERVICE_API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjkwYjQ0NmYwNTRkZDRhY2FhZWI0Yzg5NTNkNDZmOTkwIiwiaCI6Im11cm11cjY0In0=' # <<< REPLACE WITH YOUR ACTUAL KEY

# ============================================================================
# OCR CONFIGURATION (Google Vision + OpenAI Vision)
# ============================================================================

import os

# OpenAI Vision Configuration (RECOMMANDÉ - Meilleur pour manuscrit)
# Obtenez votre clé sur: https://platform.openai.com/api-keys
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')  # Définir via variable d'environnement

# Modèle OpenAI à utiliser pour l'OCR
# Options: 'gpt-4o' (meilleur qualité) ou 'gpt-4o-mini' (plus rapide/économique)
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')  # Default: gpt-4o pour qualité maximale

# Google Cloud Vision Configuration (Alternative)
# API Key pour Google Vision (méthode simplifiée)
# DESACTIVE car facturation bloquée - On utilise OpenAI à la place
GOOGLE_VISION_API_KEY = ''  # 'AIzaSyA6KimZUFa3pXNWxSRds91aEqdQVD63UNU'

# Chemin vers le fichier de credentials JSON (méthode alternative)
GOOGLE_VISION_CREDENTIALS = os.path.join(BASE_DIR, 'google-vision-credentials.json')

# Déterminer le mode de fonctionnement OCR
# Priorité: OpenAI > Google Vision API Key > Google Vision Credentials > Mock
if OPENAI_API_KEY:
    # Mode: OpenAI Vision (recommandé pour manuscrit)
    GOOGLE_VISION_MODE = 'openai'
    import logging
    logging.info("Mode OCR: OpenAI Vision activé")
elif GOOGLE_VISION_API_KEY:
    # Mode: production avec API Key Google Vision
    GOOGLE_VISION_MODE = 'production_api_key'
elif os.path.exists(GOOGLE_VISION_CREDENTIALS):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_VISION_CREDENTIALS
    # Mode: production avec Service Account Google Vision
    GOOGLE_VISION_MODE = 'production'
else:
    # Mode: mock (utilise un service simulé pour développement)
    GOOGLE_VISION_MODE = 'mock'
    import logging
    logging.warning("Aucune configuration OCR trouvée. Mode MOCK activé.")

# CORS Configuration
# For development, allow typical frontend ports.
# In production, this should be restricted to the actual frontend domain.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Default Vite port
    "http://127.0.0.1:5173",
    "http://localhost:5174",  # Alternative Vite port
    "http://127.0.0.1:5174",
]

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,  # Nombre d'éléments par page par défaut
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    # Configuration des exceptions pour des messages d'erreur clairs
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

