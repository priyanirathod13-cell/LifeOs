from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import DismissedInsight
from .services import charts
from .services.comparison_service import compare_periods
from .services.date_utils import get_user_today, parse_date_range
from .services.finance_service import get_finance_metrics
from .services.habit_service import get_habit_metrics
from .services.insights_engine import generate_behavioral_insights
from .services.productivity_service import get_productivity_metrics
from .services.study_service import get_study_metrics
from .services.time_service import get_time_metrics
from .services.wellbeing_service import get_wellbeing_metrics


@login_required
def analytics_dashboard_view(request):
    """
    Main Executive Analytics Dashboard for LifeOS.
    Summarizes productivity, study, habits, well-being, time management, and finance,
    and surfaces active behavioral intelligence observations.
    """
    user = request.user
    today = get_user_today(user)
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']
    prev_start = dt_info['prev_start_date']
    prev_end = dt_info['prev_end_date']
    period_label = dt_info['label']

    # Retrieve metrics across all modules
    prod_metrics = get_productivity_metrics(user, start_date, end_date, today=today)
    study_metrics = get_study_metrics(user, start_date, end_date, today=today)
    habit_metrics = get_habit_metrics(user, start_date, end_date)
    time_metrics = get_time_metrics(user, start_date, end_date)
    wb_metrics = get_wellbeing_metrics(user, start_date, end_date)
    fin_metrics = get_finance_metrics(user, start_date, end_date)

    # Behavioral Insights (top active)
    all_insights = generate_behavioral_insights(
        user, start_date, end_date, prev_start, prev_end, period_label=period_label
    )
    active_insights = [i for i in all_insights if not i['is_dismissed']]

    # Render Charts
    prod_chart_html = charts.render_productivity_trend_chart(
        prod_metrics['date_series'],
        prod_metrics['completed_series'],
        prod_metrics['minutes_series']
    )
    time_chart_html = charts.render_time_distribution_donut(
        time_metrics['dist_labels'],
        time_metrics['dist_values']
    )
    study_chart_html = charts.render_study_hours_bar_chart(
        study_metrics['daily_dates'],
        study_metrics['daily_hours']
    )

    context = {
        'page_title': 'Analytics & Behavioral Intelligence',
        'active_nav': 'analytics',
        'analytics_tab': 'overview',
        'dt_info': dt_info,
        'prod': prod_metrics,
        'study': study_metrics,
        'habits': habit_metrics,
        'time': time_metrics,
        'wb': wb_metrics,
        'fin': fin_metrics,
        'insights': active_insights[:4],
        'total_insights_count': len(active_insights),
        'prod_chart_html': prod_chart_html,
        'time_chart_html': time_chart_html,
        'study_chart_html': study_chart_html,
    }
    return render(request, 'analytics/dashboard.html', context)


@login_required
def productivity_analytics_view(request):
    """
    Dedicated Productivity Analytics page.
    Task performance, duration estimation errors, and activity volume over time.
    """
    user = request.user
    today = get_user_today(user)
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']

    prod_metrics = get_productivity_metrics(user, start_date, end_date, today=today)

    trend_chart_html = charts.render_productivity_trend_chart(
        prod_metrics['date_series'],
        prod_metrics['completed_series'],
        prod_metrics['minutes_series']
    )

    # Estimation accuracy planned vs actual chart
    est_labels = [t['title'][:20] for t in prod_metrics['underestimated_tasks'][:4] + prod_metrics['overestimated_tasks'][:4]]
    est_planned = [round(t['estimated'] / 60.0, 1) for t in prod_metrics['underestimated_tasks'][:4] + prod_metrics['overestimated_tasks'][:4]]
    est_actual = [round(t['actual'] / 60.0, 1) for t in prod_metrics['underestimated_tasks'][:4] + prod_metrics['overestimated_tasks'][:4]]
    est_chart_html = charts.render_planned_vs_actual_chart(est_labels, est_planned, est_actual)

    context = {
        'page_title': 'Productivity Analytics',
        'active_nav': 'productivity_analytics',
        'analytics_tab': 'productivity',
        'dt_info': dt_info,
        'prod': prod_metrics,
        'trend_chart_html': trend_chart_html,
        'est_chart_html': est_chart_html,
    }
    return render(request, 'analytics/productivity.html', context)


@login_required
def study_analytics_view(request):
    """
    Dedicated Study Analytics page.
    Study hours, subject-wise investment, syllabus progress velocity, and planned vs actual study.
    """
    user = request.user
    today = get_user_today(user)
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']

    study_metrics = get_study_metrics(user, start_date, end_date, today=today)

    hours_chart_html = charts.render_study_hours_bar_chart(
        study_metrics['daily_dates'],
        study_metrics['daily_hours']
    )
    subject_chart_html = charts.render_subject_comparison_chart(
        study_metrics['subject_names'],
        study_metrics['subject_hours_list'],
        study_metrics['subject_colors']
    )

    context = {
        'page_title': 'Study Analytics',
        'active_nav': 'study_analytics',
        'analytics_tab': 'study',
        'dt_info': dt_info,
        'study': study_metrics,
        'hours_chart_html': hours_chart_html,
        'subject_chart_html': subject_chart_html,
    }
    return render(request, 'analytics/study.html', context)


@login_required
def habit_analytics_view(request):
    """
    Dedicated Habit Analytics page.
    Frequency-aware completion rates, streaks, best performing vs friction habits.
    """
    user = request.user
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']

    habit_metrics = get_habit_metrics(user, start_date, end_date)

    habit_chart_html = charts.render_habit_completion_chart(
        habit_metrics['habit_names'],
        habit_metrics['habit_rates']
    )

    context = {
        'page_title': 'Habit Analytics',
        'active_nav': 'analytics',
        'analytics_tab': 'habits',
        'dt_info': dt_info,
        'habits': habit_metrics,
        'habit_chart_html': habit_chart_html,
    }
    return render(request, 'analytics/habits.html', context)


