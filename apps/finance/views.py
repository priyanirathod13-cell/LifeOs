from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.productivity.models import Category, CategoryType
from .forms import FinanceCategoryForm, TransactionForm
from .models import Transaction, TransactionType


@login_required
def finance_dashboard_view(request):
    """
    Finance Manager Dashboard & Transaction Ledger.
    Computes all-time and monthly net balances, category spending shares,
    income vs expense metrics, with search, filtering, and sorting.
    """
    today = timezone.localdate()
    start_of_month = today.replace(day=1)

    # Base query for user
    base_qs = Transaction.objects.filter(user=request.user)

    # 1. Lifetime Summary Calculations
    total_income = base_qs.filter(
        transaction_type=TransactionType.INCOME
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    total_expense = base_qs.filter(
        transaction_type=TransactionType.EXPENSE
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    net_balance = total_income - total_expense

    # 2. Current Month Calculations
    month_income = base_qs.filter(
        transaction_type=TransactionType.INCOME,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    month_expense = base_qs.filter(
        transaction_type=TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    monthly_savings = month_income - month_expense

    # 3. Category-wise Spending Breakdown (Current Month)
    category_qs = base_qs.filter(
        transaction_type=TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today
    ).values('category__id', 'category__name', 'category__color').annotate(
        total=Sum('amount')
    ).order_by('-total')

    category_breakdown = []
    if month_expense > Decimal('0.00'):
        for cat in category_qs:
            amt = cat['total'] or Decimal('0.00')
            pct = round((amt / month_expense) * 100, 1)
            category_breakdown.append({
                'name': cat['category__name'] or 'Uncategorized',
                'color': cat['category__color'] or '#818CF8',
                'amount': amt,
                'percentage': pct,
            })

    # 4. Filterable & Sortable Ledger
    qs = base_qs.select_related('category')

    # Filter by transaction type
    type_filter = request.GET.get('type', '').strip()
    if type_filter and type_filter != 'ALL':
        qs = qs.filter(transaction_type=type_filter)

    # Filter by category
    cat_id = request.GET.get('category', '').strip()
    if cat_id:
        qs = qs.filter(category_id=cat_id)

    # Date filters
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        qs = qs.filter(transaction_date__gte=date_from)
    if date_to:
        qs = qs.filter(transaction_date__lte=date_to)

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(notes__icontains=q))

    # Sort
    sort = request.GET.get('sort', '-date')
    if sort == 'date':
        qs = qs.order_by('transaction_date', 'created_at')
    elif sort == 'amount_asc':
        qs = qs.order_by('amount')
    elif sort == 'amount_desc':
        qs = qs.order_by('-amount')
    else:
        qs = qs.order_by('-transaction_date', '-created_at')

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # User categories for filter dropdown
    user_categories = Category.objects.filter(user=request.user).order_by('name')

    context = {
        'page_title': 'Finance Manager',
        'active_nav': 'personal',
        'personal_tab': 'finance',
        'page_obj': page_obj,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'month_income': month_income,
        'month_expense': month_expense,
        'monthly_savings': monthly_savings,
        'category_breakdown': category_breakdown,
        'user_categories': user_categories,
        'type_filter': type_filter,
        'cat_id': cat_id,
        'date_from': date_from,
        'date_to': date_to,
        'q': q,
        'sort': sort,
        'total_transactions': base_qs.count(),
    }
    return render(request, 'personal/finance/dashboard.html', context)


@login_required
def transaction_create_view(request):
    """
    Record a new monetary transaction (income, expense, or transfer).
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.user = request.user
            tx.save()
            prefix = '+' if tx.transaction_type == TransactionType.INCOME else '-'
            messages.success(request, f'Transaction "{tx.description}" ({prefix}₹{tx.amount}) recorded.')
            return redirect('personal:finance')
    else:
        form = TransactionForm(user=request.user)

    context = {
        'page_title': 'Add Transaction',
        'active_nav': 'personal',
        'personal_tab': 'finance',
        'form': form,
    }
    return render(request, 'personal/finance/transaction_form.html', context)


@login_required
def transaction_edit_view(request, pk):
    """
    Edit an existing transaction.
    """
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=tx, user=request.user)
        if form.is_valid():
            tx = form.save()
            messages.success(request, f'Transaction "{tx.description}" updated.')
            return redirect('personal:finance')
    else:
        form = TransactionForm(instance=tx, user=request.user)

    context = {
        'page_title': f'Edit Transaction: {tx.description}',
        'active_nav': 'personal',
        'personal_tab': 'finance',
        'form': form,
        'tx': tx,
    }
    return render(request, 'personal/finance/transaction_form.html', context)


@login_required
def transaction_delete_view(request, pk):
    """
    Delete a transaction with confirmation.
    """
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        desc = tx.description
        tx.delete()
        messages.success(request, f'Transaction "{desc}" deleted.')
        return redirect('personal:finance')

    context = {
        'page_title': 'Confirm Delete Transaction',
        'active_nav': 'personal',
        'personal_tab': 'finance',
        'tx': tx,
    }
    return render(request, 'personal/finance/confirm_delete.html', context)


@login_required
def finance_category_create_view(request):
    """
    Quick category creation for finance.
    """
    if request.method == 'POST':
        form = FinanceCategoryForm(request.POST, user=request.user)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f'Finance Category "{cat.name}" created.')
            return redirect('personal:finance')
    else:
        form = FinanceCategoryForm(user=request.user)

    context = {
        'page_title': 'Add Finance Category',
        'active_nav': 'personal',
        'personal_tab': 'finance',
        'form': form,
    }
    return render(request, 'personal/finance/category_form.html', context)
