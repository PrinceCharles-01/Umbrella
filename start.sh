#!/bin/bash

# Script de démarrage pour Railway
# Ce script gère correctement la variable PORT fournie par Railway

# Afficher les informations de démarrage
echo "=========================================="
echo "Démarrage de l'application Umbrella Backend"
echo "=========================================="

# Vérifier que la variable PORT est définie
if [ -z "$PORT" ]; then
    echo "WARNING: PORT variable is not set, using default port 8000"
    PORT=8000
else
    echo "PORT variable is set to: $PORT"
fi

# Vérifier que PORT est un nombre valide
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "ERROR: PORT ($PORT) is not a valid port number"
    echo "Using default port 8000"
    PORT=8000
fi

# Utiliser les settings de production
export DJANGO_SETTINGS_MODULE=umbrella_api.settings_prod

# Collecter les fichiers statiques
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Appliquer les migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Créer le superuser automatiquement si les variables sont définies
if [ ! -z "$DJANGO_SUPERUSER_USERNAME" ] && [ ! -z "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py create_superuser \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "${DJANGO_SUPERUSER_EMAIL:-admin@umbrella.com}" \
        --password "$DJANGO_SUPERUSER_PASSWORD" || echo "Superuser already exists or creation failed"
fi

# Seed database if AUTO_SEED is set to true (SAFE MODE - won't delete existing data)
if [ "$AUTO_SEED" = "true" ]; then
    echo "Seeding database with initial data (safe mode)..."
    python manage.py seed_data_safe || echo "Seeding failed or database already has data"
fi

# Démarrer le serveur avec gunicorn
echo "Starting Gunicorn server on 0.0.0.0:$PORT"
exec gunicorn umbrella_api.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
