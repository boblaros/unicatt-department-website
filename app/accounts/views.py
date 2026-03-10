from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.urls import reverse

from .forms import DeleteProfileForm, ForgotPasswordForm, LoginForm, PasswordSetupForm, ProfileUpdateForm, RegistrationForm
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


def _redirect_target(request, fallback_name):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse(fallback_name)


def _profile_context(request, profile_user, *, editable_mode, profile_form=None, delete_form=None):
    return {
        'profile_user': profile_user,
        'editable_mode': editable_mode,
        'profile_form': profile_form or ProfileUpdateForm(instance=request.user),
        'delete_form': delete_form or DeleteProfileForm(request.user),
    }


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


@login_required
@require_http_methods(['GET'])
def profile_view(request):
    context = _profile_context(request, request.user, editable_mode=True)
    return render(request, 'account/profile.html', context)


@require_http_methods(['GET'])
def public_profile_view(request, pk):
    profile_user = get_object_or_404(User.objects.filter(is_active=True), pk=pk)
    context = {
        'profile_user': profile_user,
        'editable_mode': False,
    }
    return render(request, 'account/profile.html', context)


@login_required
@require_http_methods(['POST'])
def update_profile_view(request):
    form = ProfileUpdateForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, _('Your profile details have been updated.'))
        return redirect('accounts:profile')

    context = _profile_context(
        request,
        request.user,
        editable_mode=True,
        profile_form=form,
    )
    return render(request, 'account/profile.html', context, status=400)


@login_required
@require_http_methods(['POST'])
def request_password_reset_view(request):
    target = _redirect_target(request, 'accounts:profile')
    if _rate_limited(request, 'password_reset', request.user.email):
        messages.error(request, _('Too many reset attempts. Please wait and try again.'))
        return redirect(target)

    try:
        with transaction.atomic():
            send_password_action_email(request, request.user, purpose='reset')
    except EmailDeliveryError:
        messages.error(request, _('We could not send the email right now. Please try again later.'))
    else:
        messages.success(request, _('We sent a secure password reset link to %(email)s.') % {'email': request.user.email})
    return redirect(target)


@login_required
@require_http_methods(['POST'])
def delete_profile_view(request):
    form = DeleteProfileForm(request.user, request.POST)
    if form.is_valid():
        with transaction.atomic():
            request.user.deactivate_profile()
        logout(request)
        messages.success(request, _('Your profile has been deleted.'))
        return redirect('core:home')

    context = _profile_context(
        request,
        request.user,
        editable_mode=True,
        delete_form=form,
    )
    return render(request, 'account/profile.html', context, status=400)
