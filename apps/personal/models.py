from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class DecisionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    EVALUATING = 'EVALUATING', 'Evaluating Options'
    DECIDED = 'DECIDED', 'Decided'
    REVIEWED = 'REVIEWED', 'Reviewed'


class MistakeImpact(models.TextChoices):
    MINOR = 'MINOR', 'Minor'
    MODERATE = 'MODERATE', 'Moderate'
    SEVERE = 'SEVERE', 'Severe'


class MistakeStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    RESOLVED = 'RESOLVED', 'Resolved'
    RECURRING = 'RECURRING', 'Recurring'


class JournalEntry(models.Model):
    """
    Introspective diary and daily reflection log for behavioral insights.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_entries'
    )
    entry_date = models.DateField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    mood_tag = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        ordering = ['-entry_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'entry_date']),
        ]

    def __str__(self):
        return f"{self.entry_date} - {self.title}"


class Decision(models.Model):
    """
    Decision tracking entity for evaluating choices, rationale, and long-term consequences.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='decisions'
    )
    category = models.ForeignKey(
        'productivity.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='decisions'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    decision_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.DRAFT
    )
    chosen_option = models.ForeignKey(
        'DecisionOption',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='chosen_for_decisions'
    )
    reason_for_choosing = models.TextField(
        blank=True,
        default='',
        help_text='Rationale and motivation for selecting chosen option'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Decision'
        verbose_name_plural = 'Decisions'
        ordering = ['-decision_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'decision_date']),
            models.Index(fields=['user', 'status']),
        ]

    def clean(self):
        super().clean()
        if self.category and self.user_id and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})
        if self.chosen_option and self.chosen_option.decision_id != self.id and self.id:
            raise ValidationError({'chosen_option': 'Chosen option must belong to this specific decision.'})

    def __str__(self):
        return self.title


class DecisionOption(models.Model):
    """
    Candidate pathway considered as part of a formal decision analysis.
    """
    decision = models.ForeignKey(
        Decision,
        on_delete=models.CASCADE,
        related_name='options'
    )
    option_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pros = models.TextField(blank=True)
    cons = models.TextField(blank=True)
    expected_outcome = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Decision Option'
        verbose_name_plural = 'Decision Options'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.decision.title}: {self.option_name}"


class DecisionOutcome(models.Model):
    """
    Post-mortem evaluation measuring actual real-world outcomes against expectations.
    """
    decision = models.ForeignKey(
        Decision,
        on_delete=models.CASCADE,
        related_name='outcomes'
    )
    option = models.ForeignKey(
        DecisionOption,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='outcomes'
    )
    actual_outcome = models.TextField()
    outcome_score = models.PositiveSmallIntegerField(
        help_text='Rating from 1 (disastrous) to 10 (ideal success)'
    )
    lessons_learned = models.TextField(blank=True, default='')
    reflection_notes = models.TextField(
        blank=True,
        default='',
        help_text='Retrospective evaluation notes and thoughts'
    )
    outcome_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Decision Outcome'
        verbose_name_plural = 'Decision Outcomes'
        ordering = ['-outcome_date']
        constraints = [
            models.CheckConstraint(
                check=Q(outcome_score__gte=1) & Q(outcome_score__lte=10),
                name='outcome_score_between_1_and_10'
            )
        ]

    def clean(self):
        super().clean()
        if self.option and self.decision_id and self.option.decision_id != self.decision_id:
            raise ValidationError({'option': 'Evaluated option must belong to the exact same decision.'})
        if self.outcome_score is not None and not (1 <= self.outcome_score <= 10):
            raise ValidationError({'outcome_score': 'Outcome score must be between 1 and 10.'})

    def __str__(self):
        return f"Outcome for {self.decision.title} ({self.outcome_date})"


