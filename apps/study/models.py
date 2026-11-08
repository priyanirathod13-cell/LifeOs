from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class SubjectType(models.TextChoices):
    COLLEGE = 'COLLEGE', 'College / University Course'
    SELF_LEARNING = 'SELF_LEARNING', 'Self-Directed Learning'
    CERTIFICATION = 'CERTIFICATION', 'Certification Course'
    COMPETITIVE_EXAM = 'COMPETITIVE_EXAM', 'Competitive Exam Prep'


class TopicStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    MASTERED = 'MASTERED', 'Mastered'
    NEEDS_REVISION = 'NEEDS_REVISION', 'Needs Revision'


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
    color = models.CharField(max_length=20, default='#818CF8')
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
            models.Index(fields=['user', 'name']),
        ]

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


class Topic(models.Model):
    """
    Discrete concept, chapter, or syllabus syllabus unit under a Subject.
    """
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=TopicStatus.choices,
        default=TopicStatus.NOT_STARTED
    )
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.subject.name} - {self.title}"


class StudySession(models.Model):
    """
    Focused study or revision block logged towards a subject and topic.
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
    session_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(
        help_text='Total active study duration in minutes'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Study Session'
        verbose_name_plural = 'Study Sessions'
        ordering = ['-session_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'session_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(duration_minutes__gt=0),
                name='study_session_duration_positive'
            )
        ]

    def clean(self):
        super().clean()
        if self.subject and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'Cannot log study session for a subject belonging to another user.'})
        if self.topic and self.topic.subject_id != self.subject_id:
            raise ValidationError({'topic': 'Selected topic must belong to the selected subject.'})
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValidationError({'duration_minutes': 'Study session duration must be greater than zero.'})

    def __str__(self):
        return f"{self.subject.name} ({self.duration_minutes}m on {self.session_date})"


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
    weight_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Percentage contribution to overall grade'
    )
    score_achieved = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Exam'
        verbose_name_plural = 'Exams'
        ordering = ['exam_date']
        indexes = [
            models.Index(fields=['user', 'exam_date']),
        ]

    def clean(self):
        super().clean()
        if self.subject and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'Cannot link exam to a subject belonging to another user.'})

    def __str__(self):
        return f"{self.subject.name}: {self.exam_name} ({self.exam_date})"
