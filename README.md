# StudyMate AI

StudyMate AI is a Django web application for building a private library of
school textbooks and asking questions grounded in their pages. Students can
register, upload PDF textbooks, search a selected book or their own ready
books, and remove books they no longer need.

The application uses Django and SQLite for accounts, books, extracted
passages, and chat history. Retrieval is local: SQLite FTS5 keyword search
and Python cosine similarity over local sentence-transformer embeddings
are combined with Reciprocal Rank Fusion (RRF). An optional NVIDIA-hosted
chat-completions model can explain retrieved evidence. It does not use
Elasticsearch, Ollama, or a locally hosted generative model.

## Contents

- [Project setup guide](SETUP.md)
- [Features and user flows](#features-and-user-flows)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Install and run on Windows](#install-and-run-on-windows)
- [Configuration](#configuration)
- [How textbook processing works](#how-textbook-processing-works)
- [Search, answers, and privacy](#search-answers-and-privacy)
- [Reindex existing books](#reindex-existing-books)
- [Tests and checks](#tests-and-checks)
- [Troubleshooting](#troubleshooting)
- [Production notes](#production-notes)

## Features and user flows

### Accounts and library

- Student signup with username, email, age, class, and preferred language.
- Login and logout using the custom `accounts.Student` user model.
- A dashboard showing each student's own books and their processing status.
- A mobile-responsive interface with upload/search progress feedback.
- A confirmed, owner-scoped delete action. Deleting a book removes its
  database record, passages and embeddings, topics, related chat sessions
  and messages, FTS entries, and stored PDF file.

### Upload and processing

1. A logged-in student uploads a PDF and enters its title, language, class,
   and subject.
2. The server validates the `.pdf` extension, PDF signature, and 100 MB
   maximum file size. Ownership is assigned from the authenticated user,
   not from submitted form data.
3. PyMuPDF extracts each page. Tesseract OCR is used when a page has fewer
   than 40 selectable text characters.
4. Page text is split into overlapping passages. Each passage retains its
   original one-based PDF page number.
5. The local multilingual sentence-transformer creates normalized
   384-dimensional embeddings. Passages and embeddings are saved in SQLite
   and synchronized with the FTS5 index.
6. A heuristic scans passages for likely chapter and topic headings.
   Processing runs synchronously in the web request; large PDFs can take a
   while. The interface displays a progress overlay while the request is
   running.

Books have `uploaded`, `processing`, `ready`, and `failed` statuses. Only
ready books are available in normal chat/search.

### Book Chat and Main Room

- **Book Chat** searches only the selected ready book, and only if that
  book belongs to the logged-in student.
- **Main Room** searches all ready books owned by the logged-in student.
- Search combines FTS5 BM25 keyword ranking and local semantic ranking
  with RRF.
- If no passages meet the configured evidence threshold, the app abstains
  without calling NVIDIA.
- When configured, NVIDIA receives the current question, preferred answer
  language, and a bounded selection of authorized passages. Chat history
  remains in SQLite and is not sent as additional model context.
- Factual sentences must cite IDs from the supplied passages. Source title
  and page details displayed in the UI come from retrieved database records.
- Generated answers are not guaranteed correct; students should check the
  cited textbook pages.

## Project structure

```text
Student-friendly/
├── manage.py
├── db.sqlite3                      # Local Django SQLite database
├── .env.example                    # Safe configuration template
├── requirements.txt
├── public/
│   └── Logo.png                    # Original supplied logo
├── config/
│   ├── settings.py                 # Django, SQLite, OCR, search, NVIDIA settings
│   └── urls.py                     # Root URLs and development media serving
├── accounts/
│   ├── models.py                   # Custom Student user
│   ├── forms.py                    # Signup form
│   ├── views.py                    # Signup, login, dashboard
│   ├── urls.py
│   ├── templates/accounts/         # Shared layout, auth, dashboard
│   ├── static/accounts/            # CSS, responsive navigation, logo assets
│   └── migrations/
├── textbooks/
│   ├── models.py                   # Book, BookChunk, Topic
│   ├── forms.py                    # PDF validation
│   ├── views.py                    # Upload, deletion, Book Chat, Main Room
│   ├── signals.py                  # Keep FTS synchronized with chunks/books
│   ├── services/
│   │   ├── embeddings.py           # Local sentence-transformer embeddings
│   │   ├── llm_service.py          # NVIDIA hosted chat-completions adapter
│   │   ├── local_search.py         # FTS5, semantic search, RRF
│   │   ├── passage_chunker.py      # Overlapping page passage splitting
│   │   ├── pdf_processor.py        # PyMuPDF extraction and Tesseract OCR
│   │   └── topic_detector.py       # Heading/topic heuristics
│   ├── management/commands/
│   │   └── reindex_books.py        # Rebuild embeddings and FTS entries
│   ├── templates/textbooks/        # Upload, Book Chat, Main Room
│   └── migrations/
└── conversations/
    ├── models.py                   # ChatSession and ChatMessage
    ├── views.py
    ├── urls.py
    └── migrations/
```

Uploaded PDFs are stored under `media/textbooks/`. Additional Tesseract
language data can be stored in `media/tessdata/`. The `media/` directory and
SQLite database are local data; do not delete them as a routine setup step.

## Requirements

- Python 3.12 is the version used for this project environment.
- SQLite built with FTS5 support.
- Packages listed in `requirements.txt`.
- Internet access the first time the embedding model is downloaded.
- Tesseract OCR installed separately when PDFs include scanned/image pages.
- Tesseract trained data for the languages of scanned pages.
- NVIDIA API key and an account-enabled chat-completions model if generated
  explanations are required. Local search and passage retrieval work
  without NVIDIA credentials.

The interface and embedding model are intended for multilingual material,
but OCR quality, retrieval quality, and generated-answer quality have not
been evaluated for every language in the language list. A language choice
is not a guarantee of language-specific accuracy.

## Install and run on Windows

Run these commands from the repository root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` locally if you want NVIDIA answers; see
[Configuration](#configuration). Do not put a real key in `.env.example`,
Python source, templates, JavaScript, or Git.

### Initialize or update the database

For a new database, configure `AUTH_USER_MODEL = "accounts.Student"` before
the first migration, then run:

```powershell
python manage.py check
python manage.py migrate
```

For an existing database, keep the database and its records. Apply pending
migrations with `python manage.py migrate`; do not delete or replace
`db.sqlite3` to resolve a migration error. If migration reports an integrity
or foreign-key problem, inspect and resolve the underlying data issue before
retrying.

Create an administrator account if needed:

```powershell
python manage.py createsuperuser
```

Start the development server:

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The root URL redirects to the dashboard,
which requires login.

| Page | URL |
| --- | --- |
| Signup | `http://127.0.0.1:8000/accounts/signup/` |
| Login | `http://127.0.0.1:8000/accounts/login/` |
| Dashboard | `http://127.0.0.1:8000/accounts/dashboard/` |
| Upload textbook | `http://127.0.0.1:8000/textbooks/upload/` |
| Main Room | `http://127.0.0.1:8000/textbooks/main-room/` |
| Django admin | `http://127.0.0.1:8000/admin/` |

In development, Django serves media files from `MEDIA_ROOT`. Production
deployments need an appropriate private media-serving configuration.

## Configuration

### Environment variables

Copy `.env.example` to `.env`; `.env` is ignored by Git. `python-dotenv`
loads it when Django starts.

| Variable | Purpose | Default |
| --- | --- | --- |
| `NVIDIA_API_KEY` | Server-side NVIDIA credential | Empty (answers unavailable) |
| `NVIDIA_MODEL` | Exact chat model enabled for the NVIDIA account | Empty (answers unavailable) |
| `NVIDIA_BASE_URL` | OpenAI-compatible NVIDIA API base URL | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_TIMEOUT_SECONDS` | Provider request timeout; valid range 1–120 | `45` |
| `NVIDIA_MAX_RETRIES` | SDK retry limit; valid range 0–3 | `2` |
| `TEXTBOOK_MIN_EVIDENCE_SCORE` | Minimum RRF score for sending evidence to generation | `0.015` |
| `TESSERACT_DATA_DIR` | Additional OCR trained-data directory | `media/tessdata` |

The evidence-score default is provisional, not calibrated against a
representative evaluation set. Change it only after measuring retrieval on
known questions and supporting pages.

NVIDIA model IDs and account access can change. Select a model enabled for
your account in NVIDIA API Catalog. Provider errors such as missing
credentials, access restrictions, model unavailability, rate limits, or
outages are converted to safe user-facing messages. Never share the API key
or include it in logs or screenshots.

The NVIDIA call is server-side. It sends only a question, a preferred
response-language instruction, and a small bounded set of relevant
passages (up to six, subject to a context character limit). Review NVIDIA's
current privacy, retention, and service terms before sending student
questions or textbook passages to a hosted API.

### Embedding and passage settings

The model and processing defaults are in `config/settings.py`:

- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Embedding dimensions: 384
- Passage size: 1,200 characters
- Passage overlap: 200 characters
- Minimum cosine similarity: 0.35

The first embedding operation downloads the model to the local Hugging Face
cache. On Windows, Hugging Face may warn that symlinks are unavailable; the
cache still works but can use more disk space.

### Tesseract OCR

`TESSERACT_CMD` in `config/settings.py` points to the default Windows
installation. Update it if Tesseract is installed elsewhere. Scanned pages
use the corresponding Tesseract language code. Additional trained data is
read from `TESSERACT_DATA_DIR` (default `media/tessdata`); it is not bundled
with the Python package.

For Tamil OCR with the default data directory:

```powershell
New-Item -ItemType Directory -Force .\media\tessdata
Copy-Item "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" .\media\tessdata\
Copy-Item "C:\Program Files\Tesseract-OCR\tessdata\osd.traineddata" .\media\tessdata\
Invoke-WebRequest `
    -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/tam.traineddata" `
    -OutFile ".\media\tessdata\tam.traineddata"
```

Install the matching `<language-code>.traineddata` file for other scanned
languages. Confirm installed data with:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" `
    --tessdata-dir (Resolve-Path .\media\tessdata).Path `
    --list-langs
```

## How textbook processing works

The processing request is synchronous: the browser remains on the upload
page while Django extracts pages, performs OCR when needed, creates
embeddings, saves passages, updates FTS5, and detects likely headings.
Larger PDFs may take several minutes. The UI shows a progress overlay, but
this is not background processing and closing the request can interrupt
user feedback.

Book processing replaces its existing chunks only after extraction and
embeddings have completed. This avoids discarding a previous successful
index if a reprocessing attempt fails before replacement.

## Search, answers, and privacy

- SQLite is the system of record. FTS5 is a rebuildable keyword index.
- FTS5 uses BM25 ranking; semantic ranking compares normalized local
  embeddings with cosine similarity; RRF merges the ranked lists.
- Only ready books are searched. Book Chat verifies ownership and selected
  book scope; Main Room filters by the authenticated student's ownership.
- Search results are checked against the database before returning passages.
- Empty or below-threshold evidence does not invoke NVIDIA; the app returns
  an abstention instead.
- NVIDIA receives only retrieved passages, not the student's whole library
  or previous chat history.
- Citation IDs are checked against passages supplied for the request.
  Citations help trace the response but do not independently prove that
  every generated statement is correct.
- Deleting a book from the dashboard requires confirmation and removes its
  associated database records, FTS search entries, and stored PDF.

## Reindex existing books

After installing the embedding dependencies and ensuring the required PDFs
are present under `MEDIA_ROOT`, rebuild the local index with:

```powershell
python manage.py reindex_books
```

The command processes available PDFs, regenerates passage embeddings,
updates topics, indexes legacy chunks when a PDF is unavailable, and
rebuilds the FTS5 index. It reports successes and failures and exits with an
error if any books fail. Existing chunks are retained when PDF processing
fails before replacement. The command does not create students or repair
book ownership.

Run `reindex_books` after changing the embedding model or when repairing a
missing/stale FTS index. All embeddings being compared must come from the
same configured embedding model.

## Tests and checks

Run the complete Django test suite and project checks:

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Tests cover PDF text extraction and OCR fallback, chunking and embeddings,
FTS5/semantic/hybrid ranking, owner-scoped Book Chat and Main Room behavior,
NVIDIA error/citation handling, and reindex behavior. Provider tests mock
NVIDIA requests; they do not require a live API key or incur provider cost.

Check that SQLite FTS5 is available in the active Python:

```powershell
python -c "import sqlite3; c=sqlite3.connect(':memory:'); c.execute('CREATE VIRTUAL TABLE f USING fts5(content)'); print('SQLite', sqlite3.sqlite_version, 'FTS5 available')"
```

## Troubleshooting

### `no such column: textbooks_bookchunk.embedding`

Apply the project's pending migrations:

```powershell
python manage.py migrate
```

Do not reset the database to fix a missing column. If migration fails, read
the complete error and inspect the affected existing data first.

### PDF upload says “Book processing failed”

Read the Django server terminal traceback. Common causes include a missing
embedding package/model download, unavailable SQLite FTS5, invalid or
damaged PDFs, and missing Tesseract executable or language data. Confirm
that the selected Tesseract language is installed, then retry. Failed books
remain visible in the dashboard and can be deleted or uploaded again.

### Tesseract cannot find a language

Install its `<code>.traineddata` file into the configured data directory and
check `tesseract --list-langs`. For Tamil, use `tam.traineddata`. OCR
accuracy depends on page quality and is not guaranteed.

### Embedding model download or Hugging Face cache warning

The first embedding use requires downloading the model. Allow it to finish
and ensure there is enough disk space. The Windows symlink warning is
non-fatal; Developer Mode can enable symlinks, but is not required.

### NVIDIA answer is unavailable

Check that `.env` contains a valid `NVIDIA_API_KEY` and an exact,
account-enabled `NVIDIA_MODEL`. Restart the Django server after changing
`.env`. Search remains local if NVIDIA is unconfigured or unavailable.

### Search returns no passages

Confirm the book status is `ready`, the PDF produced readable passages,
and the question relates to indexed content. The evidence threshold is
provisional and can exclude weak matches. Rebuild local entries with
`python manage.py reindex_books` if you suspect the index is stale.

## Production notes

`config/settings.py` currently contains development-oriented settings.
Before deployment:

- Replace the hard-coded development `SECRET_KEY` with a secure environment
  value and set `DEBUG=False`.
- Configure `ALLOWED_HOSTS`, HTTPS, secure cookies, CSRF trusted origins,
  logging, and an appropriate email backend.
- Protect uploaded PDFs with private storage and backups; do not expose
  student files through public static hosting.
- Move long PDF processing to a background worker if request duration is
  unsuitable for deployment. No background job system is currently
  configured.
- Monitor storage, database backups, OCR quality, retrieval quality,
  provider latency/cost, and rate limits.
- Review data-protection and provider-retention requirements before sending
  student or textbook data to NVIDIA.

The repository's local SQLite database and `media/` contain application
data. Back them up before maintenance; never delete them as a general
troubleshooting step.
