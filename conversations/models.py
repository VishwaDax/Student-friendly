
from django.conf import settings
from django.db import models

from textbooks.models import Book


class ChatSession(models.Model):
    SCOPE_CHOICES = [
        ("book", "Book Chat"),
        ("main_room", "Main Room"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )

    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default="book",
    )

    title = models.CharField(
        max_length=200,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.student} - {self.scope}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.role} - {self.session_id}"
