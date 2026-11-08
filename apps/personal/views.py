from datetime import date, timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.finance.models import Transaction, TransactionType
from apps.productivity.models import Category
from .forms import (
    DailyCheckinForm,
    DecisionForm,
    DecisionOptionForm,
    DecisionOutcomeForm,
    JournalEntryForm,
    MistakeForm,
    SleepRecordForm,
)
from .models import (
    DailyMetric,
    Decision,
    DecisionOption,
    DecisionOutcome,
    DecisionStatus,
    JournalEntry,
    Mistake,
    MistakeImpact,
    MistakeStatus,
    SleepRecord,
)


# ==============================================================================
# 1. PERSONAL DASHBOARD
# ==============================================================================

@login_required
def personal_dashboard_view(request):
    """
    Central Executive Dashboard for Personal Management.
    Aggregates journal entries, daily biometric check-ins, sleep history,
    decisions, mistakes, and monthly financial summaries.
    """
    today = timezone.localdate()
    start_of_month = today.replace(day=1)
    
    # 1. Monthly Summary KPIs
    journal_month_count = JournalEntry.objects.filter(
        user=request.user,
        entry_date__gte=start_of_month,
        entry_date__lte=today
    ).count()

    monthly_metrics = DailyMetric.objects.filter(
        user=request.user,
        metric_date__gte=start_of_month,
        metric_date__lte=today
    )
    avg_mood = monthly_metrics.filter(mood_score__isnull=False).aggregate(avg=Avg('mood_score'))['avg']
    avg_energy = monthly_metrics.filter(energy_score__isnull=False).aggregate(avg=Avg('energy_score'))['avg']
    avg_sleep = monthly_metrics.filter(sleep_hours__isnull=False).aggregate(avg=Avg('sleep_hours'))['avg']

    decisions_total = Decision.objects.filter(user=request.user).count()
    decisions_pending = Decision.objects.filter(
        user=request.user,
        status__in=[DecisionStatus.DRAFT, DecisionStatus.EVALUATING]
    ).count()

    # Financial KPIs for current month
    month_income = Transaction.objects.filter(
        user=request.user,
        transaction_type=TransactionType.INCOME,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    month_expense = Transaction.objects.filter(
        user=request.user,
        transaction_type=TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    month_balance = month_income - month_expense

    # 2. Recent Streams
    recent_journals = JournalEntry.objects.filter(
        user=request.user
    ).order_by('-entry_date', '-created_at')[:3]

    recent_decisions = Decision.objects.filter(
        user=request.user
    ).select_related('category', 'chosen_option').order_by('-decision_date', '-created_at')[:3]

    recent_mistakes = Mistake.objects.filter(
        user=request.user
    ).select_related('category').order_by('-mistake_date', '-created_at')[:3]

    latest_checkin = DailyMetric.objects.filter(
        user=request.user
    ).order_by('-metric_date').first()

    # 3. 14-day Mood & Sleep Trend Data
    past_14_days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    metrics_map = {
        m.metric_date: m
        for m in DailyMetric.objects.filter(
            user=request.user,
            metric_date__in=past_14_days
        )
    }

    trend_data = []
    for d in past_14_days:
        m = metrics_map.get(d)
        trend_data.append({
            'date': d,
            'day_name': d.strftime('%a'),
            'mood': m.mood_score if m and m.mood_score else None,
            'energy': m.energy_score if m and m.energy_score else None,
            'stress': m.stress_score if m and m.stress_score else None,
            'sleep': float(m.sleep_hours) if m and m.sleep_hours else None,
        })

    # 4. Spending Category Breakdown (Current Month)
    category_spending = Transaction.objects.filter(
        user=request.user,
        transaction_type=TransactionType.EXPENSE,
        transaction_date__gte=start_of_month,
        transaction_date__lte=today
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    context = {
        'page_title': 'Personal Dashboard',
        'active_nav': 'personal',
        'personal_tab': 'dashboard',
        'today': today,
        'journal_month_count': journal_month_count,
        'avg_mood': round(avg_mood, 1) if avg_mood else None,
        'avg_energy': round(avg_energy, 1) if avg_energy else None,
        'avg_sleep': round(avg_sleep, 1) if avg_sleep else None,
        'decisions_total': decisions_total,
        'decisions_pending': decisions_pending,
        'month_income': month_income,
        'month_expense': month_expense,
        'month_balance': month_balance,
        'recent_journals': recent_journals,
        'recent_decisions': recent_decisions,
        'recent_mistakes': recent_mistakes,
        'latest_checkin': latest_checkin,
        'trend_data': trend_data,
        'category_spending': category_spending,
    }
    return render(request, 'personal/dashboard.html', context)


# ==============================================================================
# 2. JOURNAL MANAGEMENT
# ==============================================================================

@login_required
def journal_list_view(request):
    """
    Searchable, filterable, and paginated personal journal entries list.
    """
    qs = JournalEntry.objects.filter(user=request.user)

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q) | Q(mood_tag__icontains=q))

    # Date filters
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        qs = qs.filter(entry_date__gte=date_from)
    if date_to:
        qs = qs.filter(entry_date__lte=date_to)

    # Sort
    sort = request.GET.get('sort', 'newest')
    if sort == 'oldest':
        qs = qs.order_by('entry_date', 'created_at')
    else:
        qs = qs.order_by('-entry_date', '-created_at')

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'Journal',
        'active_nav': 'personal',
        'personal_tab': 'journal',
        'page_obj': page_obj,
        'q': q,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
        'total_count': qs.count(),
    }
    return render(request, 'personal/journal/list.html', context)


