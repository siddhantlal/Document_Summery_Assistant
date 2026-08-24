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

"""Document upload validation and extractor selection."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from document_summary_assistant.config import MAX_UPLOAD_BYTES
from document_summary_assistant.documents.image import extract_image
from document_summary_assistant.documents.models import ExtractedDocument
from document_summary_assistant.documents.pdf import extract_pdf
from document_summary_assistant.errors import DocumentProcessingError


SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg"})


def extract_document(uploaded_file: object) -> ExtractedDocument:
  """Validate and extract text from a Flask-compatible uploaded file.

  Args:
    uploaded_file: Object with a filename and a binary stream or read method.

  Returns:
    Extracted text and stable document metadata.

  Raises:
    DocumentProcessingError: If validation or extraction fails.
  """

  filename = str(getattr(uploaded_file, "filename", "") or "")
  extension = Path(filename).suffix.lower()
  stream = getattr(uploaded_file, "stream", uploaded_file)

  if extension not in SUPPORTED_EXTENSIONS:
    raise DocumentProcessingError(
        "unsupported_file",
        "Upload a PDF, PNG, or JPEG file.",
        400,
    )

  data = _read_upload(stream)
  if not data:
    raise DocumentProcessingError(
        "empty_file",
        "The uploaded file is empty.",
        400,
    )

  detected_type = _detect_file_type(data)
  expected_type = "jpeg" if extension in {".jpg", ".jpeg"} else extension[1:]
  if detected_type != expected_type:
    raise DocumentProcessingError(
        "invalid_file",
        "The file contents do not match its extension.",
        400,
    )

  if detected_type == "pdf":
    return extract_pdf(data)
  return extract_image(data, extension)


def _read_upload(stream: BinaryIO) -> bytes:
  try:
    data = stream.read(MAX_UPLOAD_BYTES + 1)
  except (AttributeError, OSError, TypeError) as exc:
    raise DocumentProcessingError(
        "invalid_file",
        "The uploaded file could not be read.",
        400,
    ) from exc

  if not isinstance(data, bytes):
    raise DocumentProcessingError(
        "invalid_file",
        "The uploaded file must contain binary data.",
        400,
    )
  if len(data) > MAX_UPLOAD_BYTES:
    raise DocumentProcessingError(
        "file_too_large",
        "Files are limited to 10 MB.",
        413,
    )
  return data


def _detect_file_type(data: bytes) -> str | None:
  if b"%PDF-" in data[:1024]:
    return "pdf"
  if data.startswith(b"\x89PNG\r\n\x1a\n"):
    return "png"
  if data.startswith(b"\xff\xd8\xff"):
    return "jpeg"
  return None
