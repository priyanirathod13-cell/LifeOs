from datetime import date
from decimal import Decimal
from .productivity_service import get_productivity_metrics
from .study_service import get_study_metrics
from .habit_service import get_habit_metrics
from .wellbeing_service import get_wellbeing_metrics
from .finance_service import get_finance_metrics


def compute_delta(curr_val, prev_val, higher_is_better=True, is_currency=False):
    """
    Computes absolute difference and percentage change between current and previous values.
    Gracefully handles zero denominators and missing data without division errors.
    """
    if curr_val is None or prev_val is None:
        return {
            'current': curr_val,
            'previous': prev_val,
            'diff': None,
            'pct_change': None,
            'pct_display': 'N/A',
            'status': 'neutral',
        }

    # Convert Decimals to float for calculation if needed
    curr_f = float(curr_val)
    prev_f = float(prev_val)
    diff = round(curr_f - prev_f, 2)

    if prev_f == 0.0:
        pct_display = 'N/A (baseline was 0)'
        pct_change = None
    else:
        pct = round(((curr_f - prev_f) / abs(prev_f)) * 100.0, 1)
        pct_change = pct
        pct_display = f"{pct:+.1f}%"

    # Status: positive, negative, neutral
    if diff == 0.0:
        status = 'neutral'
    elif (diff > 0 and higher_is_better) or (diff < 0 and not higher_is_better):
        status = 'positive'
    else:
        status = 'negative'

    return {
        'current': curr_f,
        'previous': prev_f,
        'diff': diff,
        'pct_change': pct_change,
        'pct_display': pct_display,
        'status': status,
    }


def compare_periods(user, curr_start: date, curr_end: date, prev_start: date, prev_end: date) -> dict:
    """
    Computes multi-dimensional period-over-period comparison metrics for LifeOS.
    """
    # 1. Productivity metrics for both periods
    curr_prod = get_productivity_metrics(user, curr_start, curr_end)
    prev_prod = get_productivity_metrics(user, prev_start, prev_end)

    # 2. Study metrics
    curr_study = get_study_metrics(user, curr_start, curr_end)
    prev_study = get_study_metrics(user, prev_start, prev_end)

    # 3. Habit metrics
    curr_habit = get_habit_metrics(user, curr_start, curr_end)
    prev_habit = get_habit_metrics(user, prev_start, prev_end)

    # 4. Well-being metrics
    curr_wb = get_wellbeing_metrics(user, curr_start, curr_end)
    prev_wb = get_wellbeing_metrics(user, prev_start, prev_end)

    # 5. Finance metrics
    curr_fin = get_finance_metrics(user, curr_start, curr_end)
    prev_fin = get_finance_metrics(user, prev_start, prev_end)

    comparisons = [
        # Productivity
        {
            'category': 'Productivity',
            'metric': 'Tasks Completed',
            'unit': 'tasks',
            **compute_delta(curr_prod['completed_tasks'], prev_prod['completed_tasks'], higher_is_better=True)
        },
        {
            'category': 'Productivity',
            'metric': 'Task Completion Rate',
            'unit': '%',
            **compute_delta(curr_prod['completion_rate'], prev_prod['completion_rate'], higher_is_better=True)
        },
        {
            'category': 'Productivity',
            'metric': 'Total Productive Time Tracked',
            'unit': 'hours',
            **compute_delta(curr_prod['total_tracked_hours'], prev_prod['total_tracked_hours'], higher_is_better=True)
        },
        # Study
        {
            'category': 'Study',
            'metric': 'Total Study Duration',
            'unit': 'hours',
            **compute_delta(curr_study['total_study_hours'], prev_study['total_study_hours'], higher_is_better=True)
        },
        {
            'category': 'Study',
            'metric': 'Study Consistency',
            'unit': '%',
            **compute_delta(curr_study['study_consistency_rate'], prev_study['study_consistency_rate'], higher_is_better=True)
        },
        {
            'category': 'Study',
            'metric': 'Active Study Sessions',
            'unit': 'sessions',
            **compute_delta(curr_study['sessions_count'], prev_study['sessions_count'], higher_is_better=True)
        },
        # Habits
        {
            'category': 'Habits',
            'metric': 'Overall Habit Completion Rate',
            'unit': '%',
            **compute_delta(curr_habit['overall_completion_rate'], prev_habit['overall_completion_rate'], higher_is_better=True)
        },
        # Well-being
        {
            'category': 'Well-being',
            'metric': 'Average Mood Score',
            'unit': '/10',
            **compute_delta(curr_wb['avg_mood'], prev_wb['avg_mood'], higher_is_better=True)
        },
        {
            'category': 'Well-being',
            'metric': 'Average Energy Score',
            'unit': '/10',
            **compute_delta(curr_wb['avg_energy'], prev_wb['avg_energy'], higher_is_better=True)
        },
        {
            'category': 'Well-being',
            'metric': 'Average Sleep Duration',
            'unit': 'hours',
            **compute_delta(curr_wb['avg_sleep'], prev_wb['avg_sleep'], higher_is_better=True)
        },
        {
            'category': 'Well-being',
            'metric': 'Average Stress Level',
            'unit': '/10',
            **compute_delta(curr_wb['avg_stress'], prev_wb['avg_stress'], higher_is_better=False)
        },
        # Finance
        {
            'category': 'Finance',
            'metric': 'Total Recorded Income',
            'unit': '₹',
            **compute_delta(curr_fin['total_income'], prev_fin['total_income'], higher_is_better=True, is_currency=True)
        },
        {
            'category': 'Finance',
            'metric': 'Total Recorded Expenses',
            'unit': '₹',
            **compute_delta(curr_fin['total_expenses'], prev_fin['total_expenses'], higher_is_better=False, is_currency=True)
        },
        {
            'category': 'Finance',
            'metric': 'Net Savings / Balance',
            'unit': '₹',
            **compute_delta(curr_fin['net_balance'], prev_fin['net_balance'], higher_is_better=True, is_currency=True)
        },
    ]

    return {
        'comparisons': comparisons,
        'curr_prod': curr_prod,
        'prev_prod': prev_prod,
        'curr_study': curr_study,
        'prev_study': prev_study,
        'curr_habit': curr_habit,
        'prev_habit': prev_habit,
        'curr_wb': curr_wb,
        'prev_wb': prev_wb,
        'curr_fin': curr_fin,
        'prev_fin': prev_fin,
    }
