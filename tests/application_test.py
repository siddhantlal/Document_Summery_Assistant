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

"""Integration tests for Flask application assembly."""

from __future__ import annotations

import io
import unittest

from document_summary_assistant import create_app


class ApplicationTest(unittest.TestCase):
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
