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

"""Tests for image OCR extraction."""

from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from document_summary_assistant.documents.image import extract_image
from document_summary_assistant.errors import DocumentProcessingError


class ImageExtractionTest(unittest.TestCase):
  @patch("document_summary_assistant.documents.image.subprocess.run")
  def test_ocr_uses_safe_command_and_cleans_up(self, run_mock) -> None:
    run_mock.return_value = SimpleNamespace(
        returncode=0,
        stdout="OCR text\n",
    )

    result = extract_image(b"\x89PNG\r\n\x1a\nimage", ".png")

    self.assertEqual(result.text, "OCR text")
    self.assertEqual(result.file_type, "image")
    command = run_mock.call_args.args[0]
    self.assertEqual(command[0], "tesseract")
    self.assertEqual(command[2:], ["stdout", "--psm", "3", "-l", "eng"])
    self.assertFalse(run_mock.call_args.kwargs["shell"])
    self.assertFalse(Path(command[1]).exists())

  @patch(
      "document_summary_assistant.documents.image.subprocess.run",
      side_effect=FileNotFoundError,
  )
  def test_missing_tesseract_has_service_error(self, _run_mock) -> None:
    with self.assertRaises(DocumentProcessingError) as context:
      extract_image(b"\xff\xd8\xffimage", ".jpg")

    self.assertEqual(context.exception.code, "ocr_unavailable")
    self.assertEqual(context.exception.status_code, 503)

  @patch(
      "document_summary_assistant.documents.image.subprocess.run",
      side_effect=subprocess.TimeoutExpired(cmd="tesseract", timeout=45),
  )
  def test_ocr_timeout_has_gateway_timeout_status(self, _run_mock) -> None:
    with self.assertRaises(DocumentProcessingError) as context:
      extract_image(b"\xff\xd8\xffimage", ".jpeg")

    self.assertEqual(context.exception.code, "ocr_timeout")
    self.assertEqual(context.exception.status_code, 504)


if __name__ == "__main__":
  unittest.main()
