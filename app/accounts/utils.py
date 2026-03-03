import secrets
import string

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _


def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def send_new_password_email(email, password):
    subject = _('Your UCSC integration portal password')
    body = (
        _('Your new password has been generated.') + '\n\n'
        + _('Email: %(email)s') % {'email': email}
        + '\n'
        + _('Password: %(password)s') % {'password': password}
        + '\n\n'
        + _('Please keep it secure.')
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
