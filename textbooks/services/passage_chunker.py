from django.conf import settings


def split_into_passages(
    text,
    chunk_size=None,
    overlap=None,
):
    """Split page text into overlapping passages without losing its page."""
    text = " ".join(text.split())
    if not text:
        return []

    if chunk_size is None:
        chunk_size = settings.TEXTBOOK_CHUNK_SIZE
    if overlap is None:
        overlap = settings.TEXTBOOK_CHUNK_OVERLAP
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Chunk size must be positive and overlap must be "
            "non-negative and smaller than the chunk size."
        )

    passages = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        passage = text[start:end].strip()
        if passage:
            passages.append(passage)
        if end == len(text):
            break
        start = max(end - overlap, start + 1)

    return passages