@login_required
def journal_create_view(request):
    """
    Create a new private journal entry.
    """
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, f'Journal entry "{entry.title}" saved successfully.')
            return redirect('personal:journal_detail', pk=entry.pk)
    else:
        form = JournalEntryForm()

    context = {
        'page_title': 'New Journal Entry',
        'active_nav': 'personal',
        'personal_tab': 'journal',
        'form': form,
    }
    return render(request, 'personal/journal/form.html', context)


@login_required
def journal_detail_view(request, pk):
    """
    Full view of a private journal entry with strict user ownership.
    """
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    context = {
        'page_title': entry.title,
        'active_nav': 'personal',
        'personal_tab': 'journal',
        'entry': entry,
    }
    return render(request, 'personal/journal/detail.html', context)


@login_required
def journal_edit_view(request, pk):
    """
    Edit an existing journal entry.
    """
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            messages.success(request, f'Journal entry "{entry.title}" updated successfully.')
            return redirect('personal:journal_detail', pk=entry.pk)
    else:
        form = JournalEntryForm(instance=entry)

    context = {
        'page_title': f'Edit: {entry.title}',
        'active_nav': 'personal',
        'personal_tab': 'journal',
        'form': form,
        'entry': entry,
    }
    return render(request, 'personal/journal/form.html', context)


@login_required
def journal_delete_view(request, pk):
    """
    Delete a journal entry with confirmation dialog.
    """
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        title = entry.title
        entry.delete()
        messages.success(request, f'Journal entry "{title}" deleted.')
        return redirect('personal:journal_list')

    context = {
        'page_title': 'Confirm Delete Journal Entry',
        'active_nav': 'personal',
        'personal_tab': 'journal',
        'entry': entry,
    }
    return render(request, 'personal/journal/confirm_delete.html', context)


# ==============================================================================
# 3. DAILY CHECK-IN
# ==============================================================================

