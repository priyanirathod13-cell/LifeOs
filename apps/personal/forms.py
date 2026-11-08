from decimal import Decimal
from django import forms
from django.utils import timezone
from apps.productivity.models import Category
from .models import (
    DailyMetric,
    Decision,
    DecisionOption,
    DecisionOutcome,
    DecisionStatus,
    JournalEntry,
    Mistake,
    MistakeImpact,
    MistakeStatus,
    SleepRecord,
)


MOOD_CHOICES = [
    (1, '1 — Very Bad (Struggling)'),
    (2, '2 — Bad (Down / Low)'),
    (3, '3 — Neutral (Balanced)'),
    (4, '4 — Good (Positive / Upbeat)'),
    (5, '5 — Excellent (Thriving / Peak)'),
]

ENERGY_CHOICES = [
    (1, '1 — Very Low (Exhausted / Depleted)'),
    (2, '2 — Low (Fatigued / Sluggish)'),
    (3, '3 — Moderate (Normal / Functional)'),
    (4, '4 — High (Alert / Productive)'),
    (5, '5 — Very High (Energized / Vibrant)'),
]

STRESS_CHOICES = [
    (1, '1 — Very Low (Completely Relaxed)'),
    (2, '2 — Low (Calm / Manageable)'),
    (3, '3 — Moderate (Mild Pressure)'),
    (4, '4 — High (Stressed / Strained)'),
    (5, '5 — Very High (Overwhelmed / Acute)'),
]

SLEEP_QUALITY_CHOICES = [
    (1, '1 — Very Poor (Restless / Broken)'),
    (2, '2 — Poor (Tossed / Disturbed)'),
    (3, '3 — Fair (Average)'),
    (4, '4 — Good (Restful)'),
    (5, '5 — Excellent (Deep & Rejuvenating)'),
]


# ==============================================================================
# 1. JOURNAL ENTRY FORM
# ==============================================================================

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'entry_date', 'mood_tag', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Title of your reflection or entry...',
                'autofocus': True,
                'required': True,
            }),
            'entry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'mood_tag': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Grateful, Focused, Overwhelmed, Peaceful',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Write your thoughts, daily experiences, reflections, and insights...',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'entry_date' not in self.initial:
            self.initial['entry_date'] = timezone.localdate()


# ==============================================================================
# 2. DAILY CHECK-IN FORM
# ==============================================================================

class DailyCheckinForm(forms.ModelForm):
    mood_score = forms.TypedChoiceField(
        choices=MOOD_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        help_text='Overall subjective psychological state today'
    )
    energy_score = forms.TypedChoiceField(
        choices=ENERGY_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        help_text='Physical & cognitive vitality level'
    )
    stress_score = forms.TypedChoiceField(
        choices=STRESS_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        help_text='Perceived friction, tension, or cognitive load'
    )

    class Meta:
        model = DailyMetric
        fields = ['metric_date', 'mood_score', 'energy_score', 'stress_score', 'sleep_hours', 'notes']
        widgets = {
            'metric_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'sleep_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.25',
                'min': '0',
                'max': '24',
                'placeholder': 'e.g. 7.5',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any notable context, diet, workouts, or somatic reflections...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'metric_date' not in self.initial:
            self.initial['metric_date'] = timezone.localdate()


# ==============================================================================
# 3. SLEEP RECORD FORM
# ==============================================================================

class SleepRecordForm(forms.ModelForm):
    quality_rating = forms.TypedChoiceField(
        choices=[('', '— Optional Rating —')] + SLEEP_QUALITY_CHOICES,
        coerce=lambda x: int(x) if x else None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
    )

    class Meta:
        model = SleepRecord
        fields = ['sleep_date', 'sleep_start', 'wake_time', 'quality_rating', 'notes']
        widgets = {
            'sleep_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'sleep_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True,
            }),
            'wake_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True,
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Sleep environment, interruptions, caffeine timing, dreams...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'sleep_date' not in self.initial:
            today = timezone.localdate()
            self.initial['sleep_date'] = today
            # Default sensible times for last night's sleep
            now = timezone.now()
            # Default sleep start 23:00 yesterday, wake 07:00 today
            yesterday = today - timezone.timedelta(days=1)
            self.initial['sleep_start'] = f"{yesterday.strftime('%Y-%m-%d')}T23:00"
            self.initial['wake_time'] = f"{today.strftime('%Y-%m-%d')}T07:00"

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('sleep_start')
        wake = cleaned_data.get('wake_time')

        if start and wake:
            if wake <= start:
                raise forms.ValidationError({'wake_time': 'Wake-up time must be strictly after sleep start time.'})
            diff = wake - start
            hours = Decimal(str(round(diff.total_seconds() / 3600, 2)))
            if hours > Decimal('24.00'):
                raise forms.ValidationError({'wake_time': 'Sleep duration cannot exceed 24 hours.'})
            if hours < Decimal('0.10'):
                raise forms.ValidationError({'wake_time': 'Sleep duration must be at least 6 minutes.'})
        return cleaned_data


