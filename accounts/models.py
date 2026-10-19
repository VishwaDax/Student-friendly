
from django.db import models
from django.contrib.auth.models import AbstractUser

from textbooks.languages import (
    LANGUAGE_CHOICES,
    STANDARD_CHOICES,
)


class Student(AbstractUser):
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
