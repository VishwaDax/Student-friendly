import os

import fitz
import pytesseract
from PIL import Image

from django.conf import settings
from django.db import transaction

from textbooks.models import BookChunk
from textbooks.search import create_book_index


# Map our application language codes to Tesseract codes.
TESSERACT_LANGUAGES = {
    "assamese": "asm",
    "bengali": "ben",
    "bodo": "eng",
    "dogri": "hin",
    "english": "eng",
    "gujarati": "guj",
    "hindi": "hin",
    "kannada": "kan",
    "kashmiri": "urd",
    "konkani": "mar",
    "maithili": "hin",
    "malayalam": "mal",
    "manipuri": "eng",
    "marathi": "mar",
    "nepali": "nep",
    "odia": "ori",
    "punjabi": "pan",
    "sanskrit": "san",
    "santali": "eng",
    "sindhi": "snd",
    "tamil": "tam",
    "telugu": "tel",
    "urdu": "urd",
}


def extract_page_text(page, language):
    """Extract selectable text; use OCR when little text is available."""
    text = page.get_text("text").strip()

    if len(text) >= 40:
        return text

    # OCR fallback for scanned or image-based pages.
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(2, 2),
        alpha=False,
    )

    image = Image.frombytes(
        "RGB",
        [pixmap.width, pixmap.height],
        pixmap.samples,
    )

    # Optional explicit path for Windows.
    tesseract_path = getattr(
        settings, "TESSERACT_CMD", None
    )
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    lang = TESSERACT_LANGUAGES.get(language, "eng")

    try:
        return pytesseract.image_to_string(
            image,
            lang=lang,
        ).strip()
    except pytesseract.TesseractError:
        # If a language data file is missing, do not silently
        # substitute English and present it as accurate OCR.
        raise RuntimeError(
            f"OCR failed for language '{language}'. "
            "Check that the required Tesseract language data "
            "is installed."
        )


def process_book(book):
    """Extract each page, save it in SQLite, then index it."""
    pdf_path = book.pdf_file.path
    chunks = []

    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            content = extract_page_text(page, book.language)

            if content:
                chunks.append(
                    BookChunk(
                        book=book,
                        page_number=page_index + 1,
                        content=content,
                    )
                )

    if not chunks:
        raise ValueError(
            "No readable text was extracted from this PDF."
        )

    # Replace previous chunks if the book is processed again.
    with transaction.atomic():
        BookChunk.objects.filter(book=book).delete()
        BookChunk.objects.bulk_create(chunks)

    # Index the saved passages in Elasticsearch.
    client = create_book_index()
    saved_chunks = BookChunk.objects.filter(book=book)

    for chunk in saved_chunks.iterator():
        client.index(
            index=settings.ELASTICSEARCH_BOOK_INDEX,
            id=str(chunk.id),
            document={
                "book_id": book.id,
                "student_id": book.student_id,
                "title": book.title,
                "language": book.language,
                "standard": book.standard,
                "page_number": chunk.page_number,
                "content": chunk.content,
            },
        )

    client.indices.refresh(
        index=settings.ELASTICSEARCH_BOOK_INDEX
    )

    return len(chunks)