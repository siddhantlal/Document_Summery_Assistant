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

"""Document validation, PDF extraction, and image OCR."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from document_summary_assistant.config import MAX_UPLOAD_BYTES
from document_summary_assistant.errors import DocumentProcessingError


MAX_PDF_PAGES = 50
MAX_EXTRACTED_CHARACTERS = 100_000
OCR_TIMEOUT_SECONDS = 45
SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg"})


@dataclass(frozen=True)
class ExtractedDocument:
  """Text and metadata extracted from an uploaded document."""

  text: str
  file_type: str
  pages: int | None


def ocr_available() -> bool:
  """Return whether the Tesseract executable is available on PATH."""

  return shutil.which("tesseract") is not None


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
    return _extract_pdf(data)
  return _extract_image(data, extension)


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


def _extract_pdf(data: bytes) -> ExtractedDocument:
  try:
    reader = PdfReader(io.BytesIO(data))
    is_encrypted = reader.is_encrypted
  except (PdfReadError, OSError, ValueError, KeyError, TypeError) as exc:
    raise DocumentProcessingError(
        "invalid_pdf",
        "The PDF is damaged or cannot be read.",
    ) from exc

  if is_encrypted:
    raise DocumentProcessingError(
        "encrypted_pdf",
        "Password-protected PDFs are not supported.",
    )

  try:
    page_count = len(reader.pages)
  except (PdfReadError, OSError, ValueError, KeyError, TypeError) as exc:
    raise DocumentProcessingError(
        "invalid_pdf",
        "The PDF is damaged or cannot be read.",
    ) from exc

  if page_count > MAX_PDF_PAGES:
    raise DocumentProcessingError(
        "pdf_too_long",
        f"PDFs are limited to {MAX_PDF_PAGES} pages.",
        413,
    )

  extracted_pages: list[str] = []
  character_count = 0
  for page_number, page in enumerate(reader.pages, start=1):
    try:
      page_text = (
          page.extract_text(extraction_mode="layout") or ""
      ).strip()
    except (PdfReadError, OSError, KeyError, TypeError, ValueError) as exc:
      raise DocumentProcessingError(
          "pdf_extraction_failed",
          "Text could not be extracted from this PDF.",
      ) from exc

    if not page_text:
      continue
    formatted_page = f"--- Page {page_number} ---\n{page_text}"
    character_count += len(formatted_page)
    if character_count > MAX_EXTRACTED_CHARACTERS:
      raise DocumentProcessingError(
          "document_too_long",
          "The extracted document exceeds the 100,000 character limit.",
          413,
      )
    extracted_pages.append(formatted_page)

  text = "\n\n".join(extracted_pages).strip()
  if not text:
    raise DocumentProcessingError(
        "scanned_pdf",
        "No selectable text was found. Upload scanned pages as PNG or JPEG "
        "images.",
    )

  return ExtractedDocument(text=text, file_type="pdf", pages=page_count)


def _extract_image(data: bytes, extension: str) -> ExtractedDocument:
  temporary_path: str | None = None
  try:
    with tempfile.NamedTemporaryFile(
        suffix=extension,
        delete=False,
    ) as temporary_file:
      temporary_file.write(data)
      temporary_path = temporary_file.name

    try:
      result = subprocess.run(
          [
              "tesseract",
              temporary_path,
              "stdout",
              "--psm",
              "3",
              "-l",
              "eng",
          ],
          capture_output=True,
          check=False,
          encoding="utf-8",
          errors="replace",
          shell=False,
          timeout=OCR_TIMEOUT_SECONDS,
      )
    except FileNotFoundError as exc:
      raise DocumentProcessingError(
          "ocr_unavailable",
          "OCR is unavailable on the server. Please try again later.",
          503,
      ) from exc
    except subprocess.TimeoutExpired as exc:
      raise DocumentProcessingError(
          "ocr_timeout",
          "OCR took too long. Try a smaller or clearer image.",
          504,
      ) from exc

    if result.returncode != 0:
      raise DocumentProcessingError(
          "ocr_failed",
          "Text could not be extracted from this image. Try a clearer scan.",
      )

    text = result.stdout.strip()
    if not text:
      raise DocumentProcessingError(
          "empty_extraction",
          "No readable text was found in this image. Try a clearer scan.",
      )
    if len(text) > MAX_EXTRACTED_CHARACTERS:
      raise DocumentProcessingError(
          "document_too_long",
          "The extracted document exceeds the 100,000 character limit.",
          413,
      )

    return ExtractedDocument(text=text, file_type="image", pages=None)
  except OSError as exc:
    raise DocumentProcessingError(
        "ocr_failed",
        "The image could not be prepared for OCR.",
    ) from exc
  finally:
    if temporary_path:
      Path(temporary_path).unlink(missing_ok=True)
