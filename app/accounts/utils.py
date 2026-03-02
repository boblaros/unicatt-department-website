import secrets
import string

from django.conf import settings
from django.core.mail import send_mail


def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def send_new_password_email(email, password):
    subject = 'Your UCSC integration portal password'
    body = (
        'Your new password has been generated.\n\n'
        f'Email: {email}\n'
        f'Password: {password}\n\n'
        'Please keep it secure.'
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
