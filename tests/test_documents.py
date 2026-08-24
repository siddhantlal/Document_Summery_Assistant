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

"""Tests for document validation, PDF parsing, and OCR execution."""

from __future__ import annotations

import io
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from document_summary_assistant import documents
from document_summary_assistant.documents import extract_document
from document_summary_assistant.errors import DocumentProcessingError


def upload(filename: str, data: bytes):
    return SimpleNamespace(filename=filename, stream=io.BytesIO(data))


class DocumentTests(unittest.TestCase):
    def test_non_binary_upload_is_rejected(self) -> None:
        uploaded_file = SimpleNamespace(
            filename="notes.pdf",
            stream=io.StringIO("%PDF-1.7"),
        )
        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(uploaded_file)

        self.assertEqual(context.exception.code, "invalid_file")

    def test_direct_upload_size_limit_is_enforced(self) -> None:
        with patch("document_summary_assistant.documents.MAX_UPLOAD_BYTES", 8):
            with self.assertRaises(DocumentProcessingError) as context:
                extract_document(upload("large.pdf", b"%PDF-1.7-too-large"))

        self.assertEqual(context.exception.code, "file_too_large")
        self.assertEqual(context.exception.status_code, 413)

    def test_unsupported_extension_is_rejected(self) -> None:
        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("notes.txt", b"plain text"))

        self.assertEqual(context.exception.code, "unsupported_file")

    def test_extension_must_match_file_signature(self) -> None:
        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("renamed.pdf", b"not a pdf"))

        self.assertEqual(context.exception.code, "invalid_file")

    @patch("document_summary_assistant.documents.PdfReader")
    def test_pdf_extraction_preserves_page_markers_and_layout(
        self, reader_mock
    ) -> None:
        first_page = MagicMock()
        first_page.extract_text.return_value = "Heading\n  aligned text"
        second_page = MagicMock()
        second_page.extract_text.return_value = "Conclusion"
        reader_mock.return_value = SimpleNamespace(
            is_encrypted=False, pages=[first_page, second_page]
        )

        result = extract_document(upload("sample.pdf", b"%PDF-1.7\ncontent"))

        self.assertEqual(result.file_type, "pdf")
        self.assertEqual(result.pages, 2)
        self.assertIn("--- Page 1 ---\nHeading\n  aligned text", result.text)
        self.assertIn("--- Page 2 ---\nConclusion", result.text)
        first_page.extract_text.assert_called_once_with(
            extraction_mode="layout"
        )

    @patch("document_summary_assistant.documents.PdfReader")
    def test_encrypted_pdf_is_rejected(self, reader_mock) -> None:
        reader_mock.return_value = SimpleNamespace(is_encrypted=True, pages=[])

        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("secret.pdf", b"%PDF-1.7"))

        self.assertEqual(context.exception.code, "encrypted_pdf")

    @patch("document_summary_assistant.documents.PdfReader")
    def test_lazy_pdf_parse_failure_has_safe_error(self, reader_mock) -> None:
        class BrokenReader:
            is_encrypted = False

            @property
            def pages(self):
                raise documents.PdfReadError("broken page tree")

        reader_mock.return_value = BrokenReader()

        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("broken.pdf", b"%PDF-1.7"))

        self.assertEqual(context.exception.code, "invalid_pdf")

    @patch("document_summary_assistant.documents.PdfReader")
    def test_pdf_page_limit_is_enforced(self, reader_mock) -> None:
        reader_mock.return_value = SimpleNamespace(
            is_encrypted=False,
            pages=[MagicMock() for _ in range(documents.MAX_PDF_PAGES + 1)],
        )

        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("long.pdf", b"%PDF-1.7"))

        self.assertEqual(context.exception.code, "pdf_too_long")
        self.assertEqual(context.exception.status_code, 413)

    @patch("document_summary_assistant.documents.PdfReader")
    def test_image_only_pdf_has_actionable_error(self, reader_mock) -> None:
        page = MagicMock()
        page.extract_text.return_value = ""
        reader_mock.return_value = SimpleNamespace(
            is_encrypted=False, pages=[page]
        )

        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("scan.pdf", b"%PDF-1.7"))

        self.assertEqual(context.exception.code, "scanned_pdf")

    @patch("document_summary_assistant.documents.PdfReader")
    def test_extracted_character_limit_is_enforced(self, reader_mock) -> None:
        page = MagicMock()
        page.extract_text.return_value = "x" * 100
        reader_mock.return_value = SimpleNamespace(
            is_encrypted=False, pages=[page]
        )

        with patch(
            "document_summary_assistant.documents.MAX_EXTRACTED_CHARACTERS", 20
        ):
            with self.assertRaises(DocumentProcessingError) as context:
                extract_document(upload("large.pdf", b"%PDF-1.7"))

        self.assertEqual(context.exception.code, "document_too_long")

    @patch("document_summary_assistant.documents.subprocess.run")
    def test_image_ocr_uses_safe_command_and_cleans_up(self, run_mock) -> None:
        run_mock.return_value = SimpleNamespace(
            returncode=0, stdout="OCR text\n"
        )

        result = extract_document(upload("scan.png", b"\x89PNG\r\n\x1a\nimage"))

        self.assertEqual(result.text, "OCR text")
        self.assertEqual(result.file_type, "image")
        command = run_mock.call_args.args[0]
        self.assertEqual(command[0], "tesseract")
        self.assertEqual(command[2:], ["stdout", "--psm", "3", "-l", "eng"])
        self.assertFalse(run_mock.call_args.kwargs["shell"])
        self.assertFalse(Path(command[1]).exists())

    @patch(
        "document_summary_assistant.documents.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_missing_tesseract_has_service_error(self, _run_mock) -> None:
        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("scan.jpg", b"\xff\xd8\xffimage"))

        self.assertEqual(context.exception.code, "ocr_unavailable")
        self.assertEqual(context.exception.status_code, 503)

    @patch(
        "document_summary_assistant.documents.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="tesseract", timeout=45),
    )
    def test_ocr_timeout_has_gateway_timeout_status(self, _run_mock) -> None:
        with self.assertRaises(DocumentProcessingError) as context:
            extract_document(upload("scan.jpeg", b"\xff\xd8\xffimage"))

        self.assertEqual(context.exception.code, "ocr_timeout")
        self.assertEqual(context.exception.status_code, 504)


if __name__ == "__main__":
    unittest.main()
