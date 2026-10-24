from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from textbooks.models import Book
from textbooks.services.embeddings import encode_texts
from textbooks.services.local_search import (
    index_chunks,
    rebuild_fts_index,
    valid_embedding,
)
from textbooks.services.pdf_processor import process_book
from textbooks.services.topic_detector import detect_topics


class Command(BaseCommand):
    help = (
        "Rebuild local textbook search entries and generate missing "
        "multilingual embeddings."
    )

    def handle(self, *args, **options):
        succeeded = 0
        failures = []

        for book in Book.objects.order_by("id").iterator():
            try:
                pdf_path = (
                    Path(book.pdf_file.path)
                    if book.pdf_file
                    else None
                )
                if pdf_path and pdf_path.is_file():
                    process_book(book)
                    detect_topics(book)
                else:
                    self._index_existing_chunks(book)

                if book.status != "ready":
                    book.status = "ready"
                    book.save(update_fields=["status"])
                succeeded += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Reindexed book {book.pk}: {book.title}"
                    )
                )
            except Exception as exc:
                failures.append((book.pk, book.title, exc))
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed book {book.pk} ({book.title}): {exc}"
                    )
                )

        try:
            rebuild_fts_index()
        except Exception as exc:
            raise CommandError(
                f"Could not rebuild the SQLite FTS5 index: {exc}"
            ) from exc

        self.stdout.write(
            f"Reindex complete: {succeeded} succeeded, "
            f"{len(failures)} failed."
        )
        if failures:
            raise CommandError(
                f"{len(failures)} book(s) could not be reindexed; "
                "existing passages were retained where processing failed."
            )

    def _index_existing_chunks(self, book):
        chunks = list(
            book.chunks.select_related("book").order_by("id")
        )
        if not chunks:
            raise ValueError(
                "No readable PDF file or existing extracted passages."
            )

        missing = [
            chunk
            for chunk in chunks
            if valid_embedding(chunk.embedding) is None
        ]
        embeddings = encode_texts([chunk.content for chunk in missing])

        with transaction.atomic():
            for chunk, embedding in zip(missing, embeddings, strict=True):
                chunk.embedding = embedding
                chunk.save(update_fields=["embedding"])
            index_chunks(chunks)