@login_required
def daily_checkin_view(request):
    """
    Daily biometric and subjective state check-in logging.
    Enforces exactly one record per date per user by updating existing entries.
    """
    target_date_str = request.GET.get('date', '').strip()
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            target_date = timezone.localdate()
    else:
        target_date = timezone.localdate()

    metric = DailyMetric.objects.filter(user=request.user, metric_date=target_date).first()

    if request.method == 'POST':
        form = DailyCheckinForm(request.POST, instance=metric)
        if form.is_valid():
            metric_obj = form.save(commit=False)
            metric_obj.user = request.user
            metric_obj.metric_date = target_date
            metric_obj.save()
            messages.success(request, f'Check-in for {target_date.strftime("%B %d, %Y")} recorded successfully.')
            return redirect(f"{request.path}?date={target_date.isoformat()}")
    else:
        form = DailyCheckinForm(instance=metric, initial={'metric_date': target_date})

    # Recent 14 check-in history strip
    recent_checkins = DailyMetric.objects.filter(
        user=request.user
    ).order_by('-metric_date')[:14]

    context = {
        'page_title': 'Daily Check-in',
        'active_nav': 'personal',
        'personal_tab': 'checkin',
        'form': form,
        'metric': metric,
        'target_date': target_date,
        'today': timezone.localdate(),
        'recent_checkins': recent_checkins,
    }
    return render(request, 'personal/checkin.html', context)


# ==============================================================================
# 4. MOOD AND ENERGY TRACKING
# ==============================================================================

@login_required
def mood_energy_view(request):
    """
    Visual analytics for mood, energy, and stress over time.
    """
    today = timezone.localdate()
    range_param = request.GET.get('range', '14')

    if range_param == '7':
        days_count = 7
    elif range_param == '30':
        days_count = 30
    elif range_param == 'all':
        days_count = 90
    else:
        days_count = 14

    cutoff_date = today - timedelta(days=days_count - 1)
    metrics_qs = DailyMetric.objects.filter(
        user=request.user,
        metric_date__gte=cutoff_date,
        metric_date__lte=today
    ).order_by('metric_date')

    # Aggregations
    avg_mood = metrics_qs.filter(mood_score__isnull=False).aggregate(avg=Avg('mood_score'))['avg']
    avg_energy = metrics_qs.filter(energy_score__isnull=False).aggregate(avg=Avg('energy_score'))['avg']
    avg_stress = metrics_qs.filter(stress_score__isnull=False).aggregate(avg=Avg('stress_score'))['avg']

    # 7-day vs 30-day benchmarks
    seven_days_ago = today - timedelta(days=6)
    thirty_days_ago = today - timedelta(days=29)

    avg_mood_7d = DailyMetric.objects.filter(
        user=request.user, metric_date__gte=seven_days_ago, mood_score__isnull=False
    ).aggregate(avg=Avg('mood_score'))['avg']

    avg_mood_30d = DailyMetric.objects.filter(
        user=request.user, metric_date__gte=thirty_days_ago, mood_score__isnull=False
    ).aggregate(avg=Avg('mood_score'))['avg']

    avg_energy_7d = DailyMetric.objects.filter(
        user=request.user, metric_date__gte=seven_days_ago, energy_score__isnull=False
    ).aggregate(avg=Avg('energy_score'))['avg']

    avg_energy_30d = DailyMetric.objects.filter(
        user=request.user, metric_date__gte=thirty_days_ago, energy_score__isnull=False
    ).aggregate(avg=Avg('energy_score'))['avg']

    # Build dense timeline array
    date_list = [cutoff_date + timedelta(days=i) for i in range(days_count)]
    metric_map = {m.metric_date: m for m in metrics_qs}

    chart_points = []
    for d in date_list:
        m = metric_map.get(d)
        chart_points.append({
            'date': d,
            'day_label': d.strftime('%d %b'),
            'day_name': d.strftime('%a'),
            'mood': m.mood_score if m and m.mood_score else None,
            'energy': m.energy_score if m and m.energy_score else None,
            'stress': m.stress_score if m and m.stress_score else None,
            'notes': m.notes if m else '',
        })

    context = {
        'page_title': 'Mood & Energy Tracking',
        'active_nav': 'personal',
        'personal_tab': 'mood_energy',
        'range_param': range_param,
        'days_count': days_count,
        'avg_mood': round(avg_mood, 1) if avg_mood else None,
        'avg_energy': round(avg_energy, 1) if avg_energy else None,
        'avg_stress': round(avg_stress, 1) if avg_stress else None,
        'avg_mood_7d': round(avg_mood_7d, 1) if avg_mood_7d else None,
        'avg_mood_30d': round(avg_mood_30d, 1) if avg_mood_30d else None,
        'avg_energy_7d': round(avg_energy_7d, 1) if avg_energy_7d else None,
        'avg_energy_30d': round(avg_energy_30d, 1) if avg_energy_30d else None,
        'chart_points': chart_points,
        'total_logged': metrics_qs.count(),
    }
    return render(request, 'personal/mood_energy.html', context)


