
from django.db import models
from django.contrib.auth.models import AbstractUser

from textbooks.languages import (
    LANGUAGE_CHOICES,
    STANDARD_CHOICES,
)


class Student(AbstractUser):
    email_verified = models.BooleanField(default=False)
    email_otp_hash = models.CharField(max_length=128, blank=True)
    email_otp_expires_at = models.DateTimeField(null=True, blank=True)
    email_otp_sent_at = models.DateTimeField(null=True, blank=True)
    email_otp_attempts = models.PositiveSmallIntegerField(default=0)

    age = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    standard = models.CharField(
        max_length=20,
        choices=STANDARD_CHOICES,
        blank=True,
    )

    preferred_language = models.CharField(
        max_length=30,
        choices=LANGUAGE_CHOICES,
        default="english",
    )

    def __str__(self):
        return self.username
