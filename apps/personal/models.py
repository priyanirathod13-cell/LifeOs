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
        if self.category and self.category.user_id != self.user_id:
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
    lessons_learned = models.TextField(blank=True)
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
        if self.option and self.option.decision_id != self.decision_id:
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
    lesson_learned = models.TextField()
    corrective_action = models.TextField(blank=True)
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
        if self.category and self.category.user_id != self.user_id:
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
