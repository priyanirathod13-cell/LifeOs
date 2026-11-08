from datetime import date, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.productivity.models import Priority


class SubjectType(models.TextChoices):
    COLLEGE = 'COLLEGE', 'College / University Course'
    SELF_LEARNING = 'SELF_LEARNING', 'Self-Directed Learning'
    CERTIFICATION = 'CERTIFICATION', 'Certification Course'
    COMPETITIVE_EXAM = 'COMPETITIVE_EXAM', 'Competitive Exam Prep'
    OTHER = 'OTHER', 'Other'


class SubjectStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    COMPLETED = 'COMPLETED', 'Completed'
    ARCHIVED = 'ARCHIVED', 'Archived'


class TopicStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    MASTERED = 'MASTERED', 'Mastered'
    NEEDS_REVISION = 'NEEDS_REVISION', 'Needs Revision'


class SessionType(models.TextChoices):
    THEORY = 'THEORY', 'Theory & Reading'
    PRACTICE = 'PRACTICE', 'Practice & Problem Solving'
    REVISION = 'REVISION', 'Revision'
    EXAM_PREP = 'EXAM_PREP', 'Exam Preparation'
    ASSIGNMENT = 'ASSIGNMENT', 'Assignment / Project'
    OTHER = 'OTHER', 'Other'


class ExamType(models.TextChoices):
    QUIZ = 'QUIZ', 'Quiz / Unit Test'
    MIDTERM = 'MIDTERM', 'Mid-Term Exam'
    FINAL = 'FINAL', 'Final / Semester Exam'
    COMPETITIVE = 'COMPETITIVE', 'Competitive Exam'
    PRACTICE = 'PRACTICE', 'Mock / Practice Exam'
    ASSIGNMENT = 'ASSIGNMENT', 'Assessment'


class ExamStatus(models.TextChoices):
    UPCOMING = 'UPCOMING', 'Upcoming'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PlanStatus(models.TextChoices):
    PLANNED = 'PLANNED', 'Planned'
    COMPLETED = 'COMPLETED', 'Completed'
    SKIPPED = 'SKIPPED', 'Skipped'
    RESCHEDULED = 'RESCHEDULED', 'Rescheduled'


class RevisionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    SKIPPED = 'SKIPPED', 'Skipped'


# ==============================================================================
# 1. SUBJECT MODEL
# ==============================================================================

class Subject(models.Model):
    """
    Academic course, syllabus module, or self-directed learning subject.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True, help_text='Course code (e.g. CS101, MATH202)')
    description = models.TextField(blank=True)
    subject_type = models.CharField(
        max_length=30,
        choices=SubjectType.choices,
        default=SubjectType.COLLEGE
    )
    status = models.CharField(
        max_length=20,
        choices=SubjectStatus.choices,
        default=SubjectStatus.ACTIVE
    )
    color = models.CharField(max_length=20, default='#818CF8')
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_subject_name'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'name']),
        ]

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValidationError({'target_date': 'Target completion date cannot precede start date.'})

    @property
    def total_topics_count(self):
        return self.topics.count()

    @property
    def completed_topics_count(self):
        return self.topics.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()

    @property
    def completion_percentage(self):
        total = self.total_topics_count
        if total == 0:
            return 0
        return round((self.completed_topics_count / total) * 100)

    @property
    def total_study_minutes(self):
        return self.sessions.aggregate(total=models.Sum('duration_minutes'))['total'] or 0

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


# ==============================================================================
# 2. TOPIC MODEL
# ==============================================================================

class Topic(models.Model):
    """
    Discrete concept, chapter, or syllabus unit under a Subject.
    """
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    chapter = models.CharField(max_length=150, blank=True, help_text='Chapter or unit grouping')
    status = models.CharField(
        max_length=20,
        choices=TopicStatus.choices,
        default=TopicStatus.NOT_STARTED
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['subject', 'status']),
            models.Index(fields=['subject', 'order']),
        ]

    @property
    def is_completed(self):
        return self.status in [TopicStatus.COMPLETED, TopicStatus.MASTERED]

    @property
    def actual_minutes(self):
        return self.sessions.aggregate(total=models.Sum('duration_minutes'))['total'] or 0

    def clean(self):
        super().clean()
        if self.title:
            self.title = self.title.strip()

    def __str__(self):
        return f"{self.subject.name} - {self.title}"


# ==============================================================================
# 3. STUDY SESSION MODEL
# ==============================================================================

class StudySession(models.Model):
    """
    Focused study or revision block logged towards a subject and topic.
    Supports both live active timers and completed historical logs.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='study_sessions'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    topic = models.ForeignKey(
        Topic,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sessions'
    )
    session_date = models.DateField(default=timezone.now)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    start_datetime = models.DateTimeField(null=True, blank=True, help_text='Precise start timestamp for live timer')
    end_datetime = models.DateTimeField(null=True, blank=True, help_text='Precise end timestamp for live timer')
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Total active study duration in minutes'
    )
    session_type = models.CharField(
        max_length=30,
        choices=SessionType.choices,
        default=SessionType.THEORY
    )
    focus_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Focus quality rating from 1 to 10'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Study Session'
        verbose_name_plural = 'Study Sessions'
        ordering = ['-session_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'session_date']),
            models.Index(fields=['user', 'end_datetime']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(duration_minutes__gt=0) | Q(duration_minutes__isnull=True),
                name='study_session_duration_positive_or_null'
            )
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.subject and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'Cannot log study session for a subject belonging to another user.'})
        if self.subject_id and self.topic and self.topic.subject_id != self.subject_id:
            raise ValidationError({'topic': 'Selected topic must belong to the selected subject.'})
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValidationError({'duration_minutes': 'Study session duration must be greater than zero.'})
        if self.focus_rating is not None and (self.focus_rating < 1 or self.focus_rating > 10):
            raise ValidationError({'focus_rating': 'Focus rating must be between 1 and 10.'})
        if self.start_datetime and self.end_datetime and self.end_datetime < self.start_datetime:
            raise ValidationError({'end_datetime': 'End time cannot precede start time.'})

    @property
    def is_active(self):
        return self.end_datetime is None and self.start_datetime is not None

    def __str__(self):
        mins = f"{self.duration_minutes}m" if self.duration_minutes else "Active"
        return f"{self.subject.name} ({mins} on {self.session_date})"