@login_required
def time_analytics_view(request):
    """
    Dedicated Time Management Analytics page.
    Time distribution by category, schedule block adherence, and time estimation.
    """
    user = request.user
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']

    time_metrics = get_time_metrics(user, start_date, end_date)

    donut_chart_html = charts.render_time_distribution_donut(
        time_metrics['dist_labels'],
        time_metrics['dist_values']
    )

    context = {
        'page_title': 'Time Management Analytics',
        'active_nav': 'analytics',
        'analytics_tab': 'time',
        'dt_info': dt_info,
        'time': time_metrics,
        'donut_chart_html': donut_chart_html,
    }
    return render(request, 'analytics/time.html', context)


@login_required
def wellbeing_analytics_view(request):
    """
    Dedicated Personal Well-being Analytics page.
    Mood, energy, stress, sleep trends, weekly/monthly averages, and exploratory correlation analysis.
    """
    user = request.user
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']

    wb_metrics = get_wellbeing_metrics(user, start_date, end_date)

    trend_chart_html = charts.render_mood_sleep_trend_chart(
        wb_metrics['dates_list'],
        wb_metrics['moods_list'],
        wb_metrics['sleeps_list'],
        wb_metrics['energies_list'],
        wb_metrics['stresses_list']
    )

    # Scatter plot for Sleep vs Energy correlation if data available
    scatter_chart_html = charts.render_correlation_scatter_chart(
        wb_metrics['sleep_vals'],
        wb_metrics['energy_vals'],
        'Sleep Duration (Hours)',
        'Energy Score (1-10)',
        'Sleep vs Energy Correlation'
    )

    context = {
        'page_title': 'Well-being & Correlations',
        'active_nav': 'analytics',
        'analytics_tab': 'wellbeing',
        'dt_info': dt_info,
        'wb': wb_metrics,
        'trend_chart_html': trend_chart_html,
        'scatter_chart_html': scatter_chart_html,
    }
    return render(request, 'analytics/wellbeing.html', context)


@login_required
def behavioral_insights_view(request):
    """
    Dedicated Behavioral Insights Hub.
    Rule-based observations categorized into Productivity, Study, Habits, Time, Well-being, Finance.
    Supports dismissing and restoring insights.
    """
    user = request.user
    dt_info = parse_date_range(user, request.GET)

    start_date = dt_info['start_date']
    end_date = dt_info['end_date']
    prev_start = dt_info['prev_start_date']
    prev_end = dt_info['prev_end_date']
    period_label = dt_info['label']

    category_filter = request.GET.get('category', 'ALL').upper()
    show_dismissed = request.GET.get('show_dismissed', 'false').lower() == 'true'

    all_insights = generate_behavioral_insights(
        user, start_date, end_date, prev_start, prev_end, period_label=period_label
    )

    if show_dismissed:
        filtered_insights = [i for i in all_insights if i['is_dismissed']]
    else:
        filtered_insights = [i for i in all_insights if not i['is_dismissed']]

    if category_filter != 'ALL':
        filtered_insights = [i for i in filtered_insights if i['category'] == category_filter]

    context = {
        'page_title': 'Behavioral Insights Engine',
        'active_nav': 'behavioral_insights',
        'analytics_tab': 'insights',
        'dt_info': dt_info,
        'insights': filtered_insights,
        'category_filter': category_filter,
        'show_dismissed': show_dismissed,
        'active_count': sum(1 for i in all_insights if not i['is_dismissed']),
        'dismissed_count': sum(1 for i in all_insights if i['is_dismissed']),
    }
    return render(request, 'analytics/insights.html', context)


@login_required
@require_POST
def dismiss_insight_view(request):
    """
    Allows user to dismiss a specific behavioral insight.
    """
    insight_key = request.POST.get('insight_key', '').strip()
    if insight_key:
        DismissedInsight.objects.get_or_create(user=request.user, insight_key=insight_key)
        messages.success(request, 'Insight dismissed.')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'dismissed': insight_key})

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'analytics:insights'
    return redirect(next_url)


@login_required
@require_POST
def restore_insight_view(request):
    """
    Restores a previously dismissed insight.
    """
    insight_key = request.POST.get('insight_key', '').strip()
    if insight_key:
        DismissedInsight.objects.filter(user=request.user, insight_key=insight_key).delete()
        messages.success(request, 'Insight restored to active feed.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'analytics:insights'
    return redirect(next_url)


@login_required
def comparison_view(request):
    """
    Dedicated Multi-Period Comparison System.
    Compares two temporal periods across productivity, study, habits, well-being, and finances.
    """
    user = request.user
    today = get_user_today(user)
    dt_info = parse_date_range(user, request.GET)

    curr_start = dt_info['start_date']
    curr_end = dt_info['end_date']
    prev_start = dt_info['prev_start_date']
    prev_end = dt_info['prev_end_date']

    comp_results = compare_periods(user, curr_start, curr_end, prev_start, prev_end)

    context = {
        'page_title': 'Period Comparison System',
        'active_nav': 'analytics',
        'analytics_tab': 'compare',
        'dt_info': dt_info,
        'comparisons': comp_results['comparisons'],
        'curr_label': dt_info['label'],
        'prev_label': dt_info['prev_label'],
    }
    return render(request, 'analytics/compare.html', context)
