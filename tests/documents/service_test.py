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

"""Tests for document upload validation and extractor selection."""

from __future__ import annotations

import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from document_summary_assistant.documents import extract_document
from document_summary_assistant.errors import DocumentProcessingError


def _upload(filename: str, data: bytes) -> SimpleNamespace:
  return SimpleNamespace(filename=filename, stream=io.BytesIO(data))


class DocumentServiceTest(unittest.TestCase):
  def test_non_binary_upload_is_rejected(self) -> None:
    uploaded_file = SimpleNamespace(
        filename="notes.pdf",
        stream=io.StringIO("%PDF-1.7"),
    )
    with self.assertRaises(DocumentProcessingError) as context:
      extract_document(uploaded_file)

    self.assertEqual(context.exception.code, "invalid_file")

  def test_direct_upload_size_limit_is_enforced(self) -> None:
    with patch(
        "document_summary_assistant.documents.service.MAX_UPLOAD_BYTES",
        8,
    ):
      with self.assertRaises(DocumentProcessingError) as context:
        extract_document(_upload("large.pdf", b"%PDF-1.7-too-large"))

    self.assertEqual(context.exception.code, "file_too_large")
    self.assertEqual(context.exception.status_code, 413)

  def test_unsupported_extension_is_rejected(self) -> None:
    with self.assertRaises(DocumentProcessingError) as context:
      extract_document(_upload("notes.txt", b"plain text"))

    self.assertEqual(context.exception.code, "unsupported_file")

  def test_extension_must_match_file_signature(self) -> None:
    with self.assertRaises(DocumentProcessingError) as context:
      extract_document(_upload("renamed.pdf", b"not a pdf"))

    self.assertEqual(context.exception.code, "invalid_file")


if __name__ == "__main__":
  unittest.main()
