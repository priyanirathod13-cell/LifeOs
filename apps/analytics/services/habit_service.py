from datetime import date, timedelta
from django.db.models import Count, Q
from apps.productivity.models import Habit, HabitFrequency, HabitLog
from apps.productivity.views import calculate_habit_streak


def get_habit_metrics(user, start_date: date, end_date: date) -> dict:
    """
    Computes frequency-aware habit analytics for the user.
    Respects DAILY vs WEEKLY vs MONTHLY frequencies without artificially penalizing non-daily habits.
    """
    days_count = max(1, (end_date - start_date).days + 1)
    weeks_count = max(1.0, days_count / 7.0)
    months_count = max(1.0, days_count / 30.0)

    habits = Habit.objects.filter(user=user, is_active=True).select_related('category')
    total_active_habits = habits.count()

    all_logs = HabitLog.objects.filter(
        user=user,
        log_date__range=(start_date, end_date)
    ).select_related('habit')

    habit_metrics_list = []
    total_expected_sum = 0
    total_completed_sum = 0

    habit_names_for_chart = []
    habit_rates_for_chart = []

    for habit in habits:
        h_logs = [l for l in all_logs if l.habit_id == habit.id]
        completed_logs = sum(1 for l in h_logs if l.completed)

        # Determine frequency-aware expected count
        if habit.frequency == HabitFrequency.DAILY:
            # Expected once per day
            expected = days_count
        elif habit.frequency == HabitFrequency.WEEKLY:
            # Expected target_count times per week
            expected = max(1, round(weeks_count * habit.target_count))
        elif habit.frequency == HabitFrequency.MONTHLY:
            expected = max(1, round(months_count * habit.target_count))
        else:
            expected = days_count

        total_expected_sum += expected
        total_completed_sum += completed_logs

        rate = round((completed_logs / expected * 100.0) if expected > 0 else 0.0, 1)

        # Habit streak validity:
        streaks = calculate_habit_streak(habit, user)
        streak_val = streaks['current_streak'] if habit.frequency == HabitFrequency.DAILY else None

        item = {
            'id': habit.id,
            'name': habit.name,
            'category': habit.category.name if habit.category else 'General',
            'category_color': habit.category.color if habit.category else '#818CF8',
            'frequency': habit.get_frequency_display(),
            'frequency_raw': habit.frequency,
            'target_count': habit.target_count,
            'completed_count': completed_logs,
            'expected_count': expected,
            'completion_rate': rate,
            'streak': streak_val,
            'streak_raw': streaks['current_streak'],
        }
        habit_metrics_list.append(item)
        habit_names_for_chart.append(habit.name)
        habit_rates_for_chart.append(rate)

    # Overall habit completion rate
    overall_completion_rate = round(
        (total_completed_sum / total_expected_sum * 100.0) if total_expected_sum > 0 else 0.0,
        1
    )

    # Sort to find most and least consistent
    sorted_by_rate = sorted(habit_metrics_list, key=lambda x: x['completion_rate'], reverse=True)
    best_performing = [h for h in sorted_by_rate if h['completion_rate'] >= 60.0][:5]
    inconsistent_habits = [h for h in sorted_by_rate if h['completion_rate'] < 60.0]

    return {
        'total_active_habits': total_active_habits,
        'overall_completion_rate': overall_completion_rate,
        'total_completed_logs': total_completed_sum,
        'total_expected_completions': total_expected_sum,
        'habits_list': habit_metrics_list,
        'best_performing_habits': best_performing,
        'inconsistent_habits': inconsistent_habits,
        'habit_names': habit_names_for_chart,
        'habit_rates': habit_rates_for_chart,
    }
