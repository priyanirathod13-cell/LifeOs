from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.finance.models import Transaction, TransactionType
from apps.productivity.models import Category, CategoryType

User = get_user_model()


class FinanceModelsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='user_fin_a',
            email='fin_a@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_fin_b',
            email='fin_b@example.com',
            password='Password123!'
        )

        self.category_a = Category.objects.create(
            user=self.user_a,
            name='Groceries',
            category_type=CategoryType.FINANCE
        )
        self.category_b = Category.objects.create(
            user=self.user_b,
            name='Groceries',
            category_type=CategoryType.FINANCE
        )

    def test_transaction_creation_and_str(self):
        """Transactions record income or expense with high-precision decimal."""
        tx_expense = Transaction.objects.create(
            user=self.user_a,
            category=self.category_a,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('450.50'),
            description='Weekly vegetables',
            transaction_date=date.today(),
            payment_method='UPI'
        )
        self.assertIn('-₹450.50', str(tx_expense))

        tx_income = Transaction.objects.create(
            user=self.user_a,
            transaction_type=TransactionType.INCOME,
            amount=Decimal('15000.00'),
            description='Freelance project milestone',
            transaction_date=date.today()
        )
        self.assertIn('+₹15000.00', str(tx_income))

    def test_strictly_positive_amount_validation(self):
        """Zero or negative transaction amounts are strictly prohibited."""
        invalid_tx_zero = Transaction(
            user=self.user_a,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('0.00'),
            description='Free sample',
            transaction_date=date.today()
        )
        with self.assertRaises(ValidationError):
            invalid_tx_zero.full_clean()

        invalid_tx_neg = Transaction(
            user=self.user_a,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('-100.00'),
            description='Negative charge',
            transaction_date=date.today()
        )
        with self.assertRaises(ValidationError):
            invalid_tx_neg.full_clean()

    def test_cross_user_category_isolation(self):
        """Transactions cannot link to another user's category."""
        cross_tx = Transaction(
            user=self.user_a,
            category=self.category_b,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('250.00'),
            description='Coffee with friend',
            transaction_date=date.today()
        )
        with self.assertRaises(ValidationError):
            cross_tx.full_clean()
