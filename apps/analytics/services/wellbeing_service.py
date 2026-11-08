from datetime import date, timedelta
import numpy as np
import pandas as pd
from django.db.models import Avg, Count
from apps.personal.models import DailyMetric, SleepRecord
from apps.productivity.models import Task, TaskStatus
from apps.study.models import StudySession

CORRELATION_MIN_OBSERVATIONS = 14


def calculate_pearson_r(x_list, y_list):
    """
    Computes Pearson correlation coefficient between two numeric series.
    Returns (r_value, n_count). Returns (None, n_count) if data has zero variance or n < 3.
    """
    clean_pairs = [(x, y) for x, y in zip(x_list, y_list) if x is not None and y is not None]
    n = len(clean_pairs)
    if n < 3:
        return None, n

    xs = np.array([p[0] for p in clean_pairs], dtype=float)
    ys = np.array([p[1] for p in clean_pairs], dtype=float)

    # Check for zero variance
    std_x = np.std(xs)
    std_y = np.std(ys)
    if std_x == 0 or std_y == 0:
        return 0.0, n

    r = float(np.corrcoef(xs, ys)[0, 1])
    if np.isnan(r):
        return None, n
    return round(r, 2), n


def interpret_correlation(r, label_x, label_y):
    """
    Generates cautious, scientifically sound non-causal interpretation.
    """
    if r is None:
        return "Insufficient variation to establish a correlation."
    if abs(r) < 0.2:
        return f"Little to no linear association between {label_x.lower()} and {label_y.lower()} during this period (r = {r:+.2f})."
    elif r >= 0.5:
        return f"During the recorded period, higher {label_x.lower()} was strongly associated with higher {label_y.lower()} (r = {r:+.2f})."
    elif r >= 0.2:
        return f"Higher {label_x.lower()} showed a moderate positive association with {label_y.lower()} (r = {r:+.2f})."
    elif r <= -0.5:
        return f"Higher {label_x.lower()} was strongly associated with lower {label_y.lower()} (r = {r:+.2f})."
    else:
        return f"Higher {label_x.lower()} showed a moderate inverse association with {label_y.lower()} (r = {r:+.2f})."


