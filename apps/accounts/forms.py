from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class RegistrationForm(forms.Form):
    """
    User registration form requiring full name, email, password, and confirmation.
    """
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Priyani Rathod',
            'autocomplete': 'name',
            'required': True,
        }),
        label='Full Name'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. user@lifeos.internal',
            'autocomplete': 'email',
            'required': True,
        }),
        label='Email Address'
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong master password',
            'autocomplete': 'new-password',
            'required': True,
        }),
        label='Password'
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter your master password',
            'autocomplete': 'new-password',
            'required': True,
        }),
        label='Confirm Password'
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email address already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', 'Passwords do not match. Please re-enter.')
            else:
                # Validate password against Django's configured password validators
                try:
                    validate_password(password)
                except ValidationError as error:
                    self.add_error('password', error)

        return cleaned_data

    def save(self):
        """Creates and saves a new User instance in MySQL."""
        full_name = self.cleaned_data['full_name'].strip()
        email = self.cleaned_data['email'].strip().lower()
        password = self.cleaned_data['password']

        # Parse first and last names
        parts = full_name.split(None, 1)
        first_name = parts[0] if parts else ''
        last_name = parts[1] if len(parts) > 1 else ''

        # Guarantee unique username (use email as primary username handle)
        username = email

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        return user


class LoginForm(forms.Form):
    """
    Secure login form requiring email and password with optional Remember Me session control.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'autocomplete': 'email',
            'required': True,
        }),
        label='Email Address'
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'required': True,
        }),
        label='Password'
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'custom-checkbox-input',
        }),
        label='Remember me on this device for 2 weeks'
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            email = email.strip().lower()
            self.user_cache = authenticate(self.request, email=email, password=password)

            # Avoid revealing whether the email exists
            if self.user_cache is None:
                raise ValidationError('Invalid email address or password. Please try again.')
            elif not self.user_cache.is_active:
                raise ValidationError('This user account is currently deactivated.')

        return cleaned_data

    def get_user(self):
        return self.user_cache


class UserProfileForm(forms.ModelForm):
    """
    Form allowing users to update their personal details and behavioral profile.
    """
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name',
        }),
        label='Full Name'
    )

    class Meta:
        model = User
        fields = ['bio', 'timezone_pref']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your personal philosophy, core drivers, or long-term vision...',
            }),
            'timezone_pref': forms.Select(
                choices=[
                    ('Asia/Kolkata', 'Asia/Kolkata (IST - UTC+5:30)'),
                    ('UTC', 'UTC (Coordinated Universal Time)'),
                    ('America/New_York', 'America/New_York (EST/EDT)'),
                    ('America/Los_Angeles', 'America/Los_Angeles (PST/PDT)'),
                    ('Europe/London', 'Europe/London (GMT/BST)'),
                    ('Europe/Berlin', 'Europe/Berlin (CET/CEST)'),
                    ('Asia/Singapore', 'Asia/Singapore (SGT)'),
                    ('Asia/Tokyo', 'Asia/Tokyo (JST)'),
                ],
                attrs={'class': 'form-select'}
            ),
        }
        labels = {
            'bio': 'Personal Philosophy / Bio',
            'timezone_pref': 'Primary Timezone',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            full_name = f"{self.instance.first_name} {self.instance.last_name}".strip()
            self.fields['full_name'].initial = full_name

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        parts = full_name.split(None, 1)
        user.first_name = parts[0] if parts else ''
        user.last_name = parts[1] if len(parts) > 1 else ''

        if commit:
            user.save()
        return user
