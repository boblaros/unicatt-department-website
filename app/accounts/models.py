from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .choices import COUNTRY_CHOICES, STUDY_PROGRAM_CHOICES, YEAR_OF_STUDY_CHOICES


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified_student', True)
        extra_fields.setdefault('full_name', 'Administrator')
        extra_fields.setdefault('study_program', 'medicine')
        extra_fields.setdefault('year_of_study', 'postgrad')
        extra_fields.setdefault('country_of_origin', 'IT')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    study_program = models.CharField(max_length=32, choices=STUDY_PROGRAM_CHOICES)
    year_of_study = models.CharField(max_length=16, choices=YEAR_OF_STUDY_CHOICES)
    country_of_origin = models.CharField(max_length=16, choices=COUNTRY_CHOICES)
    is_verified_student = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.is_moderator:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def role(self):
        if self.is_superuser:
            return 'Admin'
        if self.is_moderator:
            return 'Moderator'
        return 'Student'


class RateLimitRecord(models.Model):
    action = models.CharField(max_length=50)
    key = models.CharField(max_length=255)
    count = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('action', 'key')

    @classmethod
    def allow(cls, action, key, limit, window_seconds):
        now = timezone.now()
        window_start = now - timedelta(seconds=window_seconds)
        record, _ = cls.objects.get_or_create(action=action, key=key)
        if record.window_started_at < window_start:
            record.window_started_at = now
            record.count = 0
        if record.count >= limit:
            record.save(update_fields=['window_started_at', 'count'])
            return False
        record.count += 1
        record.save(update_fields=['window_started_at', 'count'])
        return True
