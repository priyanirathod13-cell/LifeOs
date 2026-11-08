from datetime import date
from decimal import Decimal
from apps.analytics.models import DismissedInsight
from .productivity_service import get_productivity_metrics
from .study_service import get_study_metrics
from .habit_service import get_habit_metrics
from .time_service import get_time_metrics
from .wellbeing_service import get_wellbeing_metrics
from .finance_service import get_finance_metrics


def generate_behavioral_insights(
    user,
    curr_start: date,
    curr_end: date,
    prev_start: date,
    prev_end: date,
    period_label: str = 'Recent Period'
) -> list:
    """
    Evaluates transparent, deterministic, rule-based behavioral heuristics across
    the user's recorded productivity, study, habit, time, well-being, and financial data.
    Every single insight is grounded exclusively in real database records.
    """
    today = date.today()

    # Pre-fetch user's dismissed insight keys
    dismissed_keys = set(
        DismissedInsight.objects.filter(user=user).values_list('insight_key', flat=True)
    )

    insights = []

    # 1. Productivity Insights
    prod_curr = get_productivity_metrics(user, curr_start, curr_end, today=today)
    prod_prev = get_productivity_metrics(user, prev_start, prev_end, today=today)

    curr_comp = prod_curr['completed_tasks']
    prev_comp = prod_prev['completed_tasks']

    # Rule 1.1: Task Completion Velocity Surge
    if prev_comp > 0 and curr_comp >= prev_comp * 1.25 and curr_comp >= 3:
        inc_pct = round(((curr_comp - prev_comp) / prev_comp) * 100)
        key = f"prod_velocity_surge_{curr_start}_{curr_end}"
        insights.append({
            'key': key,
            'title': 'Task Completion Velocity Increased',
            'category': 'PRODUCTIVITY',
            'category_badge': 'badge-success',
            'description': f"You completed {curr_comp} tasks during {period_label}, up {inc_pct}% compared with the prior period ({prev_comp} tasks).",
            'supporting_metric': f"{curr_comp} completed vs {prev_comp} previous (+{inc_pct}%)",
            'period': period_label,
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })
    # Rule 1.2: Task Completion Velocity Dip
    elif prev_comp >= 4 and curr_comp <= prev_comp * 0.70:
        dec_pct = round(((prev_comp - curr_comp) / prev_comp) * 100)
        key = f"prod_velocity_dip_{curr_start}_{curr_end}"
        insights.append({
            'key': key,
            'title': 'Task Completion Rate Decreased',
            'category': 'PRODUCTIVITY',
            'category_badge': 'badge-warning',
            'description': f"Task completions decreased by {dec_pct}% in {period_label} ({curr_comp} completed vs {prev_comp} in prior period).",
            'supporting_metric': f"{curr_comp} completed vs {prev_comp} previous (-{dec_pct}%)",
            'period': period_label,
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })

    # Rule 1.3: Duration Estimation Bias
    est_comps = prod_curr['estimation_comparisons_count']
    avg_err = prod_curr['avg_estimation_error']
    if est_comps >= 3 and avg_err is not None:
        if avg_err >= 15.0:
            key = f"prod_underestimation_{curr_start}_{curr_end}"
            insights.append({
                'key': key,
                'title': 'Estimation Bias: Tasks Frequently Take Longer Than Expected',
                'category': 'PRODUCTIVITY',
                'category_badge': 'badge-warning',
                'description': f"Across {est_comps} timed tasks, your actual completion duration averaged {avg_err:.1f} minutes longer than initial estimates.",
                'supporting_metric': f"Average estimation error: +{avg_err:.1f} minutes ({est_comps} tasks evaluated)",
                'period': period_label,
                'confidence': 'HIGH',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })
        elif avg_err <= -15.0:
            key = f"prod_overestimation_{curr_start}_{curr_end}"
            insights.append({
                'key': key,
                'title': 'Planning Tendency: Tasks Completed Faster Than Estimated',
                'category': 'PRODUCTIVITY',
                'category_badge': 'badge-accent',
                'description': f"Across {est_comps} timed tasks, you completed action items an average of {abs(avg_err):.1f} minutes faster than planned.",
                'supporting_metric': f"Average estimation error: {avg_err:.1f} minutes",
                'period': period_label,
                'confidence': 'HIGH',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })

    # 2. Study Insights
    study_curr = get_study_metrics(user, curr_start, curr_end, today=today)
    study_subj_durations = study_curr['subject_durations']
    total_study_hrs = study_curr['total_study_hours']

    # Rule 2.1: Subject Study Imbalance
    if len(study_subj_durations) >= 2 and total_study_hrs >= 3.0:
        top_subj = study_subj_durations[0]
        bottom_subj = study_subj_durations[-1]
        if top_subj['percentage'] >= 60.0 and bottom_subj['percentage'] <= 10.0:
            key = f"study_imbalance_{top_subj['id']}_{bottom_subj['id']}_{curr_start}_{curr_end}"
            insights.append({
                'key': key,
                'title': 'Subject Study Distribution Imbalance',
                'category': 'STUDY',
                'category_badge': 'badge-accent',
                'description': f"You invested {top_subj['hours']:.1f} hours ({top_subj['percentage']}%) in {top_subj['name']}, while {bottom_subj['name']} received only {bottom_subj['hours']:.1f} hours ({bottom_subj['percentage']}%).",
                'supporting_metric': f"{top_subj['name']}: {top_subj['percentage']}% vs {bottom_subj['name']}: {bottom_subj['percentage']}% of study time",
                'period': period_label,
                'confidence': 'HIGH',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })

    # Rule 2.2: Approaching Topic Deadlines Near Target Date
    slow_subjs = study_curr['slow_progress_subjects']
    if slow_subjs:
        s = slow_subjs[0]
        key = f"study_deadline_lag_{s['id']}_{today}"
        insights.append({
            'key': key,
            'title': f"Syllabus Milestone Approaching: {s['name']}",
            'category': 'STUDY',
            'category_badge': 'badge-warning',
            'description': f"{s['remaining_topics']} topics remain incomplete for {s['name']} with target milestone date approaching on {s['target_date']}.",
            'supporting_metric': f"{s['completed_topics']}/{s['total_topics']} topics completed ({s['rate']}%)",
            'period': 'Current Milestone',
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })

    # 3. Habit Insights
    habit_curr = get_habit_metrics(user, curr_start, curr_end)
    best_habits = habit_curr['best_performing_habits']
    inconsistent_habits = habit_curr['inconsistent_habits']

    # Rule 3.1: Keystone Habit High Consistency
    if best_habits and best_habits[0]['completion_rate'] >= 80.0 and best_habits[0]['expected_count'] >= 3:
        h = best_habits[0]
        key = f"habit_keystone_{h['id']}_{curr_start}_{curr_end}"
        insights.append({
            'key': key,
            'title': f"Consistent Keystone Habit: {h['name']}",
            'category': 'HABITS',
            'category_badge': 'badge-success',
            'description': f"Your '{h['name']}' habit achieved a {h['completion_rate']:.0f}% completion rate during {period_label} ({h['completed_count']}/{h['expected_count']} target completions).",
            'supporting_metric': f"{h['completion_rate']:.0f}% completion rate ({h['completed_count']}/{h['expected_count']} logged)",
            'period': period_label,
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })

    # Rule 3.2: Habit Friction
    if inconsistent_habits:
        low_h = inconsistent_habits[-1]
        if low_h['expected_count'] >= 3 and low_h['completion_rate'] < 40.0:
            key = f"habit_friction_{low_h['id']}_{curr_start}_{curr_end}"
            insights.append({
                'key': key,
                'title': f"Habit Friction Observed: {low_h['name']}",
                'category': 'HABITS',
                'category_badge': 'badge-warning',
                'description': f"'{low_h['name']}' achieved {low_h['completion_rate']:.0f}% completion in {period_label}. Consider reducing target friction or pairing it with an existing routine.",
                'supporting_metric': f"{low_h['completed_count']}/{low_h['expected_count']} target completions logged ({low_h['completion_rate']:.0f}%)",
                'period': period_label,
                'confidence': 'MEDIUM',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })

    # 4. Time Management Insights
    time_curr = get_time_metrics(user, curr_start, curr_end)
    tot_sched = time_curr['total_scheduled_blocks']
    adh_rate = time_curr['adherence_rate']

    if tot_sched >= 5:
        if adh_rate >= 80.0:
            key = f"time_high_adherence_{curr_start}_{curr_end}"
            insights.append({
                'key': key,
                'title': 'High Schedule Adherence',
                'category': 'TIME',
                'category_badge': 'badge-success',
                'description': f"You completed {adh_rate:.0f}% of your planned timetable schedule blocks during {period_label} ({time_curr['completed_blocks']}/{tot_sched} blocks).",
                'supporting_metric': f"{adh_rate:.0f}% schedule adherence ({time_curr['completed_blocks']}/{tot_sched} completed)",
                'period': period_label,
                'confidence': 'HIGH',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })
        elif adh_rate < 50.0:
            key = f"time_low_adherence_{curr_start}_{curr_end}"
            insights.append({
                'key': key,
                'title': 'Timetable Schedule Divergence',
                'category': 'TIME',
                'category_badge': 'badge-warning',
                'description': f"Only {adh_rate:.0f}% of scheduled blocks were completed as planned during {period_label}. Unscheduled interruptions or overly tight blocks may be causing schedule slippage.",
                'supporting_metric': f"{adh_rate:.0f}% adherence ({time_curr['completed_blocks']}/{tot_sched} completed, {time_curr['skipped_blocks'] + time_curr['missed_blocks']} missed/skipped)",
                'period': period_label,
                'confidence': 'HIGH',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })

    # 5. Personal Well-being Insights
    wb_curr = get_wellbeing_metrics(user, curr_start, curr_end)
    for corr in wb_curr['correlations']:
        if corr['has_min_data'] and corr['r'] is not None and abs(corr['r']) >= 0.40:
            key = f"wb_corr_{corr['pair_id']}"
            insights.append({
                'key': key,
                'title': f"Well-being Pattern: {corr['title']}",
                'category': 'WELLBEING',
                'category_badge': 'badge-accent',
                'description': corr['interpretation'],
                'supporting_metric': f"Pearson r = {corr['r']:+.2f} across {corr['n']} paired observations",
                'period': f"All-time records ({corr['n']} days)",
                'confidence': 'HIGH',
                'generated_date': today,
                'is_dismissed': key in dismissed_keys,
            })
            break  # Show highest correlation only to prevent clutter

    # Rule 5.2: Stress / Energy Alert
    if wb_curr['avg_stress'] >= 7.0 and wb_curr['avg_energy'] <= 4.5:
        key = f"wb_recovery_alert_{curr_start}_{curr_end}"
        insights.append({
            'key': key,
            'title': 'Rest & Recovery Advisory',
            'category': 'WELLBEING',
            'category_badge': 'badge-danger',
            'description': f"Recorded average stress level is elevated ({wb_curr['avg_stress']:.1f}/10) with energy averaging {wb_curr['avg_energy']:.1f}/10 during {period_label}. Prioritize sleep and active rest.",
            'supporting_metric': f"Average stress: {wb_curr['avg_stress']:.1f}/10, average energy: {wb_curr['avg_energy']:.1f}/10",
            'period': period_label,
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })

    # 6. Finance Insights
    fin_curr = get_finance_metrics(user, curr_start, curr_end)
    top_exp = fin_curr['top_expense']
    if top_exp and top_exp['percentage'] >= 40.0 and fin_curr['total_expenses'] > Decimal('0.00'):
        key = f"fin_top_expense_{curr_start}_{curr_end}"
        insights.append({
            'key': key,
            'title': f"Top Spending Driver: {top_exp['category']}",
            'category': 'FINANCE',
            'category_badge': 'badge-accent',
            'description': f"'{top_exp['category']}' accounted for {top_exp['percentage']:.0f}% (₹{top_exp['amount']:,.2f}) of your total recorded expenses during {period_label}.",
            'supporting_metric': f"₹{top_exp['amount']:,.2f} ({top_exp['percentage']:.0f}% of total expenses)",
            'period': period_label,
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })

    if fin_curr['total_income'] > Decimal('0.00') and fin_curr['net_balance'] > Decimal('0.00') and fin_curr['savings_rate'] >= 20.0:
        key = f"fin_positive_savings_{curr_start}_{curr_end}"
        insights.append({
            'key': key,
            'title': 'Positive Cash Flow & Savings Rate',
            'category': 'FINANCE',
            'category_badge': 'badge-success',
            'description': f"You achieved a positive net balance of ₹{fin_curr['net_balance']:,.2f} during {period_label}, achieving a {fin_curr['savings_rate']:.1f}% savings rate.",
            'supporting_metric': f"Net savings: ₹{fin_curr['net_balance']:,.2f} ({fin_curr['savings_rate']:.1f}% savings rate)",
            'period': period_label,
            'confidence': 'HIGH',
            'generated_date': today,
            'is_dismissed': key in dismissed_keys,
        })

    return insights
