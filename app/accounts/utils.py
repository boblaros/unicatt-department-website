from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _


class EmailDeliveryError(Exception):
    pass


def build_password_action_url(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    relative_url = reverse('accounts:set_password', kwargs={'uidb64': uid, 'token': token})
    return request.build_absolute_uri(relative_url)


def send_password_action_email(request, user, purpose):
    action_url = build_password_action_url(request, user)
    if purpose == 'setup':
        subject = _('Set your UCSC integration portal password')
        intro = _('Welcome to the UCSC integration portal.')
        action_text = _('Use the secure link below to set your password:')
    else:
        subject = _('Reset your UCSC integration portal password')
        intro = _('A password reset was requested for your account.')
        action_text = _('Use the secure link below to choose a new password:')

    body = '\n\n'.join(
        [
            intro,
            _('Email: %(email)s') % {'email': user.email},
            action_text,
            action_url,
            _('If you did not expect this message, you can ignore it.'),
        ]
    )

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception as exc:
        raise EmailDeliveryError from exc
