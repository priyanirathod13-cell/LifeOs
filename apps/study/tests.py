from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.productivity.models import Priority
from apps.study.models import (
    Exam,
    ExamStatus,
    ExamType,
    Revision,
    RevisionStatus,
    StudyPlan,
    PlanStatus,
    StudySession,
    SessionType,
    Subject,
    SubjectStatus,
    SubjectType,
    Topic,
    TopicStatus,
)

User = get_user_model()


class StudyModelsTestCase(TestCase):
    """Unit tests for Study Management models, constraints, and validation logic."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='user_study_a',
            email='study_a@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_study_b',
            email='study_b@example.com',
            password='Password123!'
        )

        self.subject_a = Subject.objects.create(
            user=self.user_a,
            name='Algorithms & Data Structures',
            code='CS201',
            color='#6366f1',
            subject_type=SubjectType.COLLEGE,
            status=SubjectStatus.ACTIVE,
            start_date=date.today() - timedelta(days=30),
            target_date=date.today() + timedelta(days=60),
        )

        self.subject_b = Subject.objects.create(
            user=self.user_b,
            name='Algorithms & Data Structures',  # Same name allowed for different user
            code='CS201',
            color='#10b981',
            subject_type=SubjectType.COLLEGE,
            status=SubjectStatus.ACTIVE,
        )

    def test_subject_uniqueness_and_properties(self):
        """Subjects are scoped to user; duplicate name for same user is rejected."""
        self.assertEqual(str(self.subject_a), 'Algorithms & Data Structures (CS201)')
        self.assertEqual(self.subject_a.total_topics_count, 0)
        self.assertEqual(self.subject_a.completed_topics_count, 0)
        self.assertEqual(self.subject_a.completion_percentage, 0)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Subject.objects.create(
                    user=self.user_a,
                    name='Algorithms & Data Structures',
                    code='CS201-DUPLICATE'
                )

    def test_topic_progress_and_completion_percentage(self):
        """Topic additions and completions correctly compute subject completion percentage."""
        t1 = Topic.objects.create(
            subject=self.subject_a,
            title='Dynamic Programming',
            chapter='Chapter 4',
            status=TopicStatus.COMPLETED,
            completion_date=date.today(),
            estimated_minutes=120,
        )
        t2 = Topic.objects.create(
            subject=self.subject_a,
            title='Graph Traversals',
            chapter='Chapter 3',
            status=TopicStatus.MASTERED,
            estimated_minutes=90,
        )
        t3 = Topic.objects.create(
            subject=self.subject_a,
            title='Greedy Algorithms',
            chapter='Chapter 5',
            status=TopicStatus.IN_PROGRESS,
            estimated_minutes=60,
        )
        t4 = Topic.objects.create(
            subject=self.subject_a,
            title='Bit Manipulation',
            chapter='Chapter 1',
            status=TopicStatus.NOT_STARTED,
            estimated_minutes=45,
        )

        self.assertEqual(self.subject_a.total_topics_count, 4)
        self.assertEqual(self.subject_a.completed_topics_count, 2)
        self.assertEqual(self.subject_a.completion_percentage, 50)
        self.assertIn('Dynamic Programming', str(t1))

    def test_study_session_validation_and_coherence(self):
        """StudySession enforces positive duration, topic coherence, and user alignment."""
        topic_a = Topic.objects.create(subject=self.subject_a, title='Divide and Conquer')
        topic_b = Topic.objects.create(subject=self.subject_b, title='Foreign Topic')

        valid_session = StudySession.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_a,
            session_date=date.today(),
            duration_minutes=90,
            session_type=SessionType.THEORY,
            focus_rating=8,
        )
        self.assertEqual(valid_session.is_active, False)
        self.assertIn('90m', str(valid_session))

        # Active timer session with None duration is valid
        active_session = StudySession.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            session_date=date.today(),
            start_datetime=timezone.now(),
            duration_minutes=None,
        )
        self.assertEqual(active_session.is_active, True)

        # Topic mismatch with subject fails clean
        mismatched = StudySession(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_b,
            session_date=date.today(),
            duration_minutes=60,
        )
        with self.assertRaises(ValidationError):
            mismatched.full_clean()

        # Subject owned by other user fails clean
        cross_user = StudySession(
            user=self.user_a,
            subject=self.subject_b,
            session_date=date.today(),
            duration_minutes=45,
        )
        with self.assertRaises(ValidationError):
            cross_user.full_clean()

    def test_study_plan_validation(self):
        """StudyPlan checks subject and topic alignment with user."""
        topic_a = Topic.objects.create(subject=self.subject_a, title='Heaps & Priority Queues')
        topic_b = Topic.objects.create(subject=self.subject_b, title='Unrelated Topic')

        plan = StudyPlan.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_a,
            planned_date=date.today() + timedelta(days=2),
            estimated_minutes=60,
            priority=Priority.HIGH,
            status=PlanStatus.PLANNED,
        )
        self.assertIn('Heaps & Priority Queues', str(plan))

        invalid_plan = StudyPlan(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_b,
            planned_date=date.today(),
            estimated_minutes=30,
        )
        with self.assertRaises(ValidationError):
            invalid_plan.full_clean()

    def test_revision_validation_and_iteration(self):
        """Revision validates topic-subject relationship and iteration numbering."""
        topic_a = Topic.objects.create(subject=self.subject_a, title='Shortest Paths')
        topic_b = Topic.objects.create(subject=self.subject_b, title='Foreign')

        rev = Revision.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_a,
            revision_date=date.today() + timedelta(days=3),
            revision_number=1,
            status=RevisionStatus.PENDING,
        )
        self.assertIn('Rev #1', str(rev))

        invalid_rev = Revision(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_b,
            revision_date=date.today(),
            revision_number=1,
        )
        with self.assertRaises(ValidationError):
            invalid_rev.full_clean()

    def test_exam_score_and_percentage(self):
        """Exam calculates percentage and prevents achieved score exceeding max score."""
        exam = Exam.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            exam_name='Final Assessment',
            exam_date=date.today() + timedelta(days=15),
            exam_type=ExamType.FINAL,
            status=ExamStatus.UPCOMING,
            max_score=Decimal('100.00'),
            score_achieved=Decimal('87.50'),
        )
        self.assertEqual(exam.percentage_score, Decimal('87.50'))

        invalid_exam = Exam(
            user=self.user_a,
            subject=self.subject_a,
            exam_name='Broken Exam',
            exam_date=date.today(),
            max_score=Decimal('50.00'),
            score_achieved=Decimal('60.00'),  # Exceeds max score!
        )
        with self.assertRaises(ValidationError):
            invalid_exam.full_clean()


class StudyViewsTestCase(TestCase):
    """End-to-end view and authorization tests for all 9 Study Management areas."""

    def setUp(self):
        self.client_a = Client(SERVER_NAME='127.0.0.1')
        self.client_b = Client(SERVER_NAME='127.0.0.1')

        self.user_a = User.objects.create_user(
            username='student_alice',
            email='alice@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='student_bob',
            email='bob@example.com',
            password='Password123!'
        )

        self.client_a.force_login(self.user_a)
        self.client_b.force_login(self.user_b)

        # Populate user_a data
        self.subject_a = Subject.objects.create(
            user=self.user_a,
            name='Operating Systems',
            code='CS301',
            color='#6366f1',
            subject_type=SubjectType.COLLEGE,
            status=SubjectStatus.ACTIVE,
            start_date=date.today() - timedelta(days=10),
            target_date=date.today() + timedelta(days=50),
        )
        self.topic_a1 = Topic.objects.create(
            subject=self.subject_a,
            title='Processes and Threads',
            chapter='Chapter 1',
            status=TopicStatus.COMPLETED,
            completion_date=date.today() - timedelta(days=2),
            estimated_minutes=90,
        )
        self.topic_a2 = Topic.objects.create(
            subject=self.subject_a,
            title='Memory Management',
            chapter='Chapter 2',
            status=TopicStatus.IN_PROGRESS,
            estimated_minutes=120,
        )

        # Populate user_b data
        self.subject_b = Subject.objects.create(
            user=self.user_b,
            name='Computer Networks',
            code='CS303',
            color='#10b981',
            subject_type=SubjectType.COLLEGE,
            status=SubjectStatus.ACTIVE,
        )
        self.topic_b = Topic.objects.create(
            subject=self.subject_b,
            title='TCP/IP Protocol Suite',
            chapter='Unit 1',
            status=TopicStatus.IN_PROGRESS,
            estimated_minutes=60,
        )

    # --------------------------------------------------------------------------
    # 1. Study Dashboard
    # --------------------------------------------------------------------------
    def test_study_dashboard_view(self):
        """Dashboard renders 200 OK and only displays logged in user's subjects."""
        response = self.client_a.get(reverse('study:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operating Systems')
        self.assertNotContains(response, 'Computer Networks')

        # Check core:study alias
        alias_resp = self.client_a.get(reverse('core:study'))
        self.assertEqual(alias_resp.status_code, 200)

    # --------------------------------------------------------------------------
    # 2. Subjects CRUD & IDOR Protection
    # --------------------------------------------------------------------------
    def test_subject_list_view(self):
        """Subjects list displays user subjects and supports search and filter."""
        response = self.client_a.get(reverse('study:subject_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operating Systems')
        self.assertNotContains(response, 'Computer Networks')

        # Search filter
        search_resp = self.client_a.get(reverse('study:subject_list'), {'q': 'Operating'})
        self.assertContains(search_resp, 'Operating Systems')

    def test_subject_create_view(self):
        """User can create a new subject."""
        response = self.client_a.post(reverse('study:subject_create'), {
            'name': 'Linear Algebra',
            'code': 'MATH201',
            'color': '#ec4899',
            'subject_type': SubjectType.COLLEGE,
            'status': SubjectStatus.ACTIVE,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subject.objects.filter(user=self.user_a, name='Linear Algebra').exists())

    def test_subject_detail_view_and_cross_user_isolation(self):
        """Subject detail shows chapters, and blocks other users with 404."""
        response = self.client_a.get(reverse('study:subject_detail', args=[self.subject_a.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Processes and Threads')

        # User B trying to access User A's subject gets 404
        cross_resp = self.client_b.get(reverse('study:subject_detail', args=[self.subject_a.pk]))
        self.assertEqual(cross_resp.status_code, 404)

    def test_subject_update_and_delete(self):
        """User can update and delete their own subject."""
        # Update
        up_resp = self.client_a.post(reverse('study:subject_update', args=[self.subject_a.pk]), {
            'name': 'Advanced Operating Systems',
            'code': 'CS301-A',
            'color': '#6366f1',
            'subject_type': SubjectType.COLLEGE,
            'status': SubjectStatus.ACTIVE,
        })
        self.assertEqual(up_resp.status_code, 302)
        self.subject_a.refresh_from_db()
        self.assertEqual(self.subject_a.name, 'Advanced Operating Systems')

        # Delete
        del_resp = self.client_a.post(reverse('study:subject_delete', args=[self.subject_a.pk]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Subject.objects.filter(pk=self.subject_a.pk).exists())

    # --------------------------------------------------------------------------
    # 3. Topics & Chapters CRUD
    # --------------------------------------------------------------------------
    def test_topic_create_and_toggle_complete(self):
        """User can create topic and toggle its completed status."""
        # Create
        c_resp = self.client_a.post(reverse('study:topic_create'), {
            'subject': self.subject_a.pk,
            'title': 'Deadlocks & Concurrency',
            'chapter': 'Chapter 3',
            'priority': Priority.HIGH,
            'estimated_minutes': 75,
            'status': TopicStatus.NOT_STARTED,
        })
        self.assertEqual(c_resp.status_code, 302)
        new_topic = Topic.objects.get(subject=self.subject_a, title='Deadlocks & Concurrency')
        self.assertEqual(new_topic.status, TopicStatus.NOT_STARTED)

        # Toggle Complete
        toggle_resp = self.client_a.post(reverse('study:topic_toggle', args=[new_topic.pk]))
        self.assertEqual(toggle_resp.status_code, 302)
        new_topic.refresh_from_db()
        self.assertEqual(new_topic.status, TopicStatus.COMPLETED)
        self.assertIsNotNone(new_topic.completion_date)

        # Cross-user toggle attempt
        cross_resp = self.client_b.post(reverse('study:topic_toggle', args=[new_topic.pk]))
        self.assertEqual(cross_resp.status_code, 404)

    # --------------------------------------------------------------------------
    # 4. Syllabus Tracker
    # --------------------------------------------------------------------------
    def test_syllabus_tracker_view(self):
        """Syllabus tracker calculates curriculum mastery and detects behind-schedule alerts."""
        response = self.client_a.get(reverse('study:syllabus'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Syllabus Tracker')
        self.assertContains(response, 'Operating Systems')
        self.assertNotContains(response, 'Computer Networks')

    # --------------------------------------------------------------------------
    # 5. Study Planner
    # --------------------------------------------------------------------------
    def test_study_plan_crud_and_status_actions(self):
        """Study plan can be created, updated to COMPLETED/SKIPPED/RESCHEDULED."""
        plan = StudyPlan.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=self.topic_a1,
            planned_date=date.today(),
            estimated_minutes=45,
            priority=Priority.MEDIUM,
            status=PlanStatus.PLANNED,
        )

        list_resp = self.client_a.get(reverse('study:planner'))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, 'Processes and Threads')

        # Status action: Complete
        comp_resp = self.client_a.post(
            reverse('study:planner_status', args=[plan.pk]),
            {'status': 'COMPLETED'}
        )
        self.assertEqual(comp_resp.status_code, 302)
        plan.refresh_from_db()
        self.assertEqual(plan.status, PlanStatus.COMPLETED)

        # Cross-user status update fails with 404
        cross_resp = self.client_b.post(
            reverse('study:planner_status', args=[plan.pk]),
            {'status': 'SKIPPED'}
        )
        self.assertEqual(cross_resp.status_code, 404)

    # --------------------------------------------------------------------------
    # 6. Study Sessions & Stopwatch Timer
    # --------------------------------------------------------------------------
    def test_stopwatch_timer_workflow(self):
        """Timer start, auto-close of dangling active timers, and timer stop."""
        # 1. Start live timer
        start_resp = self.client_a.post(reverse('study:session_start'), {
            'subject': self.subject_a.pk,
            'topic': self.topic_a2.pk,
            'session_type': SessionType.PRACTICE,
        })
        self.assertEqual(start_resp.status_code, 302)

        active = StudySession.objects.filter(user=self.user_a, duration_minutes__isnull=True).first()
        self.assertIsNotNone(active)
        self.assertEqual(active.topic, self.topic_a2)

        # 2. Starting another timer auto-completes the previous dangling timer
        start_2_resp = self.client_a.post(reverse('study:session_start'), {
            'subject': self.subject_a.pk,
            'session_type': SessionType.THEORY,
        })
        self.assertEqual(start_2_resp.status_code, 302)
        active.refresh_from_db()
        self.assertIsNotNone(active.duration_minutes)  # Closed!

        # 3. Stop the second timer
        active_2 = StudySession.objects.filter(user=self.user_a, duration_minutes__isnull=True).first()
        self.assertIsNotNone(active_2)
        stop_resp = self.client_a.post(reverse('study:session_stop', args=[active_2.pk]), {
            'focus_rating': '9',
            'notes': 'Completed memory segmentation problems.',
        })
        self.assertEqual(stop_resp.status_code, 302)
        active_2.refresh_from_db()
        self.assertIsNotNone(active_2.duration_minutes)
        self.assertEqual(active_2.focus_rating, 9)

    def test_manual_study_session_logging_and_validation(self):
        """Manual session creation calculates duration from start/end times."""
        resp = self.client_a.post(reverse('study:session_create'), {
            'subject': self.subject_a.pk,
            'topic': self.topic_a1.pk,
            'session_date': str(date.today()),
            'start_time': '10:00',
            'end_time': '11:30',
            'session_type': SessionType.REVISION,
            'focus_rating': '8',
            'notes': 'Reviewed synchronization primitives.',
        })
        self.assertEqual(resp.status_code, 302)
        created = StudySession.objects.filter(user=self.user_a, session_type=SessionType.REVISION).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.duration_minutes, 90)

    # --------------------------------------------------------------------------
    # 7. Revision Planner
    # --------------------------------------------------------------------------
    def test_revision_planner_workflow(self):
        """User can schedule, toggle completion, and reschedule revisions."""
        rev = Revision.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=self.topic_a1,
            revision_date=date.today(),
            revision_number=1,
            status=RevisionStatus.PENDING,
        )

        rev_resp = self.client_a.get(reverse('study:revisions'))
        self.assertEqual(rev_resp.status_code, 200)
        self.assertContains(rev_resp, 'Processes and Threads')

        # Toggle completion
        toggle_resp = self.client_a.post(reverse('study:revision_toggle', args=[rev.pk]))
        self.assertEqual(toggle_resp.status_code, 302)
        rev.refresh_from_db()
        self.assertEqual(rev.status, RevisionStatus.COMPLETED)
        self.assertIsNotNone(rev.completed_at)

        # Reschedule
        future_date = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        resched_resp = self.client_a.post(
            reverse('study:revision_reschedule', args=[rev.pk]),
            {'revision_date': future_date}
        )
        self.assertEqual(resched_resp.status_code, 302)
        rev.refresh_from_db()
        self.assertEqual(str(rev.revision_date), future_date)
        self.assertEqual(rev.status, RevisionStatus.PENDING)

    # --------------------------------------------------------------------------
    # 8. Exams & Assessments
    # --------------------------------------------------------------------------
    def test_exam_crud_and_scores(self):
        """User can schedule exam, record achieved score, and view countdowns."""
        # Create
        create_resp = self.client_a.post(reverse('study:exam_create'), {
            'subject': self.subject_a.pk,
            'exam_name': 'Midterm 1',
            'exam_date': str(date.today() + timedelta(days=10)),
            'exam_type': ExamType.MIDTERM,
            'status': ExamStatus.UPCOMING,
            'weight_percentage': '25.0',
            'max_score': '100.0',
        })
        self.assertEqual(create_resp.status_code, 302)
        exam = Exam.objects.get(user=self.user_a, exam_name='Midterm 1')

        # Record Score
        update_resp = self.client_a.post(reverse('study:exam_update', args=[exam.pk]), {
            'subject': self.subject_a.pk,
            'exam_name': 'Midterm 1',
            'exam_date': str(exam.exam_date),
            'exam_type': ExamType.MIDTERM,
            'status': ExamStatus.COMPLETED,
            'weight_percentage': '25.0',
            'score_achieved': '94.0',
            'max_score': '100.0',
        })
        self.assertEqual(update_resp.status_code, 302)
        exam.refresh_from_db()
        self.assertEqual(exam.score_achieved, Decimal('94.00'))
        self.assertEqual(exam.percentage_score, Decimal('94.00'))

        # Cross-user exam update attempt fails with 404
        cross_resp = self.client_b.post(reverse('study:exam_update', args=[exam.pk]), {
            'subject': self.subject_b.pk,
            'exam_name': 'Hacked Exam',
            'exam_date': str(exam.exam_date),
            'exam_type': ExamType.MIDTERM,
            'status': ExamStatus.COMPLETED,
        })
        self.assertEqual(cross_resp.status_code, 404)

    # --------------------------------------------------------------------------
    # 9. Study Analytics
    # --------------------------------------------------------------------------
    def test_study_analytics_view(self):
        """Analytics view returns 200 OK and calculates 14-day study rhythm."""
        # Log 120 minutes of study for user_a
        StudySession.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=self.topic_a1,
            session_date=date.today(),
            duration_minutes=120,
            session_type=SessionType.THEORY,
            focus_rating=9,
        )

        response = self.client_a.get(reverse('study:analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '14-Day Study Volume')
        self.assertContains(response, 'Operating Systems')
        self.assertNotContains(response, 'Computer Networks')

        # Check core:study_analytics alias
        alias_resp = self.client_a.get(reverse('core:study_analytics'))
        self.assertEqual(alias_resp.status_code, 200)