# ==============================================================================
# 5. SLEEP TRACKING
# ==============================================================================

@login_required
def sleep_list_view(request):
    """
    Sleep tracking history, weekly/monthly averages, and duration trends.
    """
    today = timezone.localdate()
    qs = SleepRecord.objects.filter(user=request.user).order_by('-sleep_date', '-wake_time')

    # Averages
    seven_days_ago = today - timedelta(days=7)
    thirty_days_ago = today - timedelta(days=30)

    avg_sleep_7d = SleepRecord.objects.filter(
        user=request.user, sleep_date__gte=seven_days_ago
    ).aggregate(avg=Avg('duration_hours'))['avg']

    avg_sleep_30d = SleepRecord.objects.filter(
        user=request.user, sleep_date__gte=thirty_days_ago
    ).aggregate(avg=Avg('duration_hours'))['avg']

    avg_quality = SleepRecord.objects.filter(
        user=request.user, quality_rating__isnull=False
    ).aggregate(avg=Avg('quality_rating'))['avg']

    total_records = qs.count()

    # 14-day sleep chart
    past_14_days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    records_14d = {
        r.sleep_date: r for r in SleepRecord.objects.filter(
            user=request.user, sleep_date__in=past_14_days
        )
    }

    sleep_chart = []
    for d in past_14_days:
        rec = records_14d.get(d)
        sleep_chart.append({
            'date': d,
            'day_name': d.strftime('%a'),
            'duration': float(rec.duration_hours) if rec else None,
            'quality': rec.quality_rating if rec else None,
        })

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'Sleep Tracking',
        'active_nav': 'personal',
        'personal_tab': 'sleep',
        'page_obj': page_obj,
        'avg_sleep_7d': round(avg_sleep_7d, 2) if avg_sleep_7d else None,
        'avg_sleep_30d': round(avg_sleep_30d, 2) if avg_sleep_30d else None,
        'avg_quality': round(avg_quality, 1) if avg_quality else None,
        'total_records': total_records,
        'sleep_chart': sleep_chart,
    }
    return render(request, 'personal/sleep/list.html', context)


@login_required
def sleep_create_view(request):
    """
    Record a new sleep session with automatic duration calculation and DailyMetric sync.
    """
    if request.method == 'POST':
        form = SleepRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.user = request.user
            record.save()
            messages.success(request, f'Sleep record for {record.sleep_date} ({record.duration_hours}h) saved.')
            return redirect('personal:sleep_list')
    else:
        form = SleepRecordForm()

    context = {
        'page_title': 'Record Sleep',
        'active_nav': 'personal',
        'personal_tab': 'sleep',
        'form': form,
    }
    return render(request, 'personal/sleep/form.html', context)


