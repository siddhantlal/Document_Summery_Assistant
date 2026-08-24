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

"""OCR extraction from validated image documents."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from document_summary_assistant.documents.models import ExtractedDocument
from document_summary_assistant.errors import DocumentProcessingError


MAX_EXTRACTED_CHARACTERS = 100_000
OCR_TIMEOUT_SECONDS = 45


def ocr_available() -> bool:
  """Return whether the Tesseract executable is available on PATH."""

  return shutil.which("tesseract") is not None


def extract_image(data: bytes, extension: str) -> ExtractedDocument:
  """Extract English text from validated image bytes using Tesseract."""

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
