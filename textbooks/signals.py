from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Book, BookChunk
from .services.local_search import (
    index_chunks,
    remove_chunk_entries,
)


@receiver(post_save, sender=BookChunk)
def index_saved_chunk(sender, instance, **kwargs):
    index_chunks([instance])


@receiver(post_save, sender=Book)
def refresh_book_metadata_in_fts(sender, instance, **kwargs):
    chunks = instance.chunks.select_related("book").iterator()
    index_chunks(chunks)


@receiver(pre_delete, sender=BookChunk)
def remove_deleted_chunk_from_fts(sender, instance, **kwargs):
    remove_chunk_entries([instance.pk])
