import re

from textbooks.models import Topic, BookChunk


CHAPTER_PATTERN = re.compile(
    r"^\s*(chapter|unit|lesson)\s+"
    r"([0-9]+|[ivxlcdm]+)\b",
    re.IGNORECASE,
)

NUMBERED_HEADING_PATTERN = re.compile(
    r"^\s*\d+(?:\.\d+)*[.)]?\s+\S+"
)


def looks_like_heading(line):
    line = " ".join(line.split())

    if not line or len(line) > 120:
        return False

    if len(line.split()) > 15:
        return False

    if CHAPTER_PATTERN.match(line):
        return True

    if NUMBERED_HEADING_PATTERN.match(line):
        return True

    # Heuristic: short lines written in uppercase.
    letters = [char for char in line if char.isalpha()]
    if letters and all(char.isupper() for char in letters):
        return True

    return False


def detect_topics(book):
    """
    Detect likely headings from extracted page text.

    This is a heuristic, not a perfect chapter parser.
    """
    chunks = BookChunk.objects.filter(
        book=book
    ).order_by("page_number", "id")

    detected = []

    for chunk in chunks.iterator():
        for line in chunk.content.splitlines():
            title = " ".join(line.split())

            if not looks_like_heading(title):
                continue

            topic_type = (
                "chapter"
                if CHAPTER_PATTERN.match(title)
                else "topic"
            )

            detected.append(
                Topic(
                    book=book,
                    title=title,
                    topic_type=topic_type,
                    page_number=chunk.page_number,
                )
            )

    # Replace the existing topic index for this book.
    Topic.objects.filter(book=book).delete()

    # Avoid duplicate headings on the same page.
    unique_topics = {}
    for topic in detected:
        key = (
            topic.title.casefold(),
            topic.page_number,
            topic.topic_type,
        )
        unique_topics[key] = topic

    Topic.objects.bulk_create(unique_topics.values())

    return len(unique_topics)