from django.contrib import admin
from .models import Goal, GoalTask, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'priority', 'status', 'target_date', 'created_at')
    list_filter = ('status', 'priority', 'user')
    search_fields = ('title', 'description', 'user__username')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'priority', 'status', 'target_date', 'created_at')
    list_filter = ('status', 'priority', 'user')
    search_fields = ('title', 'description', 'user__username')


@admin.register(GoalTask)
class GoalTaskAdmin(admin.ModelAdmin):
    list_display = ('goal', 'task', 'created_at')
    search_fields = ('goal__title', 'task__title')
