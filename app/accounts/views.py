from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ForgotPasswordForm, LoginForm, RegistrationForm
from .models import RateLimitRecord, User
from .utils import generate_password, send_new_password_email


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _rate_limited(request, action, email):
    ip = _client_ip(request)
    email_key = (email or 'unknown').lower()
    ip_ok = RateLimitRecord.allow(action, f'ip:{ip}', limit=10, window_seconds=300)
    email_ok = RateLimitRecord.allow(action, f'email:{email_key}', limit=5, window_seconds=300)
    return not (ip_ok and email_ok)


@require_http_methods(['GET', 'POST'])
def login_view(request):
    form = LoginForm(request=request, data=request.POST or None)
    if request.method == 'POST':
        email = request.POST.get('email', '')
        if _rate_limited(request, 'login', email):
            messages.error(request, 'Too many attempts. Please wait and try again.')
            return render(request, 'account/login.html', {'form': form}, status=429)
        if form.is_valid():
            login(request, form.user)
            return redirect('core:home')
    return render(request, 'account/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = generate_password()
        user = form.save(commit=False)
        user.is_verified_student = True
        user.set_password(password)
        user.save()
        send_new_password_email(user.email, password)
        messages.success(request, 'Registration successful. Check your email for your password.')
        return redirect('accounts:login')
    return render(request, 'account/register.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST':
        email = request.POST.get('email', '')
        if _rate_limited(request, 'password_reset', email):
            messages.error(request, 'Too many reset attempts. Please wait and try again.')
            return render(request, 'account/forgot_password.html', {'form': form}, status=429)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user and not user.is_banned and user.is_active:
                password = generate_password()
                user.set_password(password)
                user.save(update_fields=['password'])
                send_new_password_email(user.email, password)
            messages.success(request, 'If the email is registered, a new password has been sent.')
            return redirect('accounts:login')
    return render(request, 'account/forgot_password.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('core:home')