# ==============================================================================
# 4. DECISION FORM
# ==============================================================================

class DecisionForm(forms.ModelForm):
    class Meta:
        model = Decision
        fields = ['title', 'category', 'decision_date', 'status', 'description', 'reason_for_choosing']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Transition from Full-time Job to Freelancing',
                'autofocus': True,
                'required': True,
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'decision_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Context, problem statement, stakes, and constraints...',
            }),
            'reason_for_choosing': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Why was this decision or direction chosen? Core rationale...',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if self.user:
            if not self.instance.user_id:
                self.instance.user = self.user
            self.fields['category'].queryset = Category.objects.filter(user=self.user).order_by('name')
        if not self.instance.pk and 'decision_date' not in self.initial:
            self.initial['decision_date'] = timezone.localdate()

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if cat and self.user and cat.user_id != self.user.id:
            raise forms.ValidationError('Cannot assign a category belonging to another user.')
        return cat


# ==============================================================================
# 5. DECISION OPTION FORM
# ==============================================================================

class DecisionOptionForm(forms.ModelForm):
    class Meta:
        model = DecisionOption
        fields = ['option_name', 'description', 'pros', 'cons', 'expected_outcome']
        widgets = {
            'option_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Option A: Stay at current firm and negotiate flexible hours',
                'autofocus': True,
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Details and implementation strategy for this pathway...',
            }),
            'pros': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Key advantages, positive payoffs, upside potential...',
            }),
            'cons': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Key risks, costs, negative side effects, downside...',
            }),
            'expected_outcome': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Projected 6-month result if this option is chosen...',
            }),
        }


# ==============================================================================
# 6. DECISION OUTCOME FORM
# ==============================================================================

class DecisionOutcomeForm(forms.ModelForm):
    outcome_score = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '10',
            'placeholder': '1 (Disastrous) to 10 (Ideal Success)',
            'required': True,
        }),
        help_text='Quantify real-world result from 1 to 10'
    )

    class Meta:
        model = DecisionOutcome
        fields = ['option', 'outcome_date', 'outcome_score', 'actual_outcome', 'lessons_learned', 'reflection_notes']
        widgets = {
            'option': forms.Select(attrs={'class': 'form-select'}),
            'outcome_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'actual_outcome': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What actually happened in reality?',
                'required': True,
            }),
            'lessons_learned': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What mental models or heuristics were validated or disproved?',
            }),
            'reflection_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any further thoughts, lingering effects, or future guidelines...',
            }),
        }

    def __init__(self, *args, decision=None, **kwargs):
        self.decision = decision
        super().__init__(*args, **kwargs)
        if self.decision:
            if not self.instance.decision_id:
                self.instance.decision = self.decision
            self.fields['option'].queryset = self.decision.options.all().order_by('option_name')
            if self.decision.chosen_option:
                self.initial['option'] = self.decision.chosen_option
        if not self.instance.pk and 'outcome_date' not in self.initial:
            self.initial['outcome_date'] = timezone.localdate()

    def clean_option(self):
        opt = self.cleaned_data.get('option')
        if opt and self.decision and opt.decision_id != self.decision.id:
            raise forms.ValidationError('Evaluated option must belong to this specific decision.')
        return opt


# ==============================================================================
# 7. MISTAKE FORM
# ==============================================================================

class MistakeForm(forms.ModelForm):
    class Meta:
        model = Mistake
        fields = [
            'title', 'category', 'mistake_date', 'impact_level', 'status',
            'cause_or_reason', 'description', 'lesson_learned', 'corrective_action', 'follow_up_notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Underestimated API migration timeline without benchmarking',
                'autofocus': True,
                'required': True,
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'mistake_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'impact_level': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cause_or_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Root causes, cognitive blindspots, emotional state, or assumptions...',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What occurred? Factual recounting without self-judgment...',
            }),
            'lesson_learned': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What is the primary takeaway or anti-pattern identified?',
                'required': True,
            }),
            'corrective_action': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What immediate or systemic protocol will prevent a recurrence?',
            }),
            'follow_up_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Status updates, observations after applying corrective action...',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if self.user:
            if not self.instance.user_id:
                self.instance.user = self.user
            self.fields['category'].queryset = Category.objects.filter(user=self.user).order_by('name')
        if not self.instance.pk and 'mistake_date' not in self.initial:
            self.initial['mistake_date'] = timezone.localdate()

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if cat and self.user and cat.user_id != self.user.id:
            raise forms.ValidationError('Cannot assign a category belonging to another user.')
        return cat
