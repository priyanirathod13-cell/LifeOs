from django.contrib import admin
from .models import (
    DailyMetric,
    Decision,
    DecisionOption,
    DecisionOutcome,
    JournalEntry,
    Mistake,
    SleepRecord,
)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'title', 'user', 'mood_tag', 'created_at')
    list_filter = ('entry_date', 'user')
    search_fields = ('title', 'content', 'user__username')


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'decision_date', 'status', 'chosen_option')
    list_filter = ('status', 'decision_date', 'user')
    search_fields = ('title', 'description', 'user__username')


@admin.register(DecisionOption)
class DecisionOptionAdmin(admin.ModelAdmin):
    list_display = ('decision', 'option_name', 'created_at')
    search_fields = ('option_name', 'description')


@admin.register(DecisionOutcome)
class DecisionOutcomeAdmin(admin.ModelAdmin):
    list_display = ('decision', 'option', 'outcome_score', 'outcome_date')
    list_filter = ('outcome_score', 'outcome_date')
    search_fields = ('actual_outcome', 'lessons_learned')


@admin.register(Mistake)
class MistakeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'mistake_date', 'impact_level', 'status')
    list_filter = ('impact_level', 'status', 'mistake_date', 'user')
    search_fields = ('title', 'lesson_learned', 'user__username')


@admin.register(DailyMetric)
class DailyMetricAdmin(admin.ModelAdmin):
    list_display = ('metric_date', 'user', 'mood_score', 'energy_score', 'stress_score', 'sleep_hours')
    list_filter = ('metric_date', 'user')
    search_fields = ('notes', 'user__username')


@admin.register(SleepRecord)
class SleepRecordAdmin(admin.ModelAdmin):
    list_display = ('sleep_date', 'user', 'sleep_start', 'wake_time', 'duration_hours', 'quality_rating')
    list_filter = ('quality_rating', 'sleep_date', 'user')
    search_fields = ('notes', 'user__username')
