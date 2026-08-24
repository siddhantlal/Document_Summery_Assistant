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

"""Text extraction from PDF documents."""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from document_summary_assistant.documents.models import ExtractedDocument
from document_summary_assistant.errors import DocumentProcessingError


MAX_PDF_PAGES = 50
MAX_EXTRACTED_CHARACTERS = 100_000


def extract_pdf(data: bytes) -> ExtractedDocument:
  """Extract layout-aware text from validated PDF bytes."""

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
