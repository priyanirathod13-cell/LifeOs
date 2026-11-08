from django import forms
from django.utils import timezone
from .models import (
    Activity, AvailabilityWindow, Category, CategoryType, DayOfWeek,
    Habit, HabitFrequency, HabitLog, Priority, Routine, RoutineType,
    ScheduleBlock, SchedulingPreference, Task, TaskStatus
)


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 'project',
            'priority', 'status', 'due_date', 'estimated_minutes', 'actual_minutes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What needs to be accomplished?',
                'autofocus': True,
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add details, context, or acceptance criteria...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'estimated_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 45',
                'min': '0',
                'step': '5'
            }),
            'actual_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 50',
                'min': '0',
                'step': '5'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            if not getattr(self.instance, 'user_id', None):
                self.instance.user = self.user
            self.fields['category'].queryset = Category.objects.filter(user=self.user).order_by('name')
            # Import Project inside __init__ to prevent cyclic import
            from apps.planning.models import Project
            self.fields['project'].queryset = Project.objects.filter(user=self.user).order_by('title')

        self.fields['category'].empty_label = "— No Category —"
        self.fields['project'].empty_label = "— No Project —"

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if cat and self.user and cat.user_id != self.user.id:
            raise forms.ValidationError("Invalid category selected.")
        return cat

    def clean_project(self):
        proj = self.cleaned_data.get('project')
        if proj and self.user and proj.user_id != self.user.id:
            raise forms.ValidationError("Invalid project selected.")
        return proj


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'category_type', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Engineering, Fitness, Deep Work',
                'required': True,
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description of what this category encapsulates...'
            }),
            'category_type': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'style': 'height: 42px; padding: 4px; cursor: pointer;'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. code, heart, book, dollar-sign'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Category name cannot be blank.")

        # Check duplicate category name for this user
        qs = Category.objects.filter(user=self.user, name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("You already have a category with this name.")
        return name


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['name', 'description', 'category', 'frequency', 'target_count', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Morning Hydration, 30min Reading',
                'required': True,
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Habit cue, routine, or behavioral loop rationale...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'target_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['category'].queryset = Category.objects.filter(user=self.user).order_by('name')
        self.fields['category'].empty_label = "— No Category —"

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if cat and self.user and cat.user_id != self.user.id:
            raise forms.ValidationError("Invalid category selected.")
        return cat


class HabitLogForm(forms.ModelForm):
    class Meta:
        model = HabitLog
        fields = ['log_date', 'completed', 'notes']
        widgets = {
            'log_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'completed': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional notes regarding execution or roadblocks...'
            }),
        }


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['activity_name', 'description', 'category', 'start_time', 'end_time']
        widgets = {
            'activity_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Deep Work Architecture, HIIT Session',
                'required': True,
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notes about focus level, context, or output...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['category'].queryset = Category.objects.filter(user=self.user).order_by('name')
        self.fields['category'].empty_label = "— No Category —"

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')

        if start and end and end < start:
            raise forms.ValidationError({'end_time': "End time cannot precede start time."})
        return cleaned_data


# ==============================================================================
# 5. ROUTINE FORM
# ==============================================================================

class RoutineForm(forms.ModelForm):
    days_list = forms.MultipleChoiceField(
        choices=[
            ('MON', 'Mon'),
            ('TUE', 'Tue'),
            ('WED', 'Wed'),
            ('THU', 'Thu'),
            ('FRI', 'Fri'),
            ('SAT', 'Sat'),
            ('SUN', 'Sun'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-pill'}),
        required=True,
        help_text='Select the weekdays this recurring routine applies to.'
    )

    class Meta:
        model = Routine
        fields = [
            'title', 'routine_type', 'start_time', 'end_time',
            'start_date', 'end_date', 'is_active', 'description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Morning Workout, College Lectures, Office Hours',
                'required': True,
                'autofocus': True
            }),
            'routine_type': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Location, prep details, recurrence notes...'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.days_of_week:
            self.fields['days_list'].initial = [
                d.strip().upper() for d in self.instance.days_of_week.split(',') if d.strip()
            ]
        elif not self.is_bound:
            self.fields['days_list'].initial = ['MON', 'TUE', 'WED', 'THU', 'FRI']

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        s_date = cleaned_data.get('start_date')
        e_date = cleaned_data.get('end_date')
        days = cleaned_data.get('days_list')

        if start and end and end <= start:
            raise forms.ValidationError({'end_time': "Start time must be strictly before end time for single-day routines."})

        if s_date and e_date and e_date < s_date:
            raise forms.ValidationError({'end_date': "End date cannot be prior to start date."})

        if days:
            cleaned_data['days_of_week'] = ','.join(days)

        # Check overlapping routines for user
        if self.user and start and end and days:
            from apps.productivity.services.conflicts import detect_routine_overlap
            temp_routine = Routine(
                user=self.user,
                title=cleaned_data.get('title', ''),
                start_time=start,
                end_time=end,
                days_of_week=','.join(days),
                start_date=s_date,
                end_date=e_date,
                is_active=cleaned_data.get('is_active', True)
            )
            overlap = detect_routine_overlap(self.user, temp_routine, exclude_pk=self.instance.pk if self.instance else None)
            if overlap:
                raise forms.ValidationError(
                    f"This routine conflicts with existing routine '{overlap.title}' "
                    f"({overlap.start_time.strftime('%H:%M')}-{overlap.end_time.strftime('%H:%M')})."
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        days = self.cleaned_data.get('days_list')
        if days:
            instance.days_of_week = ','.join(days)
        if self.user and not instance.user_id:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


# ==============================================================================
# 6. AVAILABILITY WINDOW FORM
# ==============================================================================

class AvailabilityWindowForm(forms.ModelForm):
    class Meta:
        model = AvailabilityWindow
        fields = ['day_of_week', 'start_time', 'end_time', 'is_active']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        day = cleaned_data.get('day_of_week')
        is_active = cleaned_data.get('is_active', True)

        if start and end and end <= start:
            raise forms.ValidationError({'end_time': "End time must be after start time."})

        if self.user and start and end and day and is_active:
            overlap_qs = AvailabilityWindow.objects.filter(
                user=self.user,
                day_of_week=day,
                is_active=True,
                start_time__lt=end,
                end_time__gt=start
            )
            if self.instance and self.instance.pk:
                overlap_qs = overlap_qs.exclude(pk=self.instance.pk)
            if overlap_qs.exists():
                other = overlap_qs.first()
                raise forms.ValidationError(
                    f"Overlaps with another availability window on {other.get_day_of_week_display()} "
                    f"({other.start_time.strftime('%H:%M')}-{other.end_time.strftime('%H:%M')})."
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not instance.user_id:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


# ==============================================================================
# 7. SCHEDULE BLOCK FORM
# ==============================================================================

class ScheduleBlockForm(forms.ModelForm):
    class Meta:
        model = ScheduleBlock
        fields = [
            'title', 'description', 'block_date', 'start_time', 'end_time',
            'block_type', 'status', 'priority', 'is_fixed', 'related_task'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Block title (e.g. Design Architecture, Math Assignment)',
                'required': True,
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Deliverables, notes, venue or sub-tasks...'
            }),
            'block_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'block_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'is_fixed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'related_task': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['related_task'].queryset = Task.objects.filter(user=self.user).order_by('title')
        self.fields['related_task'].empty_label = "— No Related Task —"

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')

        if start and end and end <= start:
            raise forms.ValidationError({'end_time': "End time must be after start time."})

        task = cleaned_data.get('related_task')
        if task and self.user and task.user_id != self.user.id:
            raise forms.ValidationError({'related_task': "Related task must belong to you."})

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not instance.user_id:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


# ==============================================================================
# 8. SCHEDULING PREFERENCE FORM
# ==============================================================================

class SchedulingPreferenceForm(forms.ModelForm):
    class Meta:
        model = SchedulingPreference
        fields = [
            'day_start_time', 'day_end_time', 'default_break_minutes',
            'max_continuous_work_minutes', 'buffer_minutes',
            'auto_insert_breaks', 'max_daily_work_minutes'
        ]
        widgets = {
            'day_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'day_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'default_break_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '5', 'max': '60', 'step': '5'}),
            'max_continuous_work_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '30', 'max': '240', 'step': '15'}),
            'buffer_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '30', 'step': '5'}),
            'auto_insert_breaks': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_daily_work_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '60', 'max': '960', 'step': '30'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('day_start_time')
        end = cleaned_data.get('day_end_time')

        if start and end and end <= start:
            raise forms.ValidationError({'day_end_time': "Day end time must be after day start time."})
        return cleaned_data


# ==============================================================================
# 9. RESCHEDULE BLOCK FORM
# ==============================================================================

class RescheduleBlockForm(forms.Form):
    new_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    new_start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'placeholder': 'Auto-fit if empty'}),
        required=False,
        help_text='Leave empty to automatically place into the earliest available slot.'
    )

