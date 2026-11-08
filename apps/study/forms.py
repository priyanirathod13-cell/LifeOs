from datetime import date, datetime, timedelta
from django import forms
from django.utils import timezone

from .models import (
    Exam,
    ExamStatus,
    ExamType,
    PlanStatus,
    Priority,
    Revision,
    RevisionStatus,
    SessionType,
    StudyPlan,
    StudySession,
    Subject,
    SubjectStatus,
    SubjectType,
    Topic,
    TopicStatus,
)


# ==============================================================================
# 1. SUBJECT FORM
# ==============================================================================

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'description', 'subject_type', 'status', 'color', 'start_date', 'target_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Distributed Systems, Organic Chemistry, Linear Algebra',
                'required': True,
                'autofocus': True
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. CS-401, CHEM-202 (optional)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Course syllabus overview, examination dates, or self-learning goals...'
            }),
            'subject_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'style': 'height: 42px; width: 80px; padding: 2px;'
            }),
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
        if self.user and not getattr(self.instance, 'user_id', None):
            self.instance.user = self.user

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Subject name cannot be blank.")

        qs = Subject.objects.filter(user=self.user, name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("You already have a subject with this name.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        target = cleaned_data.get('target_date')

        if start and target and target < start:
            raise forms.ValidationError({'target_date': "Target completion date cannot precede start date."})
        return cleaned_data


# ==============================================================================
# 2. TOPIC FORM
# ==============================================================================

class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = [
            'subject', 'title', 'chapter', 'description',
            'priority', 'status', 'estimated_minutes',
            'completion_date', 'order', 'notes'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Chapter 3: Raft Consensus, Eigenvalues & Eigenvectors',
                'required': True,
                'autofocus': True
            }),
            'chapter': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Unit 1: Foundations, Chapter 4 (optional)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Sub-topics, theorems, formula highlights, or lecture references...'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'estimated_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '5',
                'placeholder': 'e.g. 90'
            }),
            'completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'e.g. 1'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Key takeaways, exam tips, or unresolved questions...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['order'].required = False
        if self.user:
            self.fields['subject'].queryset = Subject.objects.filter(user=self.user).order_by('name')

    def clean_order(self):
        val = self.cleaned_data.get('order')
        return val if val is not None else 0

    def clean_subject(self):
        subj = self.cleaned_data.get('subject')
        if subj and self.user and subj.user_id != self.user.id:
            raise forms.ValidationError("Invalid subject selected.")
        return subj

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        completion_date = cleaned_data.get('completion_date')

        # Auto-stamp completion date if marked completed without explicit date
        if status in [TopicStatus.COMPLETED, TopicStatus.MASTERED] and not completion_date:
            cleaned_data['completion_date'] = timezone.now().date()
        elif status == TopicStatus.NOT_STARTED:
            cleaned_data['completion_date'] = None

        return cleaned_data


# ==============================================================================
# 3. STUDY SESSION FORM (MANUAL RECORDING)
# ==============================================================================

class StudySessionForm(forms.ModelForm):
    class Meta:
        model = StudySession
        fields = [
            'subject', 'topic', 'session_date', 'start_time', 'end_time',
            'duration_minutes', 'session_type', 'focus_rating', 'notes'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'session_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'e.g. 60 (calculated automatically if start/end provided)'
            }),
            'session_type': forms.Select(attrs={'class': 'form-select'}),
            'focus_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10',
                'placeholder': 'Score from 1 (distracted) to 10 (deep flow)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Topics covered, problems solved, mental hurdles, or takeaways...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            if not getattr(self.instance, 'user_id', None):
                self.instance.user = self.user
            self.fields['subject'].queryset = Subject.objects.filter(user=self.user).order_by('name')
            self.fields['topic'].queryset = Topic.objects.filter(subject__user=self.user).order_by('subject__name', 'title')

        self.fields['topic'].empty_label = "— No Specific Topic (General Subject Study) —"

    def clean_subject(self):
        subj = self.cleaned_data.get('subject')
        if subj and self.user and subj.user_id != self.user.id:
            raise forms.ValidationError("Invalid subject selected.")
        return subj

    def clean(self):
        cleaned_data = super().clean()
        subj = cleaned_data.get('subject')
        top = cleaned_data.get('topic')
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        duration = cleaned_data.get('duration_minutes')

        if top and subj and top.subject_id != subj.id:
            raise forms.ValidationError({'topic': "Selected topic does not belong to the selected subject."})

        # Calculate duration if start and end are provided
        if start and end:
            s_dt = datetime.combine(date.today(), start)
            e_dt = datetime.combine(date.today(), end)
            if e_dt < s_dt:
                raise forms.ValidationError({'end_time': "End time cannot precede start time."})
            diff_mins = int((e_dt - s_dt).total_seconds() / 60)
            if not duration or duration <= 0:
                cleaned_data['duration_minutes'] = diff_mins

        if not cleaned_data.get('duration_minutes') or cleaned_data.get('duration_minutes') <= 0:
            raise forms.ValidationError({'duration_minutes': "Please enter a valid study duration in minutes."})

        return cleaned_data


