from django.core.management.base import BaseCommand
from api.models import Pharmacie

class Command(BaseCommand):
    help = 'Lists all pharmacies in the database with their IDs'

    def handle(self, *args, **options):
        pharmacies = Pharmacie.objects.all()
        if not pharmacies.exists():
            self.stdout.write(self.style.WARNING('No pharmacies found in the database.'))
            return

        self.stdout.write(self.style.SUCCESS('Available Pharmacies:'))
        for p in pharmacies:
            self.stdout.write(f'  ID: {p.id}, Name: {p.nom}, Lat: {p.latitude}, Lon: {p.longitude}')