class Mistake(models.Model):
    """
    Learning log cataloging mistakes, root causes, and explicit corrective actions.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mistakes'
    )
    category = models.ForeignKey(
        'productivity.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mistakes'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    mistake_date = models.DateField()
    impact_level = models.CharField(
        max_length=20,
        choices=MistakeImpact.choices,
        default=MistakeImpact.MODERATE
    )
    status = models.CharField(
        max_length=20,
        choices=MistakeStatus.choices,
        default=MistakeStatus.OPEN
    )
    cause_or_reason = models.TextField(
        blank=True,
        default='',
        help_text='Root causes, cognitive triggers, or contributing circumstances'
    )
    lesson_learned = models.TextField()
    corrective_action = models.TextField(blank=True, default='')
    follow_up_notes = models.TextField(
        blank=True,
        default='',
        help_text='Post-mitigation observations, checks, or status updates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mistake'
        verbose_name_plural = 'Mistakes'
        ordering = ['-mistake_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'mistake_date']),
        ]

    def clean(self):
        super().clean()
        if self.category and self.user_id and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})

    def __str__(self):
        return self.title


class DailyMetric(models.Model):
    """
    Quantitative biometric and psychometric indicators (mood, energy, stress, sleep).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_metrics'
    )
    metric_date = models.DateField()
    mood_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Rating from 1 to 10'
    )
    energy_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Rating from 1 to 10'
    )
    stress_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Rating from 1 to 10'
    )
    sleep_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Hours of sleep (0.00 to 24.00)'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Daily Metric'
        verbose_name_plural = 'Daily Metrics'
        ordering = ['-metric_date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'metric_date'],
                name='unique_user_daily_metric'
            ),
            models.CheckConstraint(
                check=Q(mood_score__isnull=True) | (Q(mood_score__gte=1) & Q(mood_score__lte=10)),
                name='mood_score_between_1_and_10'
            ),
            models.CheckConstraint(
                check=Q(energy_score__isnull=True) | (Q(energy_score__gte=1) & Q(energy_score__lte=10)),
                name='energy_score_between_1_and_10'
            ),
            models.CheckConstraint(
                check=Q(stress_score__isnull=True) | (Q(stress_score__gte=1) & Q(stress_score__lte=10)),
                name='stress_score_between_1_and_10'
            ),
            models.CheckConstraint(
                check=Q(sleep_hours__isnull=True) | (Q(sleep_hours__gte=0) & Q(sleep_hours__lte=24)),
                name='sleep_hours_between_0_and_24'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'metric_date']),
        ]

    def clean(self):
        super().clean()
        if self.mood_score is not None and not (1 <= self.mood_score <= 10):
            raise ValidationError({'mood_score': 'Mood score must be between 1 and 10.'})
        if self.energy_score is not None and not (1 <= self.energy_score <= 10):
            raise ValidationError({'energy_score': 'Energy score must be between 1 and 10.'})
        if self.stress_score is not None and not (1 <= self.stress_score <= 10):
            raise ValidationError({'stress_score': 'Stress score must be between 1 and 10.'})
        if self.sleep_hours is not None and not (0 <= self.sleep_hours <= 24):
            raise ValidationError({'sleep_hours': 'Sleep hours must be between 0.00 and 24.00.'})

    def __str__(self):
        return f"{self.user.username or self.user.email} - {self.metric_date}"


class SleepRecord(models.Model):
    """
    Dedicated sleep session log tracking sleep start, wake time, duration, and quality.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sleep_records'
    )
    sleep_date = models.DateField(
        help_text='Primary date for the sleep session (typically wake date)'
    )
    sleep_start = models.DateTimeField(
        help_text='Exact timestamp when user went to sleep'
    )
    wake_time = models.DateTimeField(
        help_text='Exact timestamp when user woke up'
    )
    duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Calculated sleep duration in hours'
    )
    quality_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Sleep quality rating from 1 (Very Poor) to 5 (Excellent)'
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sleep Record'
        verbose_name_plural = 'Sleep Records'
        ordering = ['-sleep_date', '-wake_time']
        indexes = [
            models.Index(fields=['user', 'sleep_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(duration_hours__gt=Decimal('0.00')) & Q(duration_hours__lte=Decimal('24.00')),
                name='sleep_duration_between_0_and_24'
            ),
            models.CheckConstraint(
                check=Q(quality_rating__isnull=True) | (Q(quality_rating__gte=1) & Q(quality_rating__lte=5)),
                name='sleep_quality_between_1_and_5'
            ),
        ]

    def clean(self):
        super().clean()
        if self.sleep_start and self.wake_time:
            if self.wake_time <= self.sleep_start:
                raise ValidationError({'wake_time': 'Wake-up time must be strictly after sleep start time.'})
            diff = self.wake_time - self.sleep_start
            hours = Decimal(str(round(diff.total_seconds() / 3600, 2)))
            if hours > Decimal('24.00'):
                raise ValidationError({'wake_time': 'Sleep duration cannot exceed 24 hours.'})
            self.duration_hours = hours
        if self.quality_rating is not None and not (1 <= self.quality_rating <= 5):
            raise ValidationError({'quality_rating': 'Sleep quality must be between 1 and 5.'})

    def save(self, *args, **kwargs):
        if self.sleep_start and self.wake_time:
            diff = self.wake_time - self.sleep_start
            self.duration_hours = Decimal(str(round(diff.total_seconds() / 3600, 2)))
        super().save(*args, **kwargs)
        # Synchronize with DailyMetric for this date
        DailyMetric.objects.update_or_create(
            user=self.user,
            metric_date=self.sleep_date,
            defaults={'sleep_hours': self.duration_hours}
        )

    def __str__(self):
        return f"{self.user.username or self.user.email} - {self.sleep_date}: {self.duration_hours}h"

