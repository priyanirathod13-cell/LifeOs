from django import forms
from apps.productivity.models import Category, Priority, Task
from .models import Goal, GoalStatus, GoalTask, Project, ProjectStatus


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'category', 'priority', 'status', 'start_date', 'target_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. LifeOS Core Development, Portfolio Website',
                'required': True,
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Overarching project vision, roadmap, and milestone scopes...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
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

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        target = cleaned_data.get('target_date')

        if start and target and target < start:
            raise forms.ValidationError({'target_date': "Target date cannot precede start date."})
        return cleaned_data


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'description', 'category', 'priority', 'status', 'start_date', 'target_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Master Cloud Engineering, Run Half-Marathon',
                'required': True,
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Strategic outcome, personal why, and success metrics...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
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

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        target = cleaned_data.get('target_date')

        if start and target and target < start:
            raise forms.ValidationError({'target_date': "Target date cannot precede start date."})
        return cleaned_data


class GoalTaskLinkForm(forms.Form):
    """
    Form to associate an existing user task directly with a goal.
    """
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="— Select a Task to Link —"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        goal = kwargs.pop('goal', None)
        super().__init__(*args, **kwargs)
        if user and goal:
            # Exclude tasks already linked to this goal
            linked_task_ids = goal.goal_tasks.values_list('task_id', flat=True)
            self.fields['task'].queryset = Task.objects.filter(
                user=user
            ).exclude(id__in=linked_task_ids).order_by('title')
