from django.contrib import admin
from .models import (
    Activity,
    Category,
    Habit,
    HabitLog,
    Routine,
    ScheduleBlock,
    Task,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category_type', 'color', 'created_at')
    list_filter = ('category_type', 'user')
    search_fields = ('name', 'user__username', 'user__email')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'priority', 'status', 'due_date', 'estimated_minutes', 'actual_minutes')
    list_filter = ('status', 'priority', 'user')
    search_fields = ('title', 'description', 'user__username')


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'frequency', 'target_count', 'is_active')
    list_filter = ('frequency', 'is_active', 'user')
    search_fields = ('name', 'user__username')


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('habit', 'user', 'log_date', 'completed')
    list_filter = ('completed', 'log_date', 'user')
    search_fields = ('habit__name', 'notes')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('activity_name', 'user', 'category', 'start_time', 'end_time', 'duration_display')
    list_filter = ('user',)
    search_fields = ('activity_name', 'description')

    def duration_display(self, obj):
        dur = obj.duration_minutes
        return f"{dur} mins" if dur is not None else "Active"
    duration_display.short_description = "Duration"


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'start_time', 'end_time', 'days_of_week', 'is_active')
    list_filter = ('is_active', 'user')
    search_fields = ('title',)


@admin.register(ScheduleBlock)
class ScheduleBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'block_date', 'start_time', 'end_time', 'block_type', 'status')
    list_filter = ('block_type', 'status', 'block_date', 'user')
    search_fields = ('title', 'description')