@login_required
def sleep_edit_view(request, pk):
    """
    Edit an existing sleep record.
    """
    record = get_object_or_404(SleepRecord, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SleepRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()
            messages.success(request, f'Sleep record for {record.sleep_date} updated.')
            return redirect('personal:sleep_list')
    else:
        form = SleepRecordForm(instance=record)

    context = {
        'page_title': f'Edit Sleep Record: {record.sleep_date}',
        'active_nav': 'personal',
        'personal_tab': 'sleep',
        'form': form,
        'record': record,
    }
    return render(request, 'personal/sleep/form.html', context)


@login_required
def sleep_delete_view(request, pk):
    """
    Delete a sleep record with confirmation.
    """
    record = get_object_or_404(SleepRecord, pk=pk, user=request.user)
    if request.method == 'POST':
        date_str = str(record.sleep_date)
        record.delete()
        messages.success(request, f'Sleep record for {date_str} deleted.')
        return redirect('personal:sleep_list')

    context = {
        'page_title': 'Confirm Delete Sleep Record',
        'active_nav': 'personal',
        'personal_tab': 'sleep',
        'record': record,
    }
    return render(request, 'personal/sleep/confirm_delete.html', context)


# ==============================================================================
# 6. DECISION JOURNAL
# ==============================================================================

@login_required
def decision_list_view(request):
    """
    Catalog of decisions with filtering, search, and outcome status counters.
    """
    qs = Decision.objects.filter(user=request.user).select_related('category', 'chosen_option')

    # Counters
    total_count = qs.count()
    pending_count = qs.filter(status__in=[DecisionStatus.DRAFT, DecisionStatus.EVALUATING]).count()
    decided_count = qs.filter(status=DecisionStatus.DECIDED).count()
    reviewed_count = qs.filter(status=DecisionStatus.REVIEWED).count()

    # Filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs.order_by('-decision_date', '-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'Decision Journal',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'page_obj': page_obj,
        'total_count': total_count,
        'pending_count': pending_count,
        'decided_count': decided_count,
        'reviewed_count': reviewed_count,
        'status_filter': status_filter,
        'q': q,
    }
    return render(request, 'personal/decisions/list.html', context)


@login_required
def decision_create_view(request):
    """
    Create a new decision log.
    """
    if request.method == 'POST':
        form = DecisionForm(request.POST, user=request.user)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.user = request.user
            decision.save()
            messages.success(request, f'Decision "{decision.title}" created. Now add candidate options.')
            return redirect('personal:decision_detail', pk=decision.pk)
    else:
        form = DecisionForm(user=request.user)

    context = {
        'page_title': 'New Decision',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'form': form,
    }
    return render(request, 'personal/decisions/form.html', context)


@login_required
def decision_detail_view(request, pk):
    """
    Decision details view: options comparison, chosen pathway, and outcome post-mortem.
    """
    decision = get_object_or_404(
        Decision.objects.select_related('category', 'chosen_option').prefetch_related('options', 'outcomes'),
        pk=pk,
        user=request.user
    )
    options = decision.options.all()
    latest_outcome = decision.outcomes.first()

    context = {
        'page_title': decision.title,
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'decision': decision,
        'options': options,
        'latest_outcome': latest_outcome,
    }
    return render(request, 'personal/decisions/detail.html', context)


@login_required
def decision_edit_view(request, pk):
    """
    Edit decision header and context.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    if request.method == 'POST':
        form = DecisionForm(request.POST, instance=decision, user=request.user)
        if form.is_valid():
            decision = form.save()
            messages.success(request, f'Decision "{decision.title}" updated.')
            return redirect('personal:decision_detail', pk=decision.pk)
    else:
        form = DecisionForm(instance=decision, user=request.user)

    context = {
        'page_title': f'Edit: {decision.title}',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'form': form,
        'decision': decision,
    }
    return render(request, 'personal/decisions/form.html', context)


@login_required
def decision_delete_view(request, pk):
    """
    Delete a decision with confirmation.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    if request.method == 'POST':
        title = decision.title
        decision.delete()
        messages.success(request, f'Decision "{title}" deleted.')
        return redirect('personal:decision_list')

    context = {
        'page_title': 'Confirm Delete Decision',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'decision': decision,
    }
    return render(request, 'personal/decisions/confirm_delete.html', context)


