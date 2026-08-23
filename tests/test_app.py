"""HTTP contract tests for the Flask application."""

from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app as app_module
from document_service import DocumentProcessingError, ExtractedDocument


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def test_index_renders_application(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Document Summary Assistant", response.data)

    def test_local_environment_loader_does_not_override_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "NEW_TEST_SETTING=loaded\nEXISTING_TEST_SETTING=file-value\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"EXISTING_TEST_SETTING": "shell-value"}, clear=False
            ):
                os.environ.pop("NEW_TEST_SETTING", None)
                app_module.load_local_environment(str(env_path))
                self.assertEqual(os.environ["NEW_TEST_SETTING"], "loaded")
                self.assertEqual(os.environ["EXISTING_TEST_SETTING"], "shell-value")
                os.environ.pop("NEW_TEST_SETTING", None)

    @patch("app.ocr_available", return_value=True)
    @patch("app.is_configured", return_value=True)
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
        self.assertEqual(response.get_json()["error"]["code"], "missing_document")

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

    @patch("app.generate_summary")
    @patch("app.extract_document")
    def test_success_response_matches_public_contract(self, extract_mock, summary_mock) -> None:
        extract_mock.return_value = ExtractedDocument(
            text="A useful document", file_type="pdf", pages=2
        )
        summary_mock.return_value = {
            "summary": "A concise summary.",
            "key_points": ["First", "Second", "Third"],
        }

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

    @patch("app.extract_document")
    def test_service_error_is_mapped_without_internal_details(self, extract_mock) -> None:
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
        original_limit = app_module.app.config["MAX_CONTENT_LENGTH"]
        app_module.app.config["MAX_CONTENT_LENGTH"] = 256
        try:
            response = self.client.post(
                "/api/summarize",
                data={
                    "length": "medium",
                    "document": (io.BytesIO(b"x" * 1024), "large.pdf"),
                },
            )
        finally:
            app_module.app.config["MAX_CONTENT_LENGTH"] = original_limit

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"]["code"], "file_too_large")
        response.close()


if __name__ == "__main__":
    unittest.main()
