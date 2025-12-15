from django.core.management.base import BaseCommand, CommandError
from api.models import Pharmacie

class Command(BaseCommand):
    help = 'Adds latitude and longitude to a given pharmacy'

    def add_arguments(self, parser):
        parser.add_argument('pharmacy_id', type=int, help='The ID of the pharmacy to update')
        parser.add_argument('latitude', type=float, help='The latitude of the pharmacy')
        parser.add_argument('longitude', type=float, help='The longitude of the pharmacy')

    def handle(self, *args, **options):
        pharmacy_id = options['pharmacy_id']
        latitude = options['latitude']
        longitude = options['longitude']

        try:
            pharmacy = Pharmacie.objects.get(pk=pharmacy_id)
        except Pharmacie.DoesNotExist:
            raise CommandError(f'Pharmacy with ID "{pharmacy_id}" does not exist.')

        pharmacy.latitude = latitude
        pharmacy.longitude = longitude
        pharmacy.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully updated coordinates for "{pharmacy.nom}"'))
