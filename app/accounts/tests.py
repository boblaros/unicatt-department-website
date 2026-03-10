import re
from unittest.mock import patch

from django.contrib import admin
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .admin import UserAdmin
from .models import RateLimitRecord, User
from .utils import EmailDeliveryError
from .views import _client_ip


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountFlowTests(TestCase):
    def registration_payload(self, email='student@unicatt.it'):
        return {
            'email': email,
            'full_name': 'Student Example',
            'study_program': 'medicine',
            'year_of_study': '1',
            'country_of_origin': 'IT',
        }

    def extract_path_from_email(self, body):
        match = re.search(r'https?://testserver(?P<path>\S+)', body)
        self.assertIsNotNone(match)
        return match.group('path')

    def test_registration_sends_setup_link_and_password_is_set_later(self):
        response = self.client.post(reverse('accounts:register'), self.registration_payload())

        self.assertRedirects(response, reverse('accounts:login'))
        user = User.objects.get(email='student@unicatt.it')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/accounts/set-password/', mail.outbox[0].body)

        set_password_path = self.extract_path_from_email(mail.outbox[0].body)
        response = self.client.post(
            set_password_path,
            {'new_password1': 'SecurePass123!', 'new_password2': 'SecurePass123!'},
        )

        self.assertRedirects(response, reverse('accounts:login'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('SecurePass123!'))

    def test_registration_rolls_back_when_email_delivery_fails(self):
        with patch('accounts.views.send_password_action_email', side_effect=EmailDeliveryError):
            response = self.client.post(reverse('accounts:register'), self.registration_payload())

        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.filter(email='student@unicatt.it').exists())

    def test_password_reset_email_failure_leaves_credentials_unchanged(self):
        user = User.objects.create_user(
            email='student@unicatt.it',
            password='OriginalPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )

        with patch('accounts.views.send_password_action_email', side_effect=EmailDeliveryError):
            response = self.client.post(reverse('accounts:forgot_password'), {'email': user.email})

        self.assertEqual(response.status_code, 503)
        user.refresh_from_db()
        self.assertTrue(user.check_password('OriginalPass123!'))

    def test_password_reset_uses_secure_link_without_mutating_password_until_confirmation(self):
        user = User.objects.create_user(
            email='student@unicatt.it',
            password='OriginalPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )

        response = self.client.post(reverse('accounts:forgot_password'), {'email': user.email})

        self.assertRedirects(response, reverse('accounts:login'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('OriginalPass123!'))
        self.assertEqual(len(mail.outbox), 1)

        set_password_path = self.extract_path_from_email(mail.outbox[0].body)
        response = self.client.post(
            set_password_path,
            {'new_password1': 'UpdatedPass123!', 'new_password2': 'UpdatedPass123!'},
        )

        self.assertRedirects(response, reverse('accounts:login'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('UpdatedPass123!'))

    def test_login_accepts_mixed_case_email(self):
        user = User.objects.create_user(
            email='student@unicatt.it',
            password='OriginalPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )

        response = self.client.post(
            reverse('accounts:login'),
            {'email': 'Student@UniCatt.it', 'password': 'OriginalPass123!'},
        )

        self.assertRedirects(response, reverse('core:home'))
        self.assertEqual(str(user.pk), self.client.session.get('_auth_user_id'))

    def test_client_ip_uses_trusted_real_ip_header(self):
        request = RequestFactory().get(
            '/',
            HTTP_X_FORWARDED_FOR='203.0.113.10, 10.0.0.1',
            HTTP_X_REAL_IP='198.51.100.20',
            REMOTE_ADDR='172.18.0.2',
        )

        self.assertEqual(_client_ip(request), '198.51.100.20')

    def test_rate_limit_cannot_be_bypassed_by_spoofing_forwarded_for(self):
        url = reverse('accounts:login')

        for index in range(10):
            response = self.client.post(
                url,
                {'email': f'user{index}@example.com', 'password': 'wrong-pass'},
                HTTP_X_REAL_IP='198.51.100.20',
                HTTP_X_FORWARDED_FOR=f'203.0.113.{index}',
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url,
            {'email': 'overflow@example.com', 'password': 'wrong-pass'},
            HTTP_X_REAL_IP='198.51.100.20',
            HTTP_X_FORWARDED_FOR='192.0.2.55',
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            RateLimitRecord.objects.get(action='login', key='ip:198.51.100.20').count,
            10,
        )


class ModeratorUserAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = UserAdmin(User, admin.site)
        self.superuser = User.objects.create_superuser('admin@unicatt.it', 'SuperPass123!')
        self.moderator = User.objects.create_user(
            email='moderator@unicatt.it',
            password='ModPass123!',
            full_name='Moderator Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
            is_moderator=True,
            is_staff=True,
        )
        self.student = User.objects.create_user(
            email='student@unicatt.it',
            password='StudentPass123!',
            full_name='Student Example',
            study_program='medicine',
            year_of_study='1',
            country_of_origin='IT',
            is_verified_student=True,
        )

    def test_moderator_queryset_and_permissions_are_limited_to_students(self):
        request = self.factory.get('/admin/accounts/user/')
        request.user = self.moderator

        queryset = self.model_admin.get_queryset(request)

        self.assertQuerySetEqual(queryset.order_by('pk'), [self.student], transform=lambda obj: obj)
        self.assertFalse(self.model_admin.has_add_permission(request))
        self.assertFalse(self.model_admin.has_change_permission(request, self.moderator))
        self.assertFalse(self.model_admin.has_change_permission(request, self.superuser))
        self.assertTrue(self.model_admin.has_change_permission(request, self.student))

    def test_moderator_post_cannot_escalate_student_privileges(self):
        self.client.force_login(self.moderator)

        response = self.client.post(
            reverse('admin:accounts_user_change', args=[self.student.pk]),
            {
                'full_name': 'Updated Student',
                'study_program': 'law',
                'year_of_study': '2',
                'country_of_origin': 'US',
                'is_verified_student': 'on',
                'is_banned': 'on',
                'is_staff': 'on',
                'is_superuser': 'on',
                'is_moderator': 'on',
                '_save': 'Save',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, 'Updated Student')
        self.assertEqual(self.student.study_program, 'law')
        self.assertEqual(self.student.year_of_study, '2')
        self.assertEqual(self.student.country_of_origin, 'US')
        self.assertTrue(self.student.is_banned)
        self.assertFalse(self.student.is_staff)
        self.assertFalse(self.student.is_superuser)
        self.assertFalse(self.student.is_moderator)
