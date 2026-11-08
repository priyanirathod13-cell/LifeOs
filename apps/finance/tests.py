from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

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


class FinanceViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(
            username='user_fin_va',
            email='fin_va@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_fin_vb',
            email='fin_vb@example.com',
            password='Password123!'
        )
        self.client.login(username='user_fin_va', password='Password123!')

        self.category_a = Category.objects.create(
            user=self.user_a,
            name='Food & Dining',
            category_type=CategoryType.FINANCE,
            color='#10B981'
        )

    def test_views_require_login(self):
        """Unauthenticated requests redirect to login."""
        self.client.logout()
        protected_urls = [
            reverse('personal:finance'),
            reverse('finance:dashboard'),
            reverse('finance:transaction_create'),
            reverse('finance:category_create'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    def test_finance_dashboard_calculations(self):
        """Dashboard accurately computes total income, total expense, and net balance."""
        today = date.today()

        # Income: ₹50,000
        Transaction.objects.create(
            user=self.user_a,
            transaction_type=TransactionType.INCOME,
            amount=Decimal('50000.00'),
            description='Salary Deposit',
            transaction_date=today
        )
        # Expense: ₹12,000
        Transaction.objects.create(
            user=self.user_a,
            category=self.category_a,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('12000.00'),
            description='Rent & Groceries',
            transaction_date=today
        )

        response = self.client.get(reverse('personal:finance'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_income'], Decimal('50000.00'))
        self.assertEqual(response.context['total_expense'], Decimal('12000.00'))
        self.assertEqual(response.context['net_balance'], Decimal('38000.00'))
        self.assertEqual(response.context['monthly_savings'], Decimal('38000.00'))

    def test_transaction_crud_flow(self):
        """Transaction creation, edit, and deletion."""
        # Create
        create_url = reverse('finance:transaction_create')
        res = self.client.post(create_url, {
            'description': 'Laptop Stand',
            'amount': '1499.00',
            'transaction_type': TransactionType.EXPENSE,
            'category': self.category_a.pk,
            'transaction_date': date.today().isoformat(),
            'payment_method': 'UPI',
            'notes': 'Amazon order',
        })
        self.assertEqual(res.status_code, 302)
        tx = Transaction.objects.get(user=self.user_a, description='Laptop Stand')
        self.assertEqual(tx.amount, Decimal('1499.00'))

        # Edit
        edit_url = reverse('finance:transaction_edit', kwargs={'pk': tx.pk})
        res = self.client.post(edit_url, {
            'description': 'Ergonomic Laptop Stand',
            'amount': '1599.00',
            'transaction_type': TransactionType.EXPENSE,
            'category': self.category_a.pk,
            'transaction_date': date.today().isoformat(),
            'payment_method': 'UPI',
            'notes': 'Price adjustment',
        })
        self.assertEqual(res.status_code, 302)
        tx.refresh_from_db()
        self.assertEqual(tx.description, 'Ergonomic Laptop Stand')
        self.assertEqual(tx.amount, Decimal('1599.00'))

        # Delete
        delete_url = reverse('finance:transaction_delete', kwargs={'pk': tx.pk})
        res = self.client.post(delete_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=tx.pk).exists())

    def test_finance_category_creation(self):
        """Users can create custom finance categories."""
        create_url = reverse('finance:category_create')
        res = self.client.post(create_url, {
            'name': 'Investments',
            'description': 'Mutual funds and stocks',
            'color': '#8B5CF6',
            'icon': 'trending-up',
        })
        self.assertEqual(res.status_code, 302)
        cat = Category.objects.get(user=self.user_a, name='Investments')
        self.assertEqual(cat.category_type, CategoryType.FINANCE)

    def test_ledger_search_and_filters(self):
        """Ledger supports search, type filter, category filter, and sorting."""
        today = date.today()
        Transaction.objects.create(
            user=self.user_a,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('200.00'),
            description='Coffee with friend',
            transaction_date=today
        )
        Transaction.objects.create(
            user=self.user_a,
            transaction_type=TransactionType.INCOME,
            amount=Decimal('5000.00'),
            description='Consulting gig',
            transaction_date=today
        )

        url = reverse('personal:finance')

        # Filter by INCOME
        res = self.client.get(url, {'type': 'INCOME'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Consulting gig')
        self.assertNotContains(res, 'Coffee with friend')

        # Search by keyword
        res = self.client.get(url, {'q': 'Coffee'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Coffee with friend')
        self.assertNotContains(res, 'Consulting gig')

    def test_cross_user_transaction_isolation(self):
        """User B cannot view or edit User A's transactions."""
        tx_a = Transaction.objects.create(
            user=self.user_a,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('999.00'),
            description="User A's Secret Purchase",
            transaction_date=date.today()
        )

        # Log in as User B
        self.client.login(username='user_fin_vb', password='Password123!')

        self.assertEqual(self.client.get(reverse('finance:transaction_edit', kwargs={'pk': tx_a.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('finance:transaction_delete', kwargs={'pk': tx_a.pk})).status_code, 404)
