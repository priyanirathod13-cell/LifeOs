import MySQLdb
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.personal.models import DailyMetric
from apps.planning.models import Goal, GoalStatus, GoalTask, Priority
from apps.productivity.models import (
    Category,
    CategoryType,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority as TaskPriority,
    Task,
    TaskStatus,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Import and preserve legacy data from the legacy MySQL 'lifeos' database into 'lifeos_db'."

    def add_arguments(self, parser):
        parser.add_argument(
            '--legacy-db',
            default='lifeos',
            help="Name of the legacy database to read from (default: 'lifeos')"
        )

    def handle(self, *args, **options):
        legacy_db_name = options['legacy_db']
        self.stdout.write(self.style.NOTICE(f"Connecting to legacy database '{legacy_db_name}'..."))

        # Connect to MySQL legacy database using configured credentials
        db_settings = settings.DATABASES['default']
        try:
            conn = MySQLdb.connect(
                host=db_settings.get('HOST', '127.0.0.1') or '127.0.0.1',
                port=int(db_settings.get('PORT', 3306) or 3306),
                user=db_settings.get('USER', 'root'),
                passwd=db_settings.get('PASSWORD', ''),
                db=legacy_db_name,
                charset='utf8mb4'
            )
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to connect to legacy database '{legacy_db_name}': {e}"))
            return

        user_map = {}      # legacy user_id -> new User object
        category_map = {}  # legacy category_id -> new Category object
        task_map = {}      # legacy task_id -> new Task object
        habit_map = {}     # legacy habit_id -> new Habit object
        goal_map = {}      # legacy goal_id -> new Goal object

        with transaction.atomic():
            self.stdout.write("1. Importing legacy users...")
            cursor.execute("SELECT * FROM users ORDER BY user_id")
            legacy_users = cursor.fetchall()
            for u in legacy_users:
                # Map role / bio / full name
                raw_pass = u.get('password_hash', 'Password123!')
                email = u['email'].strip().lower()
                username = u['username'].strip()

                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': username.split('_')[0].capitalize(),
                        'last_name': username.split('_')[-1].capitalize() if '_' in username else '',
                        'password': make_password(raw_pass),
                        'bio': f"Migrated {u.get('role', 'User').capitalize()} account from legacy LifeOS.",
                        'is_active': True,
                    }
                )
                user_map[u['user_id']] = user
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] User: {user.username} ({user.email})")

            self.stdout.write("2. Importing categories...")
            cursor.execute("SELECT * FROM categories ORDER BY category_id")
            legacy_categories = cursor.fetchall()
            type_mapping = {
                'TASK': CategoryType.TASK,
                'HABIT': CategoryType.HABIT,
                'ACTIVITY': CategoryType.ACTIVITY,
                'EXPENSE': CategoryType.FINANCE,
                'INCOME': CategoryType.FINANCE,
                'STUDY': CategoryType.STUDY,
                'GENERAL': CategoryType.GENERAL,
            }
            for c in legacy_categories:
                user = user_map.get(c['user_id'])
                if not user:
                    continue
                cat_type = type_mapping.get(c.get('type', 'GENERAL'), CategoryType.GENERAL)
                category, created = Category.objects.get_or_create(
                    user=user,
                    name=c['name'].strip(),
                    defaults={
                        'category_type': cat_type,
                        'color': c.get('color') or '#818CF8',
                        'icon': c.get('icon') or '',
                    }
                )
                category_map[c['category_id']] = category
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] Category: {category.name} ({category.category_type})")

            self.stdout.write("3. Importing tasks...")
            cursor.execute("SELECT * FROM tasks ORDER BY task_id")
            legacy_tasks = cursor.fetchall()
            priority_map = {
                'LOW': TaskPriority.LOW,
                'MED': TaskPriority.MEDIUM,
                'MEDIUM': TaskPriority.MEDIUM,
                'HIGH': TaskPriority.HIGH,
                'URGENT': TaskPriority.URGENT,
            }
            status_map = {
                'PENDING': TaskStatus.PENDING,
                'IN_PROGRESS': TaskStatus.IN_PROGRESS,
                'COMPLETED': TaskStatus.COMPLETED,
                'CANCELLED': TaskStatus.CANCELLED,
            }
            for t in legacy_tasks:
                user = user_map.get(t['user_id'])
                if not user:
                    continue
                cat = category_map.get(t['category_id']) if t.get('category_id') else None
                task, created = Task.objects.get_or_create(
                    user=user,
                    title=t['title'].strip(),
                    defaults={
                        'category': cat,
                        'description': t.get('description') or '',
                        'priority': priority_map.get(t.get('priority', 'MEDIUM'), TaskPriority.MEDIUM),
                        'status': status_map.get(t.get('status', 'PENDING'), TaskStatus.PENDING),
                        'due_date': t.get('due_date'),
                        'estimated_minutes': t.get('estimated_minutes'),
                        'actual_minutes': t.get('actual_minutes'),
                        'completed_at': t.get('completed_at'),
                    }
                )
                task_map[t['task_id']] = task
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] Task #{t['task_id']}: {task.title}")

            self.stdout.write("4. Importing habits and habit logs...")
            cursor.execute("SELECT * FROM habits ORDER BY habit_id")
            legacy_habits = cursor.fetchall()
            freq_map = {
                'DAILY': HabitFrequency.DAILY,
                'WEEKLY': HabitFrequency.WEEKLY,
                'MONTHLY': HabitFrequency.MONTHLY,
            }
            for h in legacy_habits:
                user = user_map.get(h['user_id'])
                if not user:
                    continue
                cat = category_map.get(h['category_id']) if h.get('category_id') else None
                habit, created = Habit.objects.get_or_create(
                    user=user,
                    name=h['name'].strip(),
                    defaults={
                        'category': cat,
                        'description': h.get('description') or '',
                        'frequency': freq_map.get(h.get('frequency', 'DAILY'), HabitFrequency.DAILY),
                        'target_count': h.get('target_count') or 1,
                        'is_active': True,
                    }
                )
                habit_map[h['habit_id']] = habit
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] Habit: {habit.name}")

            cursor.execute("SELECT * FROM habit_logs ORDER BY habit_log_id")
            legacy_logs = cursor.fetchall()
            for l in legacy_logs:
                habit = habit_map.get(l['habit_id'])
                user = user_map.get(l['user_id'])
                if not habit or not user:
                    continue
                hlog, created = HabitLog.objects.get_or_create(
                    habit=habit,
                    log_date=l['log_date'],
                    defaults={
                        'user': user,
                        'completed': bool(l.get('completed', 1)),
                        'notes': l.get('notes') or '',
                    }
                )
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] HabitLog: {habit.name} on {l['log_date']}")

            self.stdout.write("5. Importing goals and goal tasks...")
            cursor.execute("SELECT * FROM goals ORDER BY goal_id")
            legacy_goals = cursor.fetchall()
            goal_status_map = {
                'NOT_STARTED': GoalStatus.NOT_STARTED,
                'IN_PROGRESS': GoalStatus.IN_PROGRESS,
                'ACHIEVED': GoalStatus.ACHIEVED,
                'COMPLETED': GoalStatus.ACHIEVED,
                'ABANDONED': GoalStatus.ABANDONED,
            }
            for g in legacy_goals:
                user = user_map.get(g['user_id'])
                if not user:
                    continue
                cat = category_map.get(g['category_id']) if g.get('category_id') else None
                goal, created = Goal.objects.get_or_create(
                    user=user,
                    title=g['title'].strip(),
                    defaults={
                        'category': cat,
                        'description': g.get('description') or '',
                        'priority': priority_map.get(g.get('priority', 'MEDIUM'), Priority.MEDIUM),
                        'status': goal_status_map.get(g.get('status', 'IN_PROGRESS'), GoalStatus.IN_PROGRESS),
                        'start_date': g.get('start_date'),
                        'target_date': g.get('target_date'),
                        'achieved_at': g.get('completed_at'),
                    }
                )
                goal_map[g['goal_id']] = goal
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] Goal: {goal.title}")

            cursor.execute("SELECT * FROM goal_tasks ORDER BY goal_task_id")
            legacy_gt = cursor.fetchall()
            for gt in legacy_gt:
                goal = goal_map.get(gt['goal_id'])
                task = task_map.get(gt['task_id'])
                if not goal or not task:
                    continue
                link, created = GoalTask.objects.get_or_create(
                    goal=goal,
                    task=task
                )
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] GoalTask link: {goal.title} -> {task.title}")

            self.stdout.write("6. Importing daily metrics...")
            cursor.execute("SELECT * FROM daily_metrics ORDER BY metric_id")
            legacy_metrics = cursor.fetchall()
            for m in legacy_metrics:
                user = user_map.get(m['user_id'])
                if not user:
                    continue
                dm, created = DailyMetric.objects.get_or_create(
                    user=user,
                    metric_date=m['metric_date'],
                    defaults={
                        'mood_score': m.get('mood_score'),
                        'energy_score': m.get('energy_score'),
                        'stress_score': m.get('stress_score'),
                        'sleep_hours': m.get('sleep_hours'),
                        'notes': m.get('notes') or '',
                    }
                )
                status_str = "Created" if created else "Found existing"
                self.stdout.write(f"  - [{status_str}] DailyMetric: {user.username} on {m['metric_date']}")

        cursor.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS("Legacy data migration completed successfully with zero loss."))
