# Student Learning Platform --- Textbook Search & Chat

A Django learning platform where students upload school textbooks,
extract their content, and search only within books they are authorized
to access. The initial version uses **SQLite** for application data and
**Elasticsearch** for full-text search. PyMuPDF extracts PDF text, while
Tesseract OCR is used as a fallback for scanned pages.

> **Current stage:** Phase 1 (student accounts and models) and Phase 2
> (PDF upload, text extraction/OCR, and Elasticsearch indexing).
>
> **LLM/Ollama is intentionally deferred.** The initial search/chat
> version should return passages from the textbook with page references,
> not generated answers based on outside knowledge.

## Project goals

-   Student signup/login and profile fields for age, class/standard, and
    preferred language.
-   Upload PDF textbooks and associate each book with its owner.
-   Extract page text and use OCR for scanned pages when necessary.
-   Store extracted passages in SQLite and index them in Elasticsearch.
-   Support Book Chat (one selected book) and Main Room (the student's
    authorized books).
-   Return only evidence from authorized textbooks; abstain when the
    source does not contain enough information.
-   Add chapter/topic extraction and multilingual hybrid search in later
    phases.

## Technology stack

  Technology            Purpose
  --------------------- ---------------------------------------------
  Python and Django     Web application, authentication, forms, ORM
  SQLite                Initial application database
  Elasticsearch         Full-text search index
  PyMuPDF (`pymupdf`)   PDF text extraction and page rendering
  Pillow                Image handling for OCR
  Tesseract OCR         Text extraction from scanned/image PDFs
  `pytesseract`         Python interface to Tesseract

## Supported languages

The intended interface supports English plus India's 22 Eighth Schedule
languages: Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada,
Kashmiri, Konkani, Maithili, Malayalam, Manipuri (Meitei), Marathi,
Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, and
Urdu.

**OCR support must be configured separately.** Install and test the
correct Tesseract trained-data file for each language. A language
appearing in the form does not guarantee OCR support; do not silently
treat an English fallback as accurate transcription of another language.

## Current features

-   Custom Django `Student` user model.
-   Signup, login, dashboard, and logout.
-   `Book` model with student ownership, metadata, PDF, and processing
    status.
-   `BookChunk` model for extracted text and page number.
-   PDF upload form with a size limit and basic PDF signature
    validation.
-   PyMuPDF text extraction with Tesseract OCR fallback.
-   Elasticsearch index containing book ID, student ID, language, class,
    page number, and content.
-   `ChatSession` and `ChatMessage` models as the foundation for later
    chat features.

## Not implemented yet

-   Book-specific chat and Main Room search interfaces.
-   Secure search endpoints with student ownership filtering.
-   Chapter/topic detection.
-   Multilingual semantic embeddings and hybrid ranking.
-   Background processing for large PDFs.
-   LLM/Ollama answer generation.

## Project structure

``` text
student_learning_platform/
├── manage.py
├── db.sqlite3
├── media/
│   └── textbooks/
├── config/
│   ├── settings.py
│   └── urls.py
├── accounts/
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── templates/accounts/
├── textbooks/
│   ├── languages.py
│   ├── models.py
│   ├── forms.py
│   ├── search.py
│   ├── urls.py
│   ├── views.py
│   ├── services/
│   │   └── pdf_processor.py
│   └── templates/textbooks/
└── conversations/
    └── models.py
```

## Requirements

-   Python 3.10 or later recommended.
-   Elasticsearch server installed and running separately.
-   Tesseract OCR installed separately if scanned PDFs need OCR.
-   Tesseract language data for the languages you need.
-   The commands below assume Windows PowerShell and a virtual
    environment named `venv`.

## Installation

### 1. Create or activate the virtual environment

``` powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install django pymupdf pillow pytesseract elasticsearch
```

If the project and apps already exist from Phase 1, do not run
`startproject` or `startapp` again.

For a brand-new project only:

``` powershell
django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp textbooks
python manage.py startapp conversations
```

### 2. Configure Django

In `config/settings.py`, register the apps in `INSTALLED_APPS`:

``` python
INSTALLED_APPS = [
    # Django default apps...
    "accounts",
    "textbooks",
    "conversations",
]
```

Configure the custom user model **before initial migrations**:

``` python
AUTH_USER_MODEL = "accounts.Student"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

ELASTICSEARCH_URL = "http://localhost:9200"
ELASTICSEARCH_BOOK_INDEX = "textbook_pages"

# Set this if Tesseract is not available on PATH:
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

SQLite is Django's default database for this project:

``` python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

If Tesseract is installed elsewhere, use its actual executable path.

### 3. Start Elasticsearch

Start the Elasticsearch server using your installation method and check:

`http://localhost:9200`

A running server should return JSON with cluster information. The
`elasticsearch` Python package is only a client; it does not install or
start the server. If authentication or HTTPS is enabled, configure the
client securely and keep credentials in environment variables.

### 4. Run migrations

``` powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

The superuser command is optional. **Custom-user warning:**
`AUTH_USER_MODEL` should be configured before the first migration. If
you already migrated with Django's default user model, do not delete the
database blindly; inspect and resolve the migration state first.

## Run the application

``` powershell
python manage.py runserver
```

  Page              URL
  ----------------- ---------------------------------------------
  Root redirect     `http://127.0.0.1:8000/`
  Signup            `http://127.0.0.1:8000/accounts/signup/`
  Login             `http://127.0.0.1:8000/accounts/login/`
  Dashboard         `http://127.0.0.1:8000/accounts/dashboard/`
  Upload textbook   `http://127.0.0.1:8000/textbooks/upload/`
  Django admin      `http://127.0.0.1:8000/admin/`

The dashboard and upload page require login. Uploaded PDFs are stored
under `MEDIA_ROOT` during development.

## Phase 2 processing flow

1.  Student logs in and submits a PDF.
2.  Django validates the file and assigns ownership from `request.user`.
3.  PyMuPDF opens the PDF and extracts selectable text page by page.
4.  If a page has little selectable text, the page is rendered and sent
    to Tesseract OCR.
5.  Non-empty page text is stored as `BookChunk` rows in SQLite, with
    one-based page numbers.
6.  Passages are indexed in Elasticsearch with book and student
    identifiers.
7.  The book status becomes `ready` or `failed`.

### Verify the results

-   Inspect `Book` and `BookChunk` in Django admin.
-   On a local Elasticsearch instance without authentication, inspect:
    `http://localhost:9200/textbook_pages/_search?pretty=true`

Never expose an unauthenticated Elasticsearch endpoint publicly.

## Data models

-   **Student:** Django user plus age, standard/class, and preferred
    language.
-   **Book:** owner, title, language, standard, subject, PDF file,
    status, upload timestamp.
-   **BookChunk:** related book, page number, extracted page content.
-   **ChatSession:** student, scope (`book` or `main_room`), optional
    book, title, timestamp.
-   **ChatMessage:** chat session, role, content, timestamp.

## Roadmap

### Phase 3 --- Topics and secure search

-   Detect chapter headings and create topic/chapter records.
-   Add a search endpoint that filters every result to the authenticated
    student's books.
-   Book Chat searches only its selected book.
-   Main Room searches only the student's authorized books.
-   Return source title, page number, and matching passages.
-   Show a no-answer message when evidence is insufficient.

### Phase 4 --- Hybrid retrieval

-   Normalize text carefully for each supported language.
-   Split long pages into passages while preserving page references.
-   Add multilingual semantic embeddings.
-   Combine keyword and semantic results with rank fusion such as
    Reciprocal Rank Fusion.
-   Evaluate search quality for each language.

### Phase 5 --- Chat interface

-   Build Book Chat and Main Room.
-   Display source passages and page references.
-   Keep generated answers disabled until retrieval and access controls
    are tested.

### Phase 6 --- Optional LLM/Ollama

-   Send only authorized retrieved passages to the model.
-   Require citations to source pages.
-   Abstain when passages do not support an answer.
-   Never use general knowledge to fill gaps in the textbook.

### Phase 7 --- Production readiness

-   Add background jobs for large PDFs, progress reporting, retries, and
    logging.
-   Add automated tests for ownership isolation, OCR, search filters,
    and abstention.
-   Secure file storage and Elasticsearch.
-   Add backups and monitoring.

## Security and reliability

-   Derive book ownership from the authenticated user; never trust a
    submitted student ID.
-   Verify ownership in Django before opening a book or chat session.
-   Filter every Elasticsearch search by the authenticated student's ID
    and, for Book Chat, the selected book ID.
-   Elasticsearch is a search index, not the authorization system.
-   Validate file contents, enforce file/page limits, consider malware
    scanning, and avoid public URLs for private PDFs.
-   When reprocessing or deleting a book, remove or update its old
    Elasticsearch documents. The initial Phase 2 implementation needs
    stale-index cleanup before repeated processing is safe.
-   SQLite transactions do not cover Elasticsearch writes. Add error
    handling and reconciliation for partial failures.
-   OCR accuracy varies by language, scan quality, and layout.
-   Do not deploy with `DEBUG=True`, development media serving, or an
    exposed Elasticsearch endpoint.
-   The textbook is the source of truth. If the authorized textbook does
    not support an answer, the system must say so rather than guess.

## Troubleshooting

### The empty path didn't match any URL patterns

Add a root URL pattern in `config/urls.py` (for example, redirect to the
dashboard) or open `/accounts/login/`.

### Elasticsearch connection refused

Start Elasticsearch and verify `ELASTICSEARCH_URL`, port, HTTPS, and
authentication settings.

### Tesseract executable not found

Install Tesseract and set `TESSERACT_CMD` to the correct executable path
or add it to `PATH`.

### OCR language data missing

Install the relevant Tesseract trained-data file and verify the language
code used by `pytesseract`.

### No readable text extracted

Check whether the PDF is damaged, empty, encrypted, or image-based.
Confirm that OCR and the appropriate language data are installed.

### Book processing failed but chunks exist

Text may have been saved to SQLite before Elasticsearch indexing failed.
Inspect both stores, repair Elasticsearch, and implement a safe
re-index/reconciliation process before retrying.

------------------------------------------------------------------------

**Core principle:** all retrieved content and future answers must come
only from the books the student is authorized to access, with page
references preserved from extraction through retrieval.
