from django.contrib import admin
from .models import Exam, StudySession, Subject, Topic


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user', 'subject_type', 'created_at')
    list_filter = ('subject_type', 'user')
    search_fields = ('name', 'code', 'user__username')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'status', 'estimated_minutes', 'order')
    list_filter = ('status', 'subject')
    search_fields = ('title', 'description')


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('session_date', 'user', 'subject', 'topic', 'duration_minutes')
    list_filter = ('session_date', 'subject', 'user')
    search_fields = ('notes', 'user__username')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('exam_name', 'user', 'subject', 'exam_date', 'score_achieved', 'max_score', 'weight_percentage')
    list_filter = ('exam_date', 'subject', 'user')
    search_fields = ('exam_name', 'description', 'user__username')