@login_required
def decision_option_add_view(request, pk):
    """
    Add a candidate option pathway to a decision.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    if request.method == 'POST':
        form = DecisionOptionForm(request.POST)
        if form.is_valid():
            option = form.save(commit=False)
            option.decision = decision
            option.save()
            if decision.status == DecisionStatus.DRAFT:
                decision.status = DecisionStatus.EVALUATING
                decision.save(update_fields=['status'])
            messages.success(request, f'Option "{option.option_name}" added.')
            return redirect('personal:decision_detail', pk=decision.pk)
    else:
        form = DecisionOptionForm()

    context = {
        'page_title': f'Add Option: {decision.title}',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'form': form,
        'decision': decision,
    }
    return render(request, 'personal/decisions/option_form.html', context)


@login_required
def decision_option_edit_view(request, pk, option_pk):
    """
    Edit an existing candidate option.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    option = get_object_or_404(DecisionOption, pk=option_pk, decision=decision)
    if request.method == 'POST':
        form = DecisionOptionForm(request.POST, instance=option)
        if form.is_valid():
            option = form.save()
            messages.success(request, f'Option "{option.option_name}" updated.')
            return redirect('personal:decision_detail', pk=decision.pk)
    else:
        form = DecisionOptionForm(instance=option)

    context = {
        'page_title': f'Edit Option: {option.option_name}',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'form': form,
        'decision': decision,
        'option': option,
    }
    return render(request, 'personal/decisions/option_form.html', context)


@login_required
def decision_option_delete_view(request, pk, option_pk):
    """
    Delete a candidate option.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    option = get_object_or_404(DecisionOption, pk=option_pk, decision=decision)
    if request.method == 'POST':
        name = option.option_name
        if decision.chosen_option_id == option.id:
            decision.chosen_option = None
            decision.save(update_fields=['chosen_option'])
        option.delete()
        messages.success(request, f'Option "{name}" deleted.')
        return redirect('personal:decision_detail', pk=decision.pk)

    context = {
        'page_title': 'Confirm Delete Option',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'decision': decision,
        'option': option,
    }
    return render(request, 'personal/decisions/confirm_delete.html', context)


@login_required
def decision_select_option_view(request, pk, option_pk):
    """
    Select an option as the chosen pathway, advancing status to DECIDED.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    option = get_object_or_404(DecisionOption, pk=option_pk, decision=decision)
    if request.method == 'POST':
        decision.chosen_option = option
        decision.status = DecisionStatus.DECIDED
        decision.save(update_fields=['chosen_option', 'status'])
        messages.success(request, f'Option "{option.option_name}" selected as chosen pathway.')
    return redirect('personal:decision_detail', pk=decision.pk)


@login_required
def decision_outcome_view(request, pk):
    """
    Record or update the post-mortem evaluation outcome for a decision.
    """
    decision = get_object_or_404(Decision, pk=pk, user=request.user)
    outcome = decision.outcomes.first()

    if request.method == 'POST':
        form = DecisionOutcomeForm(request.POST, instance=outcome, decision=decision)
        if form.is_valid():
            outcome_obj = form.save(commit=False)
            outcome_obj.decision = decision
            outcome_obj.save()
            decision.status = DecisionStatus.REVIEWED
            decision.save(update_fields=['status'])
            messages.success(request, 'Decision outcome evaluation recorded successfully.')
            return redirect('personal:decision_detail', pk=decision.pk)
    else:
        form = DecisionOutcomeForm(instance=outcome, decision=decision)

    context = {
        'page_title': f'Evaluate Outcome: {decision.title}',
        'active_nav': 'personal',
        'personal_tab': 'decisions',
        'form': form,
        'decision': decision,
        'outcome': outcome,
    }
    return render(request, 'personal/decisions/outcome_form.html', context)


