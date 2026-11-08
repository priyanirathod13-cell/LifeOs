from decimal import Decimal
from django import forms
from django.utils import timezone
from apps.productivity.models import Category, CategoryType
from .models import Transaction, TransactionType


PAYMENT_METHOD_CHOICES = [
    ('UPI', 'UPI / QR'),
    ('DEBIT_CARD', 'Debit Card'),
    ('CREDIT_CARD', 'Credit Card'),
    ('NET_BANKING', 'Net Banking / Transfer'),
    ('CASH', 'Cash'),
    ('WALLET', 'Digital Wallet'),
    ('OTHER', 'Other'),
]


class TransactionForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        initial='UPI'
    )

    class Meta:
        model = Transaction
        fields = [
            'description', 'amount', 'transaction_type', 'category',
            'transaction_date', 'payment_method', 'notes'
        ]
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Grocery shopping, Monthly salary, Books',
                'autofocus': True,
                'required': True,
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
                'required': True,
            }),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Vendor details, invoice reference, or split information...',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if self.user:
            if not self.instance.user_id:
                self.instance.user = self.user
            # Show all user categories, prioritizing FINANCE categories
            self.fields['category'].queryset = Category.objects.filter(
                user=self.user
            ).order_by('-category_type', 'name')
        if not self.instance.pk and 'transaction_date' not in self.initial:
            self.initial['transaction_date'] = timezone.localdate()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0.00'):
            raise forms.ValidationError('Transaction amount must be strictly greater than zero.')
        return amount

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if cat and self.user and cat.user_id != self.user.id:
            raise forms.ValidationError('Cannot assign a category belonging to another user.')
        return cat


class FinanceCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Groceries, Rent, Freelancing, Utilities',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What transactions belong here...',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'value': '#818CF8',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. shopping-cart, coffee, dollar-sign',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if self.user:
            qs = Category.objects.filter(user=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f'Category "{name}" already exists.')
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.user
        instance.category_type = CategoryType.FINANCE
        if commit:
            instance.save()
        return instance
