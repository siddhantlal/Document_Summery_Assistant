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

"""HTTP contract tests for the Flask application."""

from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from document_summary_assistant import create_app
from document_summary_assistant.config import load_local_environment
from document_summary_assistant.documents import ExtractedDocument
from document_summary_assistant.errors import DocumentProcessingError
from document_summary_assistant.summaries import GeneratedSummary


class WebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def test_index_renders_application(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Document Summary Assistant", response.data)

    def test_static_assets_are_packaged_with_application(self) -> None:
        response = self.client.get("/static/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/javascript")
        response.close()

    def test_local_environment_loader_preserves_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "NEW_TEST_SETTING=loaded\nEXISTING_TEST_SETTING=file-value\n",
                encoding="utf-8",
            )
            existing_environment = {
                "EXISTING_TEST_SETTING": "shell-value"
            }
            with patch.dict(os.environ, existing_environment, clear=False):
                os.environ.pop("NEW_TEST_SETTING", None)
                load_local_environment(env_path)
                self.assertEqual(os.environ["NEW_TEST_SETTING"], "loaded")
                self.assertEqual(
                    os.environ["EXISTING_TEST_SETTING"],
                    "shell-value",
                )
                os.environ.pop("NEW_TEST_SETTING", None)

    @patch("document_summary_assistant.web.ocr_available", return_value=True)
    @patch("document_summary_assistant.web.is_configured", return_value=True)
    def test_health_reports_dependencies(self, _configured, _ocr) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "status": "ok",
                "dependencies": {
                    "gemini_configured": True,
                    "ocr_available": True,
                },
            },
        )

    def test_missing_document_returns_stable_error(self) -> None:
        response = self.client.post("/api/summarize", data={"length": "short"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"],
            "missing_document",
        )

    def test_invalid_length_is_rejected_before_processing(self) -> None:
        response = self.client.post(
            "/api/summarize",
            data={
                "length": "tiny",
                "document": (io.BytesIO(b"%PDF-1.4"), "sample.pdf"),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_length")

    @patch("document_summary_assistant.web.generate_summary")
    @patch("document_summary_assistant.web.extract_document")
    def test_success_response_matches_public_contract(
        self, extract_mock, summary_mock
    ) -> None:
        extract_mock.return_value = ExtractedDocument(
            text="A useful document", file_type="pdf", pages=2
        )
        summary_mock.return_value = GeneratedSummary(
            summary="A concise summary.",
            key_points=("First", "Second", "Third"),
        )

        response = self.client.post(
            "/api/summarize",
            data={
                "length": "short",
                "document": (io.BytesIO(b"%PDF-1.4"), "sample.pdf"),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["summary"], "A concise summary.")
        self.assertEqual(payload["key_points"], ["First", "Second", "Third"])
        self.assertEqual(
            payload["metadata"],
            {
                "filename": "sample.pdf",
                "file_type": "pdf",
                "pages": 2,
                "characters_extracted": 17,
                "summary_length": "short",
            },
        )
        summary_mock.assert_called_once_with("A useful document", "short")

    @patch("document_summary_assistant.web.extract_document")
    def test_service_error_is_mapped_without_internal_details(
        self, extract_mock
    ) -> None:
        def fail_extraction(uploaded_file):
            uploaded_file.close()
            raise DocumentProcessingError(
                "invalid_pdf", "The PDF is damaged or cannot be read.", 422
            )

        extract_mock.side_effect = fail_extraction

        response = self.client.post(
            "/api/summarize",
            data={
                "length": "medium",
                "document": (io.BytesIO(b"%PDF-1.4"), "sample.pdf"),
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.get_json(),
            {
                "error": {
                    "code": "invalid_pdf",
                    "message": "The PDF is damaged or cannot be read.",
                }
            },
        )
        response.close()

    def test_oversized_request_returns_json_error(self) -> None:
        original_limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.app.config["MAX_CONTENT_LENGTH"] = 256
        try:
            response = self.client.post(
                "/api/summarize",
                data={
                    "length": "medium",
                    "document": (io.BytesIO(b"x" * 1024), "large.pdf"),
                },
            )
        finally:
            self.app.config["MAX_CONTENT_LENGTH"] = original_limit

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"]["code"], "file_too_large")
        response.close()


if __name__ == "__main__":
    unittest.main()
