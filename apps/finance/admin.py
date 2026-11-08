from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'user', 'transaction_type', 'amount', 'category', 'payment_method', 'description')
    list_filter = ('transaction_type', 'transaction_date', 'payment_method', 'user')
    search_fields = ('description', 'notes', 'user__username')
