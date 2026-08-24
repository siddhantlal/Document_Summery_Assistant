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

"""Tests for PDF text extraction."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from document_summary_assistant.documents import pdf
from document_summary_assistant.documents.pdf import extract_pdf
from document_summary_assistant.errors import DocumentProcessingError


class PdfExtractionTest(unittest.TestCase):
  @patch("document_summary_assistant.documents.pdf.PdfReader")
  def test_extraction_preserves_page_markers_and_layout(
      self,
      reader_mock,
  ) -> None:
    first_page = MagicMock()
    first_page.extract_text.return_value = "Heading\n  aligned text"
    second_page = MagicMock()
    second_page.extract_text.return_value = "Conclusion"
    reader_mock.return_value = SimpleNamespace(
        is_encrypted=False,
        pages=[first_page, second_page],
    )

    result = extract_pdf(b"%PDF-1.7\ncontent")

    self.assertEqual(result.file_type, "pdf")
    self.assertEqual(result.pages, 2)
    self.assertIn("--- Page 1 ---\nHeading\n  aligned text", result.text)
    self.assertIn("--- Page 2 ---\nConclusion", result.text)
    first_page.extract_text.assert_called_once_with(extraction_mode="layout")

  @patch("document_summary_assistant.documents.pdf.PdfReader")
  def test_encrypted_pdf_is_rejected(self, reader_mock) -> None:
    reader_mock.return_value = SimpleNamespace(is_encrypted=True, pages=[])

    with self.assertRaises(DocumentProcessingError) as context:
      extract_pdf(b"%PDF-1.7")

    self.assertEqual(context.exception.code, "encrypted_pdf")

  @patch("document_summary_assistant.documents.pdf.PdfReader")
  def test_lazy_parse_failure_has_safe_error(self, reader_mock) -> None:
    class BrokenReader:
      is_encrypted = False

      @property
      def pages(self):
        raise pdf.PdfReadError("broken page tree")

    reader_mock.return_value = BrokenReader()

    with self.assertRaises(DocumentProcessingError) as context:
      extract_pdf(b"%PDF-1.7")

    self.assertEqual(context.exception.code, "invalid_pdf")

  @patch("document_summary_assistant.documents.pdf.PdfReader")
  def test_page_limit_is_enforced(self, reader_mock) -> None:
    reader_mock.return_value = SimpleNamespace(
        is_encrypted=False,
        pages=[MagicMock() for _ in range(pdf.MAX_PDF_PAGES + 1)],
    )

    with self.assertRaises(DocumentProcessingError) as context:
      extract_pdf(b"%PDF-1.7")

    self.assertEqual(context.exception.code, "pdf_too_long")
    self.assertEqual(context.exception.status_code, 413)

  @patch("document_summary_assistant.documents.pdf.PdfReader")
  def test_image_only_pdf_has_actionable_error(self, reader_mock) -> None:
    page = MagicMock()
    page.extract_text.return_value = ""
    reader_mock.return_value = SimpleNamespace(
        is_encrypted=False,
        pages=[page],
    )

    with self.assertRaises(DocumentProcessingError) as context:
      extract_pdf(b"%PDF-1.7")

    self.assertEqual(context.exception.code, "scanned_pdf")

  @patch("document_summary_assistant.documents.pdf.PdfReader")
  def test_extracted_character_limit_is_enforced(self, reader_mock) -> None:
    page = MagicMock()
    page.extract_text.return_value = "x" * 100
    reader_mock.return_value = SimpleNamespace(
        is_encrypted=False,
        pages=[page],
    )

    with patch(
        "document_summary_assistant.documents.pdf."
        "MAX_EXTRACTED_CHARACTERS",
        20,
    ):
      with self.assertRaises(DocumentProcessingError) as context:
        extract_pdf(b"%PDF-1.7")

    self.assertEqual(context.exception.code, "document_too_long")


if __name__ == "__main__":
  unittest.main()
