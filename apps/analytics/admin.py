from django.contrib import admin
from .models import DismissedInsight


@admin.register(DismissedInsight)
class DismissedInsightAdmin(admin.ModelAdmin):
    list_display = ('user', 'insight_key', 'dismissed_at')
    list_filter = ('dismissed_at',)
    search_fields = ('user__username', 'insight_key')
    ordering = ('-dismissed_at',)
