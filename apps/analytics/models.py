from django.conf import settings
from django.db import models


class DismissedInsight(models.Model):
    """
    Stores user-dismissed behavioral insights to prevent resurfacing
    insights the user has acknowledged or dismissed for a given period or rule.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dismissed_insights'
    )
    insight_key = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Deterministic identifier for rule, entity, and temporal window"
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_dismissedinsight'
        verbose_name = 'Dismissed Insight'
        verbose_name_plural = 'Dismissed Insights'
        unique_together = ('user', 'insight_key')
        ordering = ['-dismissed_at']

    def __str__(self):
        return f"{self.user.username} - {self.insight_key}"
