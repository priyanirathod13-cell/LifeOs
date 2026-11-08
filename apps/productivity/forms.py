from django import forms
from django.utils import timezone
from .models import Activity, Category, CategoryType, Habit, HabitFrequency, HabitLog, Priority, Task, TaskStatus


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