# ==============================================================================
# 4. EXAM MODEL
# ==============================================================================

class Exam(models.Model):
    """
    Scheduled milestone exam, quiz, mid-term, or test.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exams'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exams'
    )
    exam_name = models.CharField(max_length=150)
    exam_date = models.DateField()
    exam_type = models.CharField(
        max_length=30,
        choices=ExamType.choices,
        default=ExamType.QUIZ
    )
    status = models.CharField(
        max_length=20,
        choices=ExamStatus.choices,
        default=ExamStatus.UPCOMING
    )
    weight_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Percentage contribution to overall grade'
    )
    score_achieved = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Exam'
        verbose_name_plural = 'Exams'
        ordering = ['exam_date']
        indexes = [
            models.Index(fields=['user', 'exam_date']),
            models.Index(fields=['user', 'status']),
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.subject and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'Cannot link exam to a subject belonging to another user.'})
        if self.score_achieved is not None and self.max_score is not None and self.score_achieved > self.max_score:
            raise ValidationError({'score_achieved': 'Obtained score cannot exceed maximum score.'})

    @property
    def percentage_score(self):
        if self.score_achieved is not None and self.max_score and self.max_score > 0:
            return round((float(self.score_achieved) / float(self.max_score)) * 100, 1)
        return None

    def __str__(self):
        return f"{self.subject.name}: {self.exam_name} ({self.exam_date})"


# ==============================================================================
# 5. STUDY PLAN MODEL
# ==============================================================================

class StudyPlan(models.Model):
    """
    Scheduled upcoming study commitment linking subject, topic, date, and duration.
    Keeps planned commitments distinct from actual recorded sessions.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='study_plans'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='study_plans'
    )
    topic = models.ForeignKey(
        Topic,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='study_plans'
    )
    planned_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(default=60)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=PlanStatus.choices,
        default=PlanStatus.PLANNED
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Study Plan'
        verbose_name_plural = 'Study Plans'
        ordering = ['planned_date', 'preferred_time', '-priority']
        indexes = [
            models.Index(fields=['user', 'planned_date']),
            models.Index(fields=['user', 'status']),
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.subject and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'Cannot plan for a subject belonging to another user.'})
        if self.subject_id and self.topic and self.topic.subject_id != self.subject_id:
            raise ValidationError({'topic': 'Selected topic must belong to the selected subject.'})

    def __str__(self):
        topic_info = f" - {self.topic.title}" if self.topic_id else ""
        return f"Plan: {self.subject.name}{topic_info} on {self.planned_date} ({self.get_status_display()})"


# ==============================================================================
# 6. REVISION MODEL
# ==============================================================================

class Revision(models.Model):
    """
    Scheduled spaced revision check for a topic previously studied.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    revision_date = models.DateField()
    revision_number = models.PositiveIntegerField(
        default=1,
        help_text='Revision iteration (1st revision, 2nd revision, etc.)'
    )
    status = models.CharField(
        max_length=20,
        choices=RevisionStatus.choices,
        default=RevisionStatus.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Revision'
        verbose_name_plural = 'Revisions'
        ordering = ['revision_date', 'revision_number']
        indexes = [
            models.Index(fields=['user', 'revision_date']),
            models.Index(fields=['user', 'status']),
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.subject and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'Cannot schedule revision for another user\'s subject.'})
        if self.subject_id and self.topic and self.topic.subject_id != self.subject_id:
            raise ValidationError({'topic': 'Selected topic must belong to the selected subject.'})

    def __str__(self):
        return f"Rev #{self.revision_number}: {self.topic.title} ({self.revision_date})"