def get_wellbeing_metrics(user, start_date: date, end_date: date) -> dict:
    """
    Computes personal well-being averages, trends, and exploratory correlations.
    Adheres strictly to minimum observation thresholds and non-causal language.
    """
    days_count = max(1, (end_date - start_date).days + 1)

    # 1. Fetch DailyMetrics in Range
    metrics_qs = DailyMetric.objects.filter(
        user=user,
        metric_date__range=(start_date, end_date)
    ).order_by('metric_date')

    # Aggregates
    agg = metrics_qs.aggregate(
        avg_mood=Avg('mood_score'),
        avg_energy=Avg('energy_score'),
        avg_stress=Avg('stress_score'),
        avg_sleep=Avg('sleep_hours'),
    )

    avg_mood = round(agg['avg_mood'] or 0.0, 1)
    avg_energy = round(agg['avg_energy'] or 0.0, 1)
    avg_stress = round(agg['avg_stress'] or 0.0, 1)
    avg_sleep = round(agg['avg_sleep'] or 0.0, 1)

    # Date series for charts
    dates_list = []
    moods_list = []
    energies_list = []
    stresses_list = []
    sleeps_list = []

    metrics_by_date = {m.metric_date: m for m in metrics_qs}

    curr = start_date
    while curr <= end_date:
        dates_list.append(curr.strftime('%d %b'))
        m_rec = metrics_by_date.get(curr)
        if m_rec:
            moods_list.append(m_rec.mood_score)
            energies_list.append(m_rec.energy_score)
            stresses_list.append(m_rec.stress_score)
            sleeps_list.append(float(m_rec.sleep_hours) if m_rec.sleep_hours is not None else None)
        else:
            moods_list.append(None)
            energies_list.append(None)
            stresses_list.append(None)
            sleeps_list.append(None)
        curr += timedelta(days=1)

    # 2. Correlation Analysis
    # We query all historical check-in paired data for the user to maximize statistical validity
    all_user_metrics = DailyMetric.objects.filter(user=user).order_by('metric_date')

    # Prepare paired lists
    sleep_vals = []
    energy_vals = []
    mood_vals = []
    stress_vals = []
    study_mins_vals = []
    task_comp_vals = []

    # Map daily study minutes and task completion counts
    all_study_sessions = StudySession.objects.filter(user=user, duration_minutes__gt=0)
    study_by_date = {}
    for s in all_study_sessions:
        study_by_date[s.session_date] = study_by_date.get(s.session_date, 0) + s.duration_minutes

    all_completed_tasks = Task.objects.filter(user=user, status=TaskStatus.COMPLETED)
    tasks_by_date = {}
    for t in all_completed_tasks:
        if t.completed_at:
            t_date = t.completed_at.date()
            tasks_by_date[t_date] = tasks_by_date.get(t_date, 0) + 1

    for m in all_user_metrics:
        d = m.metric_date
        sl = float(m.sleep_hours) if m.sleep_hours is not None else None
        en = m.energy_score
        mo = m.mood_score
        st = m.stress_score

        study_m = study_by_date.get(d, 0)
        tasks_c = tasks_by_date.get(d, 0)

        sleep_vals.append(sl)
        energy_vals.append(en)
        mood_vals.append(mo)
        stress_vals.append(st)
        study_mins_vals.append(study_m)
        task_comp_vals.append(tasks_c)

    # Run correlations with minimum observation threshold check
    correlations = []

    # Pair 1: Sleep vs Energy
    r_sleep_energy, n_se = calculate_pearson_r(sleep_vals, energy_vals)
    correlations.append({
        'pair_id': 'sleep_energy',
        'title': 'Sleep Duration vs Energy Score',
        'var_x': 'Sleep Duration (Hours)',
        'var_y': 'Energy Score (1-10)',
        'r': r_sleep_energy,
        'n': n_se,
        'has_min_data': n_se >= CORRELATION_MIN_OBSERVATIONS,
        'min_required': CORRELATION_MIN_OBSERVATIONS,
        'interpretation': interpret_correlation(r_sleep_energy, 'Sleep duration', 'Energy score'),
    })

    # Pair 2: Sleep vs Mood
    r_sleep_mood, n_sm = calculate_pearson_r(sleep_vals, mood_vals)
    correlations.append({
        'pair_id': 'sleep_mood',
        'title': 'Sleep Duration vs Mood Score',
        'var_x': 'Sleep Duration (Hours)',
        'var_y': 'Mood Score (1-10)',
        'r': r_sleep_mood,
        'n': n_sm,
        'has_min_data': n_sm >= CORRELATION_MIN_OBSERVATIONS,
        'min_required': CORRELATION_MIN_OBSERVATIONS,
        'interpretation': interpret_correlation(r_sleep_mood, 'Sleep duration', 'Mood score'),
    })

    # Pair 3: Mood vs Study Duration
    r_mood_study, n_ms = calculate_pearson_r(mood_vals, [m / 60.0 for m in study_mins_vals])
    correlations.append({
        'pair_id': 'mood_study',
        'title': 'Mood Score vs Study Duration',
        'var_x': 'Mood Score (1-10)',
        'var_y': 'Study Duration (Hours)',
        'r': r_mood_study,
        'n': n_ms,
        'has_min_data': n_ms >= CORRELATION_MIN_OBSERVATIONS,
        'min_required': CORRELATION_MIN_OBSERVATIONS,
        'interpretation': interpret_correlation(r_mood_study, 'Mood score', 'Study duration'),
    })

    # Pair 4: Energy vs Task Completion
    r_energy_tasks, n_et = calculate_pearson_r(energy_vals, task_comp_vals)
    correlations.append({
        'pair_id': 'energy_tasks',
        'title': 'Energy Score vs Tasks Completed',
        'var_x': 'Energy Score (1-10)',
        'var_y': 'Tasks Completed',
        'r': r_energy_tasks,
        'n': n_et,
        'has_min_data': n_et >= CORRELATION_MIN_OBSERVATIONS,
        'min_required': CORRELATION_MIN_OBSERVATIONS,
        'interpretation': interpret_correlation(r_energy_tasks, 'Energy score', 'Task completion'),
    })

    # Pair 5: Stress vs Productivity / Tasks
    r_stress_tasks, n_st = calculate_pearson_r(stress_vals, task_comp_vals)
    correlations.append({
        'pair_id': 'stress_tasks',
        'title': 'Stress Score vs Tasks Completed',
        'var_x': 'Stress Score (1-10)',
        'var_y': 'Tasks Completed',
        'r': r_stress_tasks,
        'n': n_st,
        'has_min_data': n_st >= CORRELATION_MIN_OBSERVATIONS,
        'min_required': CORRELATION_MIN_OBSERVATIONS,
        'interpretation': interpret_correlation(r_stress_tasks, 'Stress score', 'Task completion'),
    })

    return {
        'avg_mood': avg_mood,
        'avg_energy': avg_energy,
        'avg_stress': avg_stress,
        'avg_sleep': avg_sleep,
        'dates_list': dates_list,
        'moods_list': moods_list,
        'energies_list': energies_list,
        'stresses_list': stresses_list,
        'sleeps_list': sleeps_list,
        'correlations': correlations,
        'sleep_vals': [s for s in sleep_vals if s is not None],
        'energy_vals': [e for e in energy_vals if e is not None],
    }
