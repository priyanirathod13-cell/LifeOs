import re
from django.db.models import Q
from django.utils.html import escape

from apps.finance.models import Transaction
from apps.personal.models import Decision, JournalEntry, Mistake
from apps.planning.models import Goal, Project
from apps.productivity.models import Activity, Habit, Task
from apps.study.models import Subject, Topic


class GlobalSearchService:
    """
    Unified search engine across all LifeOS modules with strict user data isolation.
    """

    @classmethod
    def search(cls, user, query, limit_per_entity=10):
        if not user or not user.is_authenticated or not query:
            return {
                'query': query or '',
                'total_count': 0,
                'results_by_type': {},
                'all_results': []
            }

        q = query.strip()
        if len(q) < 2:
            return {
                'query': q,
                'total_count': 0,
                'results_by_type': {},
                'all_results': []
            }

        results = []

        def make_snippet(text, search_query, max_len=150):
            if not text:
                return ''
            text_str = str(text)
            idx = text_str.lower().find(search_query.lower())
            if idx == -1:
                return text_str[:max_len] + ('...' if len(text_str) > max_len else '')
            start = max(0, idx - 40)
            end = min(len(text_str), idx + len(search_query) + 80)
            prefix = '...' if start > 0 else ''
            suffix = '...' if end < len(text_str) else ''
            return f"{prefix}{text_str[start:end]}{suffix}"

        # 1. Tasks
        tasks = Task.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).select_related('category')[:limit_per_entity]

        for item in tasks:
            results.append({
                'entity_type': 'Task',
                'badge_class': 'badge-primary',
                'title': item.title,
                'snippet': make_snippet(item.description or item.title, q),
                'meta': f"{item.status} | Priority: {item.priority} | Due: {item.due_date or 'No date'}",
                'url': f'/tasks/{item.id}/',
                'icon': 'check-square',
            })

        # 2. Habits
        habits = Habit.objects.filter(
            user=user
        ).filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )[:limit_per_entity]

        for item in habits:
            results.append({
                'entity_type': 'Habit',
                'badge_class': 'badge-success',
                'title': item.name,
                'snippet': make_snippet(item.description or item.name, q),
                'meta': f"Frequency: {item.frequency} | Target: {item.target_count or 1}",
                'url': f'/habits/{item.id}/edit/',
                'icon': 'repeat',
            })

        # 3. Goals
        goals = Goal.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )[:limit_per_entity]

        for item in goals:
            results.append({
                'entity_type': 'Goal',
                'badge_class': 'badge-info',
                'title': item.title,
                'snippet': make_snippet(item.description or item.title, q),
                'meta': f"Status: {item.status} | Priority: {item.priority} | Target: {item.target_date or 'No date'}",
                'url': f'/goals/{item.id}/',
                'icon': 'target',
            })

        # 4. Projects
        projects = Project.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )[:limit_per_entity]

        for item in projects:
            results.append({
                'entity_type': 'Project',
                'badge_class': 'badge-accent',
                'title': item.title,
                'snippet': make_snippet(item.description or item.title, q),
                'meta': f"{item.status} | Priority: {item.priority}",
                'url': f'/projects/{item.id}/',
                'icon': 'folder',
            })

        # 5. Study Subjects
        subjects = Subject.objects.filter(
            user=user
        ).filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q)
        )[:limit_per_entity]

        for item in subjects:
            results.append({
                'entity_type': 'Subject',
                'badge_class': 'badge-warning',
                'title': f"{item.code} - {item.name}" if item.code else item.name,
                'snippet': make_snippet(item.description or item.name, q),
                'meta': f"Status: {item.status} | Type: {item.subject_type}",
                'url': f'/study/subjects/{item.id}/',
                'icon': 'book',
            })

        # 6. Study Topics
        topics = Topic.objects.filter(
            subject__user=user
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).select_related('subject')[:limit_per_entity]

        for item in topics:
            results.append({
                'entity_type': 'Topic',
                'badge_class': 'badge-warning',
                'title': item.title,
                'snippet': make_snippet(item.description or item.title, q),
                'meta': f"Subject: {item.subject.name} | Status: {item.status}",
                'url': f'/study/topics/{item.id}/edit/',
                'icon': 'bookmark',
            })

        # 7. Journal Entries
        journals = JournalEntry.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=q) | Q(content__icontains=q)
        )[:limit_per_entity]

        for item in journals:
            results.append({
                'entity_type': 'Journal',
                'badge_class': 'badge-secondary',
                'title': item.title or f"Reflection on {item.entry_date}",
                'snippet': make_snippet(item.content, q),
                'meta': f"Date: {item.entry_date} | Tag: {item.mood_tag or 'Reflection'}",
                'url': f'/journal/{item.id}/edit/',
                'icon': 'file-text',
            })

        # 8. Decisions
        decisions = Decision.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(reason_for_choosing__icontains=q)
        )[:limit_per_entity]

        for item in decisions:
            results.append({
                'entity_type': 'Decision',
                'badge_class': 'badge-accent',
                'title': item.title,
                'snippet': make_snippet(item.description or item.reason_for_choosing or item.title, q),
                'meta': f"Date: {item.decision_date} | Status: {item.status}",
                'url': f'/personal/decisions/{item.id}/edit/',
                'icon': 'compass',
            })

        # 9. Mistakes & Learnings
        mistakes = Mistake.objects.filter(
            user=user
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(lesson_learned__icontains=q)
        )[:limit_per_entity]

        for item in mistakes:
            results.append({
                'entity_type': 'Mistake',
                'badge_class': 'badge-danger',
                'title': item.title,
                'snippet': make_snippet(item.lesson_learned or item.description or item.title, q),
                'meta': f"Impact: {item.impact_level} | Status: {item.status}",
                'url': f'/personal/mistakes/{item.id}/edit/',
                'icon': 'alert-triangle',
            })

        # 10. Activities
        activities = Activity.objects.filter(
            user=user
        ).filter(
            Q(activity_name__icontains=q) | Q(description__icontains=q)
        )[:limit_per_entity]

        for item in activities:
            results.append({
                'entity_type': 'Activity',
                'badge_class': 'badge-primary',
                'title': item.activity_name,
                'snippet': make_snippet(item.description or item.activity_name, q),
                'meta': f"Duration: {item.duration_minutes or 0}m | Start: {item.start_time.strftime('%Y-%m-%d %H:%M')}",
                'url': f'/activities/{item.id}/edit/',
                'icon': 'clock',
            })

        # Group results by entity_type
        by_type = {}
        for r in results:
            t = r['entity_type']
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(r)

        return {
            'query': q,
            'total_count': len(results),
            'results_by_type': by_type,
            'all_results': results,
        }
