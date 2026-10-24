# Project Setup Guide

This guide walks through installing and running StudyMate AI on Windows
using PowerShell. It is written for a fresh checkout. If you already have
the project and its virtual environment, skip to [Update an existing
checkout](#update-an-existing-checkout).

## What you need

- Windows 10 or 11.
- Python 3.12 (64-bit) and Git.
- Internet access to install Python packages and download the embedding
  model on first use.
- Enough free disk space for Python packages, the sentence-transformer
  model cache, and uploaded PDFs.
- Tesseract OCR only if you need to process scanned/image-based PDF pages.
- NVIDIA API credentials only if you want generated explanations. The app
  can start without them; local search still requires the embedding model.

> Run all commands below in PowerShell, from the directory where you want
> the project folder created. Do not delete `db.sqlite3` or `media/` when
> updating an existing installation; they contain application data.

## 1. Get the source code

If Git is installed:

```powershell
git clone https://github.com/VishwaDax/Student-friendly.git
Set-Location .\Student-friendly
```

For an existing clone, navigate to its root directory (the folder containing
`manage.py`) instead.

Confirm Python and Git are available:

```powershell
python --version
git --version
```

The project was developed with Python 3.12. If `python` is not recognized
or launches a different Python version, install Python 3.12 and reopen
PowerShell.

## 2. Create a virtual environment and install packages

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands use the virtual environment's Python directly, so PowerShell
script activation settings do not need to be changed.

Optionally activate the environment for shorter commands:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, continue using
`.\venv\Scripts\python.exe` in place of `python`.

The `sentence-transformers` dependency installs the local embedding stack.
The model weights are downloaded separately the first time embeddings are
generated, which may take several minutes and require additional disk
space. The Windows Hugging Face symlink warning is informational; caching
continues to work without symlinks.

## 3. Create local configuration

Create `.env` from the safe sample if it does not already exist:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

The supplied sample uses Django's console email backend, so local signup
verification codes appear in the PowerShell window running the server. No
SMTP credentials are needed for local development. No NVIDIA key is needed
to start the site. To enable generated answers, edit `.env` and set an
NVIDIA API key and an account-enabled model:

```dotenv
NVIDIA_API_KEY=your_actual_key
NVIDIA_MODEL=your_enabled_model_id
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_TIMEOUT_SECONDS=45
NVIDIA_MAX_RETRIES=2
TEXTBOOK_MIN_EVIDENCE_SCORE=0.015
```

Replace the sample values locally. Never commit `.env` or put credentials
in `.env.example`, source code, browser code, screenshots, or issue reports.
Restart the Django server after changing environment variables.

### Email verification and email delivery

New accounts must verify their email before logging in. The signup flow is:

1. Submit the student registration form with a valid email address.
2. The app creates an inactive account and sends a random six-digit OTP.
3. Enter that code on the verification screen in the same browser session.
4. A correct code activates the account; log in using either username or
   email.

The code expires after 10 minutes, allows at most five incorrect attempts,
and is stored as a password hash. Resend requests are limited to one every
60 seconds. The code must be entered in the browser session that requested
it; verification is not a clickable link. The resend response is generic
for privacy, so it does not disclose whether an account exists.

With the sample console backend, read the OTP in the terminal running
`runserver`. For actual email delivery, configure SMTP settings in `.env`
using credentials from your email provider:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=StudyMate AI <noreply@example.com>
```

Use the provider's supported SMTP host, port, TLS mode, and sender address.
Keep the SMTP password secret. Restart the server after changing `.env`.
The SMTP backend only works when the host, username, password, and sender
are valid for your email provider. If signup reports a delivery error,
check the Django terminal and the local settings, or temporarily switch
`EMAIL_BACKEND` back to
`django.core.mail.backends.console.EmailBackend`.

After applying the email-verification migrations, existing accounts also
need to verify their registered address before logging in. From the login
page, use **Resend verification code** and enter the resulting code in that
same browser session.

## 4. Set up OCR (optional for text-based PDFs)

Text-based PDFs can be processed without OCR. For scanned PDFs, install
Tesseract OCR and its language data. The default executable location in
`config/settings.py` is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract is installed elsewhere, update `TESSERACT_CMD` in
`config/settings.py` to the actual executable path.

Extra trained data is read from `media/tessdata` by default. For example,
to enable Tamil OCR, open PowerShell from the project root and run:

```powershell
New-Item -ItemType Directory -Force .\media\tessdata
Copy-Item "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" .\media\tessdata\
Copy-Item "C:\Program Files\Tesseract-OCR\tessdata\osd.traineddata" .\media\tessdata\
Invoke-WebRequest `
    -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/tam.traineddata" `
    -OutFile ".\media\tessdata\tam.traineddata"
```

The application language name is mapped to a Tesseract language code in
`textbooks/services/pdf_processor.py`; install the matching
`<code>.traineddata` file for every scanned language you intend to process.
OCR is not required just to start Django or to use existing, already
processed text passages.

## 5. Check SQLite FTS5

The active Python's SQLite must include FTS5:

```powershell
.\venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect(':memory:'); c.execute('CREATE VIRTUAL TABLE f USING fts5(content)'); print('SQLite', sqlite3.sqlite_version, '- FTS5 available')"
```

Successful output ends with `FTS5 available`. If this command fails, use a
Python distribution whose SQLite build includes FTS5 before continuing.

## 6. Apply database migrations

Run the project checks and migrations:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py migrate
```

The project configures its custom student account model in
`config/settings.py` and uses `db.sqlite3` in the repository root. Django
creates the database file when needed. For an existing installation,
`migrate` applies pending schema updates without intentionally removing
student or textbook records.

Do not remove or replace an existing `db.sqlite3` as a way to fix a
migration error. Back up the database before maintenance, and diagnose
migration failures from their complete error output.

## 7. Start the site

```powershell
.\venv\Scripts\python.exe manage.py runserver
```

Keep that PowerShell window open while using the application. Visit:

```text
http://127.0.0.1:8000/
```

The home URL redirects to the dashboard. For a new local installation,
create a student through the signup page:

```text
http://127.0.0.1:8000/accounts/signup/
```

After signup, enter the OTP sent to the account email (or printed in the
server terminal when using the console backend). Once verified, sign in at
`/accounts/login/` with the username or email address. The dashboard is at
`/accounts/dashboard/`; upload a book at `/textbooks/upload/`, or open Main
Room at `/textbooks/main-room/`.

No administrator account is required for the normal student workflow. To
use Django's admin site, stop the development server with `Ctrl+C`, then
create an admin account:

```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

Restart the server and visit `http://127.0.0.1:8000/admin/`.
New superuser accounts also require a verified email. With the server
running, use **Resend verification code** on the login page, enter the
superuser email, and complete OTP verification in that browser session
before signing in to Django admin.

## 8. Verify local embeddings

The first book upload needs the embedding model. To download and test it
before uploading a textbook, run:

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from textbooks.services.embeddings import encode_texts; vector = encode_texts(['StudyMate setup check'])[0]; print('Embedding dimensions:', len(vector))"
```

The expected output is `Embedding dimensions: 384`. The model is cached
locally for later runs. An internet connection is required for its initial
download.

## 9. Upload and search a textbook

1. Sign in as a student.
2. Open **Upload textbook** from the dashboard.
3. Select a PDF no larger than 100 MB and fill in the book details.
4. Keep the browser page open while processing completes. Extraction,
   optional OCR, passage chunking, and embedding run synchronously.
5. When the book status becomes **Ready**, open its Book Chat or ask about
   the student's ready books in Main Room.

Generated NVIDIA answers require valid API configuration. Without it, local
indexing and retrieval can still run; no external language model is used by
the search service itself.

## Update an existing checkout

From the project root:

```powershell
git pull
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py migrate
```

If dependencies have changed, pip installs or updates the declared
packages. Migrations update the existing schema. Do not remove `db.sqlite3`
or `media/`; back up both before any maintenance that could affect user
data.

If a model or search index needs rebuilding, run:

```powershell
.\venv\Scripts\python.exe manage.py reindex_books
```

This requires the uploaded PDFs to remain available in `media/` and may
take a long time because PDFs and embeddings are processed locally.

## Run project checks

Stop the web server with `Ctrl+C`, then run:

```powershell
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

## Common setup problems

### `No module named django`

Use the project virtual environment's Python and install requirements:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### `no such column: textbooks_bookchunk.embedding`

Apply pending migrations:

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

Do not solve a missing column by deleting the database.

### The first upload takes a long time or fails downloading a model

The multilingual embedding model is downloaded on first use. Check network
access, available disk space, and the server terminal for the error. Retry
after the download succeeds.

### Scanned PDF processing fails

Check the server terminal. Confirm `TESSERACT_CMD` points to the installed
executable and that the corresponding language `.traineddata` file is
available under `media/tessdata` (or the configured `TESSERACT_DATA_DIR`).

### NVIDIA answer is unavailable

Check that `.env` contains a valid `NVIDIA_API_KEY` and an enabled
`NVIDIA_MODEL`; restart Django after editing the file. Provider
configuration is optional for running the site and performing local
retrieval.

### Email verification code is missing

With the supplied `.env.example`, the code is printed in the PowerShell
window running Django. If SMTP is enabled, confirm `.env` contains valid
provider credentials and a sender address allowed by that provider, then
restart the server. Existing unverified accounts can request a code from
the login page.

### Verification code is rejected or expired

Use the newest code in the same browser session that requested it. Codes
expire after 10 minutes; only five incorrect attempts are allowed, and a
new code can be requested once per minute. Request a replacement code and
try again.

### Port 8000 is already in use

Run the server on another port:

```powershell
.\venv\Scripts\python.exe manage.py runserver 8001
```

Then open `http://127.0.0.1:8001/`.

## Before deployment

The current settings are for local development, not public hosting. Before
deployment, configure a unique secret key, `DEBUG=False`, allowed hosts,
HTTPS and secure cookies, persistent backups, private media storage, and
production logging. PDF processing currently runs in the web request, so
large uploads can take a long time; no background worker is configured.
Review the README's production notes before exposing the application.
