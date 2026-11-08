from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.study.models import Exam, StudySession, Subject, SubjectType, Topic, TopicStatus

User = get_user_model()


class StudyModelsTestCase(TestCase):
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
            name='Database Management Systems',
            code='CS302',
            subject_type=SubjectType.COLLEGE
        )
        self.subject_b = Subject.objects.create(
            user=self.user_b,
            name='Database Management Systems',  # Identical name for different user
            code='CS302',
            subject_type=SubjectType.COLLEGE
        )

    def test_subject_uniqueness_and_isolation(self):
        """Subjects are scoped to user; duplicate name for same user is rejected."""
        self.assertIn('CS302', str(self.subject_a))

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Subject.objects.create(
                    user=self.user_a,
                    name='Database Management Systems',
                    code='CS302-DUPLICATE'
                )

    def test_topic_hierarchy(self):
        """Topics belong to a subject and track syllabus status."""
        topic = Topic.objects.create(
            subject=self.subject_a,
            title='B+ Trees and Index Optimization',
            status=TopicStatus.IN_PROGRESS,
            estimated_minutes=120,
            order=1
        )
        self.assertIn('B+ Trees', str(topic))

    def test_study_session_validation_and_topic_coherence(self):
        """Study session enforces positive duration and topic coherence with subject."""
        topic_a = Topic.objects.create(
            subject=self.subject_a,
            title='Relational Algebra'
        )
        topic_b = Topic.objects.create(
            subject=self.subject_b,
            title='Foreign Subject Topic'
        )

        # Valid session
        valid_session = StudySession.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_a,
            session_date=date.today(),
            duration_minutes=45
        )
        self.assertIn('45m', str(valid_session))

        # Mismatched topic from another subject
        mismatched_session = StudySession(
            user=self.user_a,
            subject=self.subject_a,
            topic=topic_b,  # Belongs to subject_b!
            session_date=date.today(),
            duration_minutes=60
        )
        with self.assertRaises(ValidationError):
            mismatched_session.full_clean()

        # Zero duration
        zero_session = StudySession(
            user=self.user_a,
            subject=self.subject_a,
            session_date=date.today(),
            duration_minutes=0
        )
        with self.assertRaises(ValidationError):
            zero_session.full_clean()

        # Cross-user subject
        cross_session = StudySession(
            user=self.user_a,
            subject=self.subject_b,
            session_date=date.today(),
            duration_minutes=60
        )
        with self.assertRaises(ValidationError):
            cross_session.full_clean()

    def test_exam_cross_user_isolation(self):
        """Exams cannot reference subjects belonging to another user."""
        exam = Exam.objects.create(
            user=self.user_a,
            subject=self.subject_a,
            exam_name='Midterm Assessment',
            exam_date=date.today(),
            max_score=Decimal('100.00'),
            score_achieved=Decimal('92.50')
        )
        self.assertIn('Midterm Assessment', str(exam))

        cross_exam = Exam(
            user=self.user_a,
            subject=self.subject_b,
            exam_name='Malicious Exam',
            exam_date=date.today()
        )
        with self.assertRaises(ValidationError):
            cross_exam.full_clean()
