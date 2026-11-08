import csv
import io
import json
import zipfile
from django.http import HttpResponse
from django.utils import timezone

from apps.finance.models import Transaction
from apps.personal.models import DailyMetric, Decision, JournalEntry, Mistake
from apps.planning.models import Goal, Project
from apps.productivity.models import Activity, Habit, HabitLog, Task
from apps.study.models import Exam, Revision, StudyPlan, StudySession, Subject, Topic


class ExportService:
    """
    Exports user data in CSV or JSON format with strict user privacy guarantees.
    Never exports passwords, hash tokens, or other users' records.
    """

    @classmethod
    def get_user_data_dict(cls, user, modules=None):
        """
        Gathers sanitized dictionaries of user records across all selected modules.
        """
        data = {}
        if not modules:
            modules = ['tasks', 'habits', 'activities', 'goals', 'study', 'personal', 'finance']

        # 1. Tasks
        if 'tasks' in modules:
            tasks_qs = Task.objects.filter(user=user).select_related('category', 'project')
            data['tasks'] = [
                {
                    'id': t.id,
                    'title': t.title,
                    'status': t.status,
                    'priority': t.priority,
                    'due_date': str(t.due_date) if t.due_date else None,
                    'estimated_minutes': t.estimated_minutes,
                    'actual_minutes': t.actual_minutes,
                    'category': t.category.name if t.category else None,
                    'project': t.project.title if t.project else None,
                    'description': t.description,
                    'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks_qs
            ]

        # 2. Habits & Logs
        if 'habits' in modules:
            habits_qs = Habit.objects.filter(user=user)
            data['habits'] = [
                {
                    'id': h.id,
                    'name': h.name,
                    'frequency': h.frequency,
                    'target_count': h.target_count,
                    'is_active': h.is_active,
                    'description': h.description,
                    'created_at': h.created_at.isoformat() if h.created_at else None,
                }
                for h in habits_qs
            ]

            logs_qs = HabitLog.objects.filter(user=user).select_related('habit')
            data['habit_logs'] = [
                {
                    'habit': l.habit.name,
                    'log_date': str(l.log_date),
                    'completed': l.completed,
                    'notes': l.notes,
                }
                for l in logs_qs
            ]

        # 3. Activities
        if 'activities' in modules:
            acts_qs = Activity.objects.filter(user=user).select_related('category')
            data['activities'] = [
                {
                    'id': a.id,
                    'activity_name': a.activity_name,
                    'start_time': a.start_time.isoformat() if a.start_time else None,
                    'end_time': a.end_time.isoformat() if a.end_time else None,
                    'duration_minutes': a.duration_minutes,
                    'category': a.category.name if a.category else None,
                    'description': a.description,
                }
                for a in acts_qs
            ]

        # 4. Goals & Projects
        if 'goals' in modules:
            goals_qs = Goal.objects.filter(user=user)
            data['goals'] = [
                {
                    'id': g.id,
                    'title': g.title,
                    'description': g.description,
                    'status': g.status,
                    'priority': g.priority,
                    'target_date': str(g.target_date) if g.target_date else None,
                    'created_at': g.created_at.isoformat() if g.created_at else None,
                }
                for g in goals_qs
            ]

            proj_qs = Project.objects.filter(user=user)
            data['projects'] = [
                {
                    'id': p.id,
                    'title': p.title,
                    'description': p.description,
                    'status': p.status,
                    'priority': p.priority,
                    'start_date': str(p.start_date) if p.start_date else None,
                    'target_end_date': str(p.target_end_date) if p.target_end_date else None,
                }
                for p in proj_qs
            ]

        # 5. Study
        if 'study' in modules:
            subjs_qs = Subject.objects.filter(user=user)
            data['subjects'] = [
                {
                    'id': s.id,
                    'code': s.code,
                    'name': s.name,
                    'subject_type': s.subject_type,
                    'status': s.status,
                    'description': s.description,
                }
                for s in subjs_qs
            ]

            topics_qs = Topic.objects.filter(subject__user=user).select_related('subject')
            data['topics'] = [
                {
                    'id': tp.id,
                    'subject': tp.subject.name,
                    'title': tp.title,
                    'status': tp.status,
                    'estimated_minutes': tp.estimated_minutes,
                    'actual_minutes': tp.actual_minutes,
                }
                for tp in topics_qs
            ]

            sessions_qs = StudySession.objects.filter(user=user).select_related('subject', 'topic')
            data['study_sessions'] = [
                {
                    'id': ss.id,
                    'subject': ss.subject.name if ss.subject else None,
                    'topic': ss.topic.title if ss.topic else None,
                    'session_date': str(ss.session_date),
                    'duration_minutes': ss.duration_minutes,
                    'focus_rating': ss.focus_rating,
                    'notes': ss.notes,
                }
                for ss in sessions_qs
            ]

            plans_qs = StudyPlan.objects.filter(user=user).select_related('subject', 'topic')
            data['study_plans'] = [
                {
                    'id': p.id,
                    'subject': p.subject.name,
                    'topic': p.topic.title if p.topic else None,
                    'planned_date': str(p.planned_date),
                    'status': p.status,
                    'estimated_minutes': p.estimated_minutes,
                }
                for p in plans_qs
            ]

            revisions_qs = Revision.objects.filter(user=user).select_related('subject', 'topic')
            data['revisions'] = [
                {
                    'id': r.id,
                    'subject': r.subject.name,
                    'topic': r.topic.title,
                    'revision_date': str(r.revision_date),
                    'revision_number': r.revision_number,
                    'status': r.status,
                }
                for r in revisions_qs
            ]

            exams_qs = Exam.objects.filter(user=user).select_related('subject')
            data['exams'] = [
                {
                    'id': ex.id,
                    'subject': ex.subject.name,
                    'exam_name': ex.exam_name,
                    'exam_date': str(ex.exam_date),
                    'exam_type': ex.exam_type,
                    'status': ex.status,
                    'score_achieved': float(ex.score_achieved) if ex.score_achieved else None,
                    'max_score': float(ex.max_score) if ex.max_score else None,
                }
                for ex in exams_qs
            ]

        # 6. Personal (DailyMetrics, Journal, Decisions, Mistakes)
        if 'personal' in modules:
            metrics_qs = DailyMetric.objects.filter(user=user)
            data['daily_metrics'] = [
                {
                    'metric_date': str(m.metric_date),
                    'mood_score': m.mood_score,
                    'energy_score': m.energy_score,
                    'stress_score': m.stress_score,
                    'sleep_hours': float(m.sleep_hours) if m.sleep_hours else None,
                    'notes': m.notes,
                }
                for m in metrics_qs
            ]

            journals_qs = JournalEntry.objects.filter(user=user)
            data['journal_entries'] = [
                {
                    'id': j.id,
                    'entry_date': str(j.entry_date),
                    'title': j.title,
                    'content': j.content,
                    'mood_tag': j.mood_tag,
                }
                for j in journals_qs
            ]

            decisions_qs = Decision.objects.filter(user=user)
            data['decisions'] = [
                {
                    'id': d.id,
                    'title': d.title,
                    'decision_date': str(d.decision_date),
                    'description': d.description,
                    'reason_for_choosing': d.reason_for_choosing,
                    'status': d.status,
                }
                for d in decisions_qs
            ]

            mistakes_qs = Mistake.objects.filter(user=user)
            data['mistakes'] = [
                {
                    'id': m.id,
                    'title': m.title,
                    'mistake_date': str(m.mistake_date),
                    'description': m.description,
                    'cause_or_reason': m.cause_or_reason,
                    'lesson_learned': m.lesson_learned,
                    'impact_level': m.impact_level,
                    'status': m.status,
                }
                for m in mistakes_qs
            ]

        # 7. Finance
        if 'finance' in modules:
            tx_qs = Transaction.objects.filter(user=user).select_related('category')
            data['transactions'] = [
                {
                    'id': t.id,
                    'date': str(t.transaction_date),
                    'amount': float(t.amount),
                    'type': t.transaction_type,
                    'category': t.category.name if t.category else None,
                    'description': t.description,
                }
                for t in tx_qs
            ]

        return data

    @classmethod
    def export_json_response(cls, user, modules=None):
        data = cls.get_user_data_dict(user, modules=modules)
        payload = {
            'application': 'LifeOS',
            'version': '1.0',
            'export_timestamp': timezone.now().isoformat(),
            'user': {
                'username': user.username,
                'email': user.email,
                'timezone_pref': getattr(user, 'timezone_pref', 'Asia/Kolkata'),
            },
            'data': data,
        }
        json_str = json.dumps(payload, indent=2, ensure_ascii=False)
        filename = f"lifeos_export_{user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response = HttpResponse(json_str, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @classmethod
    def export_csv_response(cls, user, module='tasks'):
        """
        Exports a single module as a direct CSV download or all modules as a zip archive of CSVs.
        """
        data = cls.get_user_data_dict(user, modules=[module] if module != 'all' else None)

        # If a single table is requested and exists
        if module != 'all' and module in data:
            records = data[module]
            output = io.StringIO()
            if records:
                fieldnames = list(records[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for row in records:
                    writer.writerow(row)
            else:
                output.write("No records found for this module.")

            filename = f"lifeos_{module}_{user.username}_{timezone.now().strftime('%Y%m%d')}.csv"
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        # Otherwise, bundle all exported modules into a ZIP of CSVs
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for table_name, rows in data.items():
                table_output = io.StringIO()
                if rows:
                    fieldnames = list(rows[0].keys())
                    writer = csv.DictWriter(table_output, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)
                else:
                    table_output.write("No records\n")
                zip_file.writestr(f"{table_name}.csv", table_output.getvalue())

        filename = f"lifeos_all_csv_{user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