# ==============================================================================
# 7. MISTAKE TRACKER
# ==============================================================================

@login_required
def mistake_list_view(request):
    """
    Mistake and learning log catalog with filtering by impact, status, and category.
    """
    qs = Mistake.objects.filter(user=request.user).select_related('category')

    # Counters
    total_count = qs.count()
    open_count = qs.filter(status=MistakeStatus.OPEN).count()
    resolved_count = qs.filter(status=MistakeStatus.RESOLVED).count()
    severe_count = qs.filter(impact_level=MistakeImpact.SEVERE).count()

    # Filters
    impact_filter = request.GET.get('impact', '').strip()
    if impact_filter and impact_filter != 'ALL':
        qs = qs.filter(impact_level=impact_filter)

    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(lesson_learned__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs.order_by('-mistake_date', '-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_title': 'Mistake Tracker',
        'active_nav': 'personal',
        'personal_tab': 'mistakes',
        'page_obj': page_obj,
        'total_count': total_count,
        'open_count': open_count,
        'resolved_count': resolved_count,
        'severe_count': severe_count,
        'impact_filter': impact_filter,
        'status_filter': status_filter,
        'q': q,
    }
    return render(request, 'personal/mistakes/list.html', context)


@login_required
def mistake_create_view(request):
    """
    Log a new mistake with constructive lesson and corrective action.
    """
    if request.method == 'POST':
        form = MistakeForm(request.POST, user=request.user)
        if form.is_valid():
            mistake = form.save(commit=False)
            mistake.user = request.user
            mistake.save()
            messages.success(request, f'Mistake learning log "{mistake.title}" recorded.')
            return redirect('personal:mistake_detail', pk=mistake.pk)
    else:
        form = MistakeForm(user=request.user)

    context = {
        'page_title': 'Log Mistake & Learning',
        'active_nav': 'personal',
        'personal_tab': 'mistakes',
        'form': form,
    }
    return render(request, 'personal/mistakes/form.html', context)


@login_required
def mistake_detail_view(request, pk):
    """
    Full view of mistake reflection, root cause, and corrective action protocol.
    """
    mistake = get_object_or_404(
        Mistake.objects.select_related('category'),
        pk=pk,
        user=request.user
    )
    context = {
        'page_title': mistake.title,
        'active_nav': 'personal',
        'personal_tab': 'mistakes',
        'mistake': mistake,
    }
    return render(request, 'personal/mistakes/detail.html', context)


@login_required
def mistake_edit_view(request, pk):
    """
    Edit a mistake entry.
    """
    mistake = get_object_or_404(Mistake, pk=pk, user=request.user)
    if request.method == 'POST':
        form = MistakeForm(request.POST, instance=mistake, user=request.user)
        if form.is_valid():
            mistake = form.save()
            messages.success(request, f'Mistake "{mistake.title}" updated.')
            return redirect('personal:mistake_detail', pk=mistake.pk)
    else:
        form = MistakeForm(instance=mistake, user=request.user)

    context = {
        'page_title': f'Edit Mistake: {mistake.title}',
        'active_nav': 'personal',
        'personal_tab': 'mistakes',
        'form': form,
        'mistake': mistake,
    }
    return render(request, 'personal/mistakes/form.html', context)


@login_required
def mistake_delete_view(request, pk):
    """
    Delete a mistake entry with confirmation.
    """
    mistake = get_object_or_404(Mistake, pk=pk, user=request.user)
    if request.method == 'POST':
        title = mistake.title
        mistake.delete()
        messages.success(request, f'Mistake "{title}" deleted.')
        return redirect('personal:mistake_list')

    context = {
        'page_title': 'Confirm Delete Mistake',
        'active_nav': 'personal',
        'personal_tab': 'mistakes',
        'mistake': mistake,
    }
    return render(request, 'personal/mistakes/confirm_delete.html', context)
