from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TransactionType(models.TextChoices):
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'
    TRANSFER = 'TRANSFER', 'Transfer'


class Transaction(models.Model):
    """
    Monetary transaction recording personal income, expense, or allocation.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    category = models.ForeignKey(
        'productivity.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.EXPENSE
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Positive monetary amount in base currency'
    )
    description = models.CharField(max_length=255)
    transaction_date = models.DateField()
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        default='CASH',
        help_text='Payment channel (e.g. UPI, Card, Cash, Bank Transfer)'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['user', 'transaction_type']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(amount__gt=Decimal('0.00')),
                name='transaction_amount_strictly_positive'
            )
        ]

    def clean(self):
        super().clean()
        if self.category and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})
        if self.amount is not None and self.amount <= Decimal('0.00'):
            raise ValidationError({'amount': 'Transaction amount must be strictly greater than zero.'})

    def __str__(self):
        prefix = '+' if self.transaction_type == TransactionType.INCOME else '-'
        return f"{prefix}₹{self.amount} ({self.transaction_date}) - {self.description}"
