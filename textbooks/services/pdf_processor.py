from pathlib import Path

import pytesseract
from PIL import Image
import pymupdf

from django.conf import settings
from django.db import transaction

from textbooks.models import BookChunk
from textbooks.services.embeddings import encode_texts
from textbooks.services.local_search import index_chunks
from textbooks.services.passage_chunker import split_into_passages


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
        matrix=pymupdf.Matrix(2, 2),
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
    tessdata_dir = Path(settings.TESSERACT_DATA_DIR)
    tesseract_config = (
        f'--tessdata-dir {tessdata_dir}'
        if tessdata_dir.is_dir()
        else ""
    )

    try:
        return pytesseract.image_to_string(
            image,
            lang=lang,
            config=tesseract_config,
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
    """Extract, split, embed, and locally index one PDF."""
    pdf_path = book.pdf_file.path
    passages = []
    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            content = extract_page_text(page, book.language)
            passages.extend(
                (page_index + 1, passage)
                for passage in split_into_passages(content)
            )

    if not passages:
        raise ValueError(
            "No readable text was extracted from this PDF."
        )

    embeddings = encode_texts(
        [content for _page_number, content in passages]
    )
    chunks = [
        BookChunk(
            book=book,
            page_number=page_number,
            content=content,
            embedding=embedding,
        )
        for (page_number, content), embedding in zip(
            passages,
            embeddings,
            strict=True,
        )
    ]

    # Stage extraction and embeddings first; replace old data atomically.
    with transaction.atomic():
        BookChunk.objects.filter(book=book).delete()
        BookChunk.objects.bulk_create(chunks)
        saved_chunks = list(
            BookChunk.objects.filter(book=book).select_related("book")
        )
        index_chunks(saved_chunks)

    return len(passages)