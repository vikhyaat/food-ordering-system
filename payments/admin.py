from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'transaction_id', 'order', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('payment_id', 'transaction_id', 'order__order_number')
