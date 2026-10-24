import math
import re
import sqlite3

import numpy as np
from django.conf import settings
from django.db import OperationalError, connection, transaction

from textbooks.models import BookChunk
from textbooks.services.embeddings import encode_texts


FTS_TABLE = "textbooks_chunks_fts"
FTS_UNAVAILABLE_MESSAGE = (
    "SQLite FTS5 is not available in this Python/SQLite build. "
    "Use a Python distribution with SQLite compiled with FTS5 support."
)
RRF_K = 60
EMBEDDING_DIMENSIONS = 384


class FTS5UnavailableError(RuntimeError):
    """Raised when SQLite lacks the FTS5 extension."""


def ensure_fts_table():
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = %s",
                [FTS_TABLE],
            )
            table_exists = cursor.fetchone() is not None
            cursor.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE}
                USING fts5(
                    chunk_id UNINDEXED,
                    book_id UNINDEXED,
                    student_id UNINDEXED,
                    title,
                    page_number UNINDEXED,
                    content,
                    tokenize='unicode61'
                )
                """
            )
            if not table_exists:
                cursor.execute(
                    f"""
                    INSERT INTO {FTS_TABLE}
                        (
                            chunk_id,
                            book_id,
                            student_id,
                            title,
                            page_number,
                            content
                        )
                    SELECT
                        chunk.id,
                        book.id,
                        book.student_id,
                        book.title,
                        chunk.page_number,
                        chunk.content
                    FROM textbooks_bookchunk AS chunk
                    JOIN textbooks_book AS book ON book.id = chunk.book_id
                    """
                )
    except (OperationalError, sqlite3.OperationalError) as exc:
        if "fts5" in str(exc).lower() or "no such module" in str(exc).lower():
            raise FTS5UnavailableError(FTS_UNAVAILABLE_MESSAGE) from exc
        raise


def remove_chunk_entries(chunk_ids):
    chunk_ids = [int(chunk_id) for chunk_id in chunk_ids]
    if not chunk_ids:
        return
    ensure_fts_table()
    placeholders = ", ".join(["%s"] * len(chunk_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {FTS_TABLE} WHERE chunk_id IN ({placeholders})",
            chunk_ids,
        )


def index_chunks(chunks):
    chunks = list(chunks)
    if not chunks:
        return

    ensure_fts_table()
    with connection.cursor() as cursor:
        cursor.executemany(
            f"DELETE FROM {FTS_TABLE} WHERE chunk_id = %s",
            [(chunk.pk,) for chunk in chunks],
        )
        cursor.executemany(
            f"""
            INSERT INTO {FTS_TABLE}
                (chunk_id, book_id, student_id, title, page_number, content)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    chunk.pk,
                    chunk.book_id,
                    chunk.book.student_id,
                    chunk.book.title,
                    chunk.page_number,
                    chunk.content,
                )
                for chunk in chunks
            ],
        )


def rebuild_fts_index():
    ensure_fts_table()
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {FTS_TABLE}")

        chunks = (
            BookChunk.objects.select_related("book")
            .order_by("id")
            .iterator(chunk_size=500)
        )
        batch = []
        for chunk in chunks:
            batch.append(chunk)
            if len(batch) == 500:
                index_chunks(batch)
                batch.clear()
        if batch:
            index_chunks(batch)


def _fts_query_tokens(query):
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)[:30]
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"' for token in tokens)


def _keyword_rankings(student_id, query, book_id, limit):
    fts_query = _fts_query_tokens(query)
    if not fts_query:
        return []

    ensure_fts_table()
    conditions = [
        f"{FTS_TABLE} MATCH %s",
        "CAST(student_id AS INTEGER) = %s",
    ]
    parameters = [fts_query, student_id]
    if book_id is not None:
        conditions.append("CAST(book_id AS INTEGER) = %s")
        parameters.append(book_id)
    parameters.append(limit)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT CAST(chunk_id AS INTEGER)
            FROM {FTS_TABLE}
            WHERE {" AND ".join(conditions)}
            ORDER BY bm25({FTS_TABLE}, 0, 0, 0, 2.0, 0, 1.0)
            LIMIT %s
            """,
            parameters,
        )
        return [row[0] for row in cursor.fetchall()]


def valid_embedding(embedding):
    if not isinstance(embedding, list) or len(embedding) != EMBEDDING_DIMENSIONS:
        return None
    try:
        vector = np.asarray(embedding, dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(vector).all():
        return None
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0:
        return None
    return vector / norm


def _semantic_rankings(student_id, query, book_id, limit):
    chunks = BookChunk.objects.filter(
        book__student_id=student_id,
        book__status="ready",
        embedding__isnull=False,
    )
    if book_id is not None:
        chunks = chunks.filter(book_id=book_id)

    candidates = []
    for chunk in chunks.only("id", "embedding").iterator(chunk_size=500):
        vector = valid_embedding(chunk.embedding)
        if vector is not None:
            candidates.append((chunk.pk, vector))
    if not candidates:
        return []

    query_embedding = valid_embedding(encode_texts([query])[0])
    if query_embedding is None:
        return []

    scored = [
        (chunk_id, float(np.dot(vector, query_embedding)))
        for chunk_id, vector in candidates
    ]
    scored = [
        item
        for item in scored
        if item[1] >= settings.TEXTBOOK_MIN_COSINE_SIMILARITY
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [chunk_id for chunk_id, _score in scored[:limit]]


def hybrid_search(student, query, book_id=None, limit=10):
    """Combine authorized FTS5 and semantic rankings with reciprocal rank fusion."""
    if not isinstance(query, str):
        return []
    query = query.strip()
    if not query or not isinstance(limit, int) or limit < 1:
        return []
    if not _fts_query_tokens(query):
        return []

    student_id = student.pk
    keyword_ids = _keyword_rankings(
        student_id,
        query,
        book_id,
        limit,
    )
    semantic_ids = _semantic_rankings(
        student_id,
        query,
        book_id,
        limit,
    )

    fused_scores = {}
    for ranked_ids in (keyword_ids, semantic_ids):
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (
                1.0 / (RRF_K + rank)
            )

    if not fused_scores:
        return []

    # Recheck ownership and book scope against SQLite before returning passages.
    authorized = BookChunk.objects.filter(
        pk__in=fused_scores,
        book__student_id=student_id,
        book__status="ready",
    ).select_related("book")
    if book_id is not None:
        authorized = authorized.filter(book_id=book_id)
    verified = {chunk.pk: chunk for chunk in authorized}

    ordered_ids = sorted(
        (chunk_id for chunk_id in fused_scores if chunk_id in verified),
        key=lambda chunk_id: fused_scores[chunk_id],
        reverse=True,
    )[:limit]
    return [
        {
            "book_id": verified[chunk_id].book_id,
            "title": verified[chunk_id].book.title,
            "language": verified[chunk_id].book.language,
            "page_number": verified[chunk_id].page_number,
            "content": verified[chunk_id].content,
            "score": fused_scores[chunk_id],
        }
        for chunk_id in ordered_ids
    ]