# ==============================================================================
# 4. STUDY PLAN FORM
# ==============================================================================

class StudyPlanForm(forms.ModelForm):
    class Meta:
        model = StudyPlan
        fields = [
            'subject', 'topic', 'planned_date', 'preferred_time',
            'estimated_minutes', 'priority', 'status', 'notes'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'planned_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'preferred_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'estimated_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'step': '5',
                'value': '60'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Preparation scope, specific exercise sets, or syllabus checkpoints...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            if not getattr(self.instance, 'user_id', None):
                self.instance.user = self.user
            self.fields['subject'].queryset = Subject.objects.filter(user=self.user).order_by('name')
            self.fields['topic'].queryset = Topic.objects.filter(subject__user=self.user).order_by('subject__name', 'title')

        self.fields['topic'].empty_label = "— General Subject Study —"

    def clean_subject(self):
        subj = self.cleaned_data.get('subject')
        if subj and self.user and subj.user_id != self.user.id:
            raise forms.ValidationError("Invalid subject selected.")
        return subj

    def clean(self):
        cleaned_data = super().clean()
        subj = cleaned_data.get('subject')
        top = cleaned_data.get('topic')

        if top and subj and top.subject_id != subj.id:
            raise forms.ValidationError({'topic': "Selected topic does not belong to the selected subject."})
        return cleaned_data


# ==============================================================================
# 5. REVISION FORM
# ==============================================================================

class RevisionForm(forms.ModelForm):
    class Meta:
        model = Revision
        fields = ['subject', 'topic', 'revision_date', 'revision_number', 'status', 'notes']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'revision_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'revision_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Formulas to re-derive, active recall flashcards, or past mistakes to review...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            if not getattr(self.instance, 'user_id', None):
                self.instance.user = self.user
            self.fields['subject'].queryset = Subject.objects.filter(user=self.user).order_by('name')
            self.fields['topic'].queryset = Topic.objects.filter(subject__user=self.user).order_by('subject__name', 'title')

    def clean_subject(self):
        subj = self.cleaned_data.get('subject')
        if subj and self.user and subj.user_id != self.user.id:
            raise forms.ValidationError("Invalid subject selected.")
        return subj

    def clean(self):
        cleaned_data = super().clean()
        subj = cleaned_data.get('subject')
        top = cleaned_data.get('topic')

        if top and subj and top.subject_id != subj.id:
            raise forms.ValidationError({'topic': "Selected topic must belong to the selected subject."})
        return cleaned_data


# ==============================================================================
# 6. EXAM FORM
# ==============================================================================

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'subject', 'exam_name', 'exam_date', 'exam_type', 'status',
            'weight_percentage', 'score_achieved', 'max_score', 'description'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'exam_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Mid-Term Exam, JEE Mock 3, AWS Solutions Architect',
                'required': True,
                'autofocus': True
            }),
            'exam_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'exam_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'weight_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'max': '100',
                'placeholder': 'e.g. 30 (%)'
            }),
            'score_achieved': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'placeholder': 'e.g. 85.0'
            }),
            'max_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'placeholder': 'e.g. 100.0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Exam venue, syllabus coverage, grading rubric, or revision goals...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            if not getattr(self.instance, 'user_id', None):
                self.instance.user = self.user
            self.fields['subject'].queryset = Subject.objects.filter(user=self.user).order_by('name')

    def clean_subject(self):
        subj = self.cleaned_data.get('subject')
        if subj and self.user and subj.user_id != self.user.id:
            raise forms.ValidationError("Invalid subject selected.")
        return subj

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score_achieved')
        max_s = cleaned_data.get('max_score')

        if score is not None and max_s is not None and score > max_s:
            raise forms.ValidationError({'score_achieved': "Obtained score cannot exceed maximum score."})
        return cleaned_data
