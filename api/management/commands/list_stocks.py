from django.core.management.base import BaseCommand
from api.models import PharmacyMedication

class Command(BaseCommand):
    help = 'Lists all medications in stock for all pharmacies'

    def handle(self, *args, **options):
        stocks = PharmacyMedication.objects.all()

        if stocks.exists():
            self.stdout.write(self.style.SUCCESS('--- Pharmacy Stock Report ---'))
            for stock_item in stocks:
                self.stdout.write(
                    f'Pharmacy: {stock_item.pharmacy.nom} | '
                    f'Medication: {stock_item.medication.nom} | '
                    f'Stock: {stock_item.stock_disponible}'
                )
            self.stdout.write(self.style.SUCCESS('--- End of Report ---'))
        else:
            self.stdout.write(self.style.WARNING('No stock information found in the database.'))
