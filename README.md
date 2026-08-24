# Briefly — Document Summary Assistant

Briefly converts text-based PDFs and scanned PNG/JPEG images into a concise
summary and a length-appropriate list of key points. It uses layout-aware PDF
extraction, local Tesseract OCR, and Gemini for summary generation.

## Features

- Drag-and-drop or file-picker uploads
- PDF extraction with page and line layout retained
- English OCR for PNG and JPEG scans
- Short, medium, and long summaries
- Structured key points, copy support, loading states, and actionable errors
- Responsive, keyboard-accessible interface
- Temporary processing only; uploaded content is not stored

## Minimal dependency design

The only Python runtime packages are Flask, pypdf, and gunicorn. Tesseract is
called directly through Python's standard library, and Gemini is called with
`urllib`, avoiding OCR wrappers, AI SDKs, HTTP clients, databases, frontend
frameworks, and npm tooling.

## Requirements

- Python 3.10 or newer for local development (Docker uses Python 3.12)
- Tesseract OCR with the English language data
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/)

Install Tesseract separately and ensure `tesseract --version` works in your
terminal. The Docker image installs it automatically.

## Local setup

Create and activate a virtual environment, then install the pinned packages:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
```

Set the environment variables. PowerShell example:

```powershell
Copy-Item .env.example .env
# Edit .env and replace the placeholder with your real key.
python -m app
```

Open `http://localhost:5000`. The app loads `.env` without an extra package and
never overrides values already supplied by the shell or hosting platform. The
model remains configurable without modifying source code.

## Docker

```bash
docker build -t document-summary-assistant .
docker run --rm -p 5000:5000 -e PORT=5000 -e GEMINI_API_KEY=your-key document-summary-assistant
```

Check the service and its dependencies at `http://localhost:5000/health`.

## API

`POST /api/summarize` accepts `multipart/form-data`:

- `document`: a PDF, PNG, JPG, or JPEG
- `length`: `short`, `medium`, or `long`

Example success response:

```json
{
  "summary": "A concise summary.",
  "key_points": ["First point", "Second point", "Third point"],
  "metadata": {
    "filename": "document.pdf",
    "file_type": "pdf",
    "pages": 2,
    "characters_extracted": 8400,
    "summary_length": "short"
  }
}
```

Errors use `{ "error": { "code": "...", "message": "..." } }` with an
appropriate HTTP status.

## Limits and known constraints

- Maximum upload: 10 MB
- Maximum PDF length: 50 pages
- Maximum extracted text: 100,000 characters
- OCR language: English
- Scanned/image-only PDFs are not OCRed; upload the pages as PNG or JPEG
- Password-protected PDFs and batch uploads are not supported
- PDF formatting means page boundaries, spacing, and approximate line layout;
  typography and visual table structure are not recreated

## Tests

The test suite uses the standard library and mocks external OCR/API calls:

```bash
python -m unittest discover -s tests
```

## Project structure

The application is organized as one self-contained Python package. The root
entry point only loads local configuration, creates the Flask application, and
starts the development server.

```text
document_summary_assistant/
  __init__.py    Flask application factory
  config.py      Runtime configuration and local environment loading
  documents.py   Upload validation, PDF extraction, and image OCR
  errors.py      Safe errors shared across service boundaries
  summaries.py   Gemini request construction and response validation
  web.py         HTTP routes and JSON response mapping
  static/        Browser behavior and styling
  templates/     Flask page templates
tests/           Focused unit and HTTP contract tests
app.py           Thin WSGI and local development entry point
```

Internal imports use the `document_summary_assistant` package name. Domain
services remain callable independently of Flask, while the web module owns only
request validation and response mapping.

Before release, also upload a text PDF and readable PNG/JPEG scan, exercise all
three summary lengths, and confirm no temporary upload remains after processing.

## Deploy to Render

1. Push the repository to GitHub.
2. Create a Render **Web Service** and choose the **Docker** runtime.
3. Set `GEMINI_API_KEY` as a secret and optionally set `GEMINI_MODEL`.
4. Set the health-check path to `/health` and deploy.
5. Test the public URL with one PDF and one scanned image.

No persistent disk is required. The container listens on Render's `PORT` and
installs Tesseract during the image build.

## Approach write-up (under 200 words)

I chose a small Flask application with a vanilla frontend to keep the solution
easy to review, deploy, and maintain within the assessment's eight-hour limit.
The server validates both file extensions and byte signatures before processing.
Text-based PDFs are parsed with pypdf in layout mode, while PNG and JPEG scans
are passed directly to the Tesseract executable. Temporary image files are
always deleted, including after failures.

Summary generation uses Gemini's REST API through Python's standard library,
which keeps the API key on the server and avoids a provider SDK. The model is
asked for schema-constrained JSON containing a faithful summary and a fixed
number of key points based on the selected length. Uploaded text is explicitly
treated as untrusted content to reduce prompt-injection risk.

The interface uses no frontend framework but includes drag-and-drop, clear
loading and error states, keyboard navigation, responsive styling, and copy/reset
actions. Unit tests mock external services and cover validation, extraction,
cleanup, API contracts, and provider failures. Docker supplies the only native
dependency, Tesseract, so local and hosted behavior remain consistent.
