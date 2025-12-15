"""
Commande pour créer un superuser de manière non-interactive
Usage: python manage.py create_superuser --username admin --email admin@umbrella.com --password votre_mot_de_passe
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    help = 'Crée un superuser de manière non-interactive'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Nom d\'utilisateur', default='admin')
        parser.add_argument('--email', type=str, help='Email', default='admin@umbrella.com')
        parser.add_argument('--password', type=str, help='Mot de passe')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Le superuser "{username}" existe déjà'))
            return

        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Superuser "{username}" créé avec succès!'))
            self.stdout.write(f'   Email: {email}')
            self.stdout.write(f'   Vous pouvez maintenant vous connecter à /admin/')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erreur lors de la création du superuser: {e}'))
