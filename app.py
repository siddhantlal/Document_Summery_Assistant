"""Flask entry point for the Document Summary Assistant."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from document_service import (
    DocumentProcessingError,
    extract_document,
    ocr_available,
)
from summary_service import SummaryServiceError, generate_summary, is_configured


def load_local_environment(path: str = ".env") -> None:
    """Load a simple local env file without adding a dotenv dependency."""

    env_path = Path(path)
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


load_local_environment()


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_LENGTHS = {"short", "medium", "long"}


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def error_response(code: str, message: str, status_code: int):
    return jsonify({"error": {"code": code, "message": message}}), status_code


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "dependencies": {
                "gemini_configured": is_configured(),
                "ocr_available": ocr_available(),
            },
        }
    )


@app.post("/api/summarize")
def summarize_document():
    uploaded_file = request.files.get("document")
    if uploaded_file is None or not uploaded_file.filename:
        return error_response(
            "missing_document", "Choose a document to summarize.", 400
        )

    summary_length = request.form.get("length", "medium").strip().lower()
    if summary_length not in ALLOWED_LENGTHS:
        return error_response(
            "invalid_length", "Choose a short, medium, or long summary.", 400
        )

    try:
        extracted = extract_document(uploaded_file)
        generated = generate_summary(extracted.text, summary_length)
    except (DocumentProcessingError, SummaryServiceError) as exc:
        return error_response(exc.code, exc.message, exc.status_code)
    except Exception:
        app.logger.exception("Unexpected document summarization failure")
        return error_response(
            "internal_error", "The document could not be processed.", 500
        )

    return jsonify(
        {
            "summary": generated["summary"],
            "key_points": generated["key_points"],
            "metadata": {
                "filename": uploaded_file.filename,
                "file_type": extracted.file_type,
                "pages": extracted.pages,
                "characters_extracted": len(extracted.text),
                "summary_length": summary_length,
            },
        }
    )


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error: RequestEntityTooLarge):
    return error_response(
        "file_too_large", "Files are limited to 10 MB.", 413
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
