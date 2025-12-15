from django.core.management.base import BaseCommand
from api.models import Pharmacie

class Command(BaseCommand):
    help = 'Creates a new pharmacy in the database'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='The name of the pharmacy')
        parser.add_argument('address', type=str, help='The address of the pharmacy')

    def handle(self, *args, **options):
        name = options['name']
        address = options['address']

        pharmacy = Pharmacie.objects.create(
            nom=name,
            adresse=address,
            # You can add default values for other fields if you want
            note="0.0"
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully created pharmacy "{pharmacy.nom}" with ID: {pharmacy.id}'))
