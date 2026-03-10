from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from .forms import ForgotPasswordForm, LoginForm, PasswordSetupForm, RegistrationForm
from .models import RateLimitRecord, User
from .utils import EmailDeliveryError, send_password_action_email


def _client_ip(request):
    real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
    if real_ip:
        return real_ip
    return request.META.get('REMOTE_ADDR', 'unknown').strip() or 'unknown'


def _rate_limited(request, action, email):
    ip = _client_ip(request)
    email_key = (email or 'unknown').lower()
    ip_ok = RateLimitRecord.allow(action, f'ip:{ip}', limit=10, window_seconds=300)
    email_ok = RateLimitRecord.allow(action, f'email:{email_key}', limit=5, window_seconds=300)
    return not (ip_ok and email_ok)


def _render_mail_failure(request, template_name, form):
    messages.error(request, _('We could not send the email right now. Please try again later.'))
    return render(request, template_name, {'form': form}, status=503)


def _get_user_from_token(uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
    if not default_token_generator.check_token(user, token):
        return None
    return user


@require_http_methods(['GET', 'POST'])
def login_view(request):
    form = LoginForm(request=request, data=request.POST or None)
    if request.method == 'POST':
        email = request.POST.get('email', '')
        if _rate_limited(request, 'login', email):
            messages.error(request, _('Too many attempts. Please wait and try again.'))
            return render(request, 'account/login.html', {'form': form}, status=429)
        if form.is_valid():
            login(request, form.user)
            return redirect('core:home')
    return render(request, 'account/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save(commit=False)
                user.is_verified_student = True
                user.set_unusable_password()
                user.save()
                send_password_action_email(request, user, purpose='setup')
        except EmailDeliveryError:
            return _render_mail_failure(request, 'account/register.html', form)
        messages.success(request, _('Registration successful. Check your email to set your password.'))
        return redirect('accounts:login')
    return render(request, 'account/register.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST':
        email = request.POST.get('email', '')
        if _rate_limited(request, 'password_reset', email):
            messages.error(request, _('Too many reset attempts. Please wait and try again.'))
            return render(request, 'account/forgot_password.html', {'form': form}, status=429)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email__iexact=email).first()
            if user and not user.is_banned and user.is_active:
                try:
                    with transaction.atomic():
                        send_password_action_email(request, user, purpose='reset')
                except EmailDeliveryError:
                    return _render_mail_failure(request, 'account/forgot_password.html', form)
            messages.success(request, _('If the email is registered, a password reset link has been sent.'))
            return redirect('accounts:login')
    return render(request, 'account/forgot_password.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def set_password_view(request, uidb64, token):
    user = _get_user_from_token(uidb64, token)
    if not user:
        messages.error(request, _('This password link is invalid or has expired.'))
        return redirect('accounts:login')

    form = PasswordSetupForm(user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _('Your password has been updated. You can now log in.'))
        return redirect('accounts:login')

    return render(
        request,
        'account/set_password.html',
        {
            'form': form,
            'target_user': user,
        },
    )


@login_required
def logout_view(request):
    logout(request)
    return redirect('core:home')
