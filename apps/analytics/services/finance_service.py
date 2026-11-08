from datetime import date
from decimal import Decimal
from django.db.models import Sum
from apps.finance.models import Transaction, TransactionType


def get_finance_metrics(user, start_date: date, end_date: date) -> dict:
    """
    Computes financial analytics (income, expenses, savings, category breakdown)
    for the user across the specified date period.
    """
    transactions = Transaction.objects.filter(
        user=user,
        transaction_date__range=(start_date, end_date)
    ).select_related('category')

    income_total = transactions.filter(
        transaction_type=TransactionType.INCOME
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    expense_total = transactions.filter(
        transaction_type=TransactionType.EXPENSE
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    net_balance = income_total - expense_total
    savings_rate = round(float((net_balance / income_total) * 100), 1) if income_total > Decimal('0.00') else 0.0

    # Category-wise expense breakdown
    cat_expenses = {}
    for tx in transactions.filter(transaction_type=TransactionType.EXPENSE):
        cat_name = tx.category.name if tx.category else 'Uncategorized'
        cat_expenses[cat_name] = cat_expenses.get(cat_name, Decimal('0.00')) + tx.amount

    expense_breakdown = []
    cat_names_chart = []
    cat_amounts_chart = []
    cat_types_chart = []

    for cat_name, amt in sorted(cat_expenses.items(), key=lambda x: x[1], reverse=True):
        pct = round(float((amt / expense_total) * 100), 1) if expense_total > Decimal('0.00') else 0.0
        expense_breakdown.append({
            'category': cat_name,
            'amount': amt,
            'percentage': pct,
        })
        cat_names_chart.append(cat_name)
        cat_amounts_chart.append(float(amt))
        cat_types_chart.append('EXPENSE')

    # Top expense driver
    top_expense = expense_breakdown[0] if expense_breakdown else None

    return {
        'total_income': income_total,
        'total_expenses': expense_total,
        'net_balance': net_balance,
        'savings_rate': savings_rate,
        'expense_breakdown': expense_breakdown,
        'top_expense': top_expense,
        'cat_names_chart': cat_names_chart,
        'cat_amounts_chart': cat_amounts_chart,
        'cat_types_chart': cat_types_chart,
    }
