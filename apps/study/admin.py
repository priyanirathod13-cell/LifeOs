from django.contrib import admin
from .models import Exam, Revision, StudyPlan, StudySession, Subject, Topic


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user', 'subject_type', 'status', 'start_date', 'target_date', 'created_at')
    list_filter = ('status', 'subject_type', 'user')
    search_fields = ('name', 'code', 'user__username')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'chapter', 'status', 'priority', 'estimated_minutes', 'order')
    list_filter = ('status', 'priority', 'subject')
    search_fields = ('title', 'description', 'chapter')


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('session_date', 'user', 'subject', 'topic', 'duration_minutes', 'session_type', 'focus_rating')
    list_filter = ('session_date', 'session_type', 'subject', 'user')
    search_fields = ('notes', 'user__username')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('exam_name', 'user', 'subject', 'exam_date', 'exam_type', 'status', 'score_achieved', 'max_score')
    list_filter = ('status', 'exam_type', 'exam_date', 'subject', 'user')
    search_fields = ('exam_name', 'description', 'user__username')


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('planned_date', 'user', 'subject', 'topic', 'estimated_minutes', 'priority', 'status')
    list_filter = ('status', 'priority', 'planned_date', 'subject', 'user')
    search_fields = ('notes', 'subject__name', 'topic__title')


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('revision_date', 'user', 'subject', 'topic', 'revision_number', 'status', 'completed_at')
    list_filter = ('status', 'revision_date', 'subject', 'user')
    search_fields = ('notes', 'subject__name', 'topic__title')
