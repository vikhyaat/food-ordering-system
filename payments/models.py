import random
import string
from django.db import models
from orders.models import Order


def generate_transaction_id():
    return "TXN" + ''.join(random.choices(string.digits, k=10))


def generate_payment_id():
    return "PAY" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class Payment(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    transaction_id = models.CharField(max_length=30, unique=True, default=generate_transaction_id)
    payment_id = models.CharField(max_length=20, unique=True, default=generate_payment_id)
    cardholder_name = models.CharField(max_length=150)
    card_last4 = models.CharField(max_length=4)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    method = models.CharField(max_length=20, default='Card')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_id} - {self.order.order_number} ({self.status})"
