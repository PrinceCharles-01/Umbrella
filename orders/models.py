from django.db import models
from api.models import Pharmacie, Medication # Assuming these models are in the 'api' app

class Order(models.Model):
    pharmacy = models.ForeignKey(Pharmacie, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Add other fields as necessary, e.g., user, status, total_price

    def __str__(self):
        return f"Order {self.id} at {self.pharmacy.nom}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.medication.nom} for Order {self.order.id}"