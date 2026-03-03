from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from .choices import ALLOWED_EMAIL_DOMAINS
from .models import User


def _email_domain(email):
    return email.split('@')[-1].lower() if '@' in email else ''


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        password = cleaned.get('password')
        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if not user:
                raise forms.ValidationError(_('Invalid credentials.'))
            if user.is_banned:
                raise forms.ValidationError(_('This account is banned.'))
            if not user.is_active:
                raise forms.ValidationError(_('This account is inactive.'))
            self.user = user
        return cleaned


class RegistrationForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['email', 'full_name', 'study_program', 'year_of_study', 'country_of_origin']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        domain = _email_domain(email)
        if domain not in ALLOWED_EMAIL_DOMAINS:
            raise forms.ValidationError(_('Only @unicatt.it and @icatt.it emails are allowed.'))
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('An account with this email already exists.'))
        return email


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        domain = _email_domain(email)
        if domain not in ALLOWED_EMAIL_DOMAINS:
            raise forms.ValidationError(_('Only university student emails are supported.'))
        return email
