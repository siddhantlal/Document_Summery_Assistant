# Copyright 2026 Document Summary Assistant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTTP routes and JSON response mapping for the Flask application."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, render_template
from flask import request
from werkzeug.exceptions import RequestEntityTooLarge

from document_summary_assistant.documents import extract_document
from document_summary_assistant.documents import ocr_available
from document_summary_assistant.errors import PublicError
from document_summary_assistant.summaries import generate_summary
from document_summary_assistant.summaries import is_configured
from document_summary_assistant.summaries import SUMMARY_LENGTHS


blueprint = Blueprint("web", __name__)


def error_response(
    code: str,
    message: str,
    status_code: int,
) -> tuple[Response, int]:
  """Create the stable public JSON error envelope."""

  return jsonify({"error": {"code": code, "message": message}}), status_code


@blueprint.get("/")
def index() -> str:
  """Render the upload interface."""

  return render_template("index.html")


@blueprint.get("/health")
def health() -> Response:
  """Report application and external dependency readiness."""

  return jsonify(
      {
          "status": "ok",
          "dependencies": {
              "gemini_configured": is_configured(),
              "ocr_available": ocr_available(),
          },
      }
  )


@blueprint.post("/api/summarize")
def summarize_document() -> Response | tuple[Response, int]:
  """Extract and summarize one uploaded document."""

  uploaded_file = request.files.get("document")
  if uploaded_file is None or not uploaded_file.filename:
    return error_response(
        "missing_document",
        "Choose a document to summarize.",
        400,
    )

  summary_length = request.form.get("length", "medium").strip().lower()
  if summary_length not in SUMMARY_LENGTHS:
    return error_response(
        "invalid_length",
        "Choose a short, medium, or long summary.",
        400,
    )

  try:
    extracted = extract_document(uploaded_file)
    generated = generate_summary(extracted.text, summary_length)
  except PublicError as exc:
    return error_response(exc.code, exc.message, exc.status_code)
  except Exception:
    current_app.logger.exception("Unexpected document summarization failure")
    return error_response(
        "internal_error",
        "The document could not be processed.",
        500,
    )

  return jsonify(
      {
          "summary": generated.summary,
          "key_points": generated.key_points,
          "metadata": {
              "filename": uploaded_file.filename,
              "file_type": extracted.file_type,
              "pages": extracted.pages,
              "characters_extracted": len(extracted.text),
              "summary_length": summary_length,
          },
      }
  )


def handle_large_upload(
    _error: RequestEntityTooLarge,
) -> tuple[Response, int]:
  """Map Flask's upload limit failure to the public error contract."""

  return error_response(
      "file_too_large",
      "Files are limited to 10 MB.",
      413,
  )
