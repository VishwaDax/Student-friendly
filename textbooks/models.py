
from django.conf import settings
from django.db import models

from .languages import LANGUAGE_CHOICES, STANDARD_CHOICES


class Book(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="books",
    )

    title = models.CharField(max_length=200)

    language = models.CharField(
        max_length=30,
        choices=LANGUAGE_CHOICES,
    )

    standard = models.CharField(
        max_length=20,
        choices=STANDARD_CHOICES,
    )

    subject = models.CharField(max_length=100)

    pdf_file = models.FileField(
        upload_to="textbooks/"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title


class BookChunk(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chunks",
    )

    page_number = models.PositiveIntegerField()

    content = models.TextField()

    def __str__(self):
        return f"{self.book.title} - Page {self.page_number}"
class Topic(models.Model):
    TOPIC_TYPES = [
        ("chapter", "Chapter"),
        ("topic", "Topic"),
    ]

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    title = models.CharField(max_length=255)
    topic_type = models.CharField(
        max_length=20,
        choices=TOPIC_TYPES,
        default="topic",
    )
    page_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["page_number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "book",
                    "title",
                    "page_number",
                    "topic_type",
                ],
                name="unique_book_topic_page_type",
            )
        ]

    def __str__(self):
        return f"{self.title} - Page {self.page_number}"