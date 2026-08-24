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

"""Tests for the dependency-free Gemini REST client."""

from __future__ import annotations

import io
import json
import os
import unittest
from unittest.mock import patch
from urllib import error

from document_summary_assistant.errors import SummaryServiceError
from document_summary_assistant.summaries import GeneratedSummary
from document_summary_assistant.summaries import generate_summary


class _FakeResponse:
  def __init__(self, payload: dict) -> None:
    self._body = json.dumps(payload).encode("utf-8")

  def __enter__(self):
    return self

  def __exit__(self, *_args):
    return False

  def read(self) -> bytes:
    return self._body


def _provider_payload(summary: str, key_points: list[object]) -> dict:
  return {
      "candidates": [
          {
              "content": {
                  "parts": [
                      {
                          "text": json.dumps(
                              {
                                  "summary": summary,
                                  "key_points": key_points,
                              }
                          )
                      }
                  ]
              }
          }
      ]
  }


class GeminiTest(unittest.TestCase):
  def test_empty_document_is_rejected_before_provider_call(self) -> None:
    with self.assertRaises(SummaryServiceError) as context:
      generate_summary("   ", "short")

    self.assertEqual(context.exception.code, "empty_document")
    self.assertEqual(context.exception.status_code, 400)

  def test_missing_api_key_is_configuration_error(self) -> None:
    with patch.dict(os.environ, {}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "summary_not_configured")
    self.assertEqual(context.exception.status_code, 503)

  def test_invalid_length_is_rejected(self) -> None:
    with self.assertRaises(SummaryServiceError) as context:
      generate_summary("Document", "tiny")

    self.assertEqual(context.exception.code, "invalid_length")

  @patch("document_summary_assistant.summaries.gemini.request.urlopen")
  def test_request_and_response_follow_structured_contract(
      self,
      urlopen_mock,
  ) -> None:
    urlopen_mock.return_value = _FakeResponse(
        _provider_payload("Accurate summary", ["One", "Two", "Three"])
    )

    with patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "secret", "GEMINI_MODEL": "gemini-test"},
        clear=True,
    ):
      result = generate_summary("Source document", "short")

    self.assertEqual(
        result,
        GeneratedSummary(
            summary="Accurate summary",
            key_points=("One", "Two", "Three"),
        ),
    )
    api_request = urlopen_mock.call_args.args[0]
    self.assertTrue(
        api_request.full_url.endswith("gemini-test:generateContent")
    )
    self.assertEqual(api_request.headers["X-goog-api-key"], "secret")
    payload = json.loads(api_request.data.decode("utf-8"))
    config = payload["generationConfig"]
    self.assertEqual(config["responseMimeType"], "application/json")
    self.assertEqual(config["responseJsonSchema"]["type"], "object")

  @patch("document_summary_assistant.summaries.gemini.request.urlopen")
  def test_malformed_provider_response_is_rejected(
      self,
      urlopen_mock,
  ) -> None:
    urlopen_mock.return_value = _FakeResponse({"candidates": []})

    with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "medium")

    self.assertEqual(context.exception.code, "invalid_provider_response")

  @patch("document_summary_assistant.summaries.gemini.request.urlopen")
  def test_rate_limit_becomes_retryable_service_error(
      self,
      urlopen_mock,
  ) -> None:
    urlopen_mock.side_effect = error.HTTPError(
        url="https://example.invalid",
        code=429,
        msg="rate limited",
        hdrs=None,
        fp=io.BytesIO(),
    )

    with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "provider_rate_limited")
    self.assertEqual(context.exception.status_code, 503)

  @patch("document_summary_assistant.summaries.gemini.request.urlopen")
  def test_incomplete_key_points_are_rejected(self, urlopen_mock) -> None:
    urlopen_mock.return_value = _FakeResponse(
        _provider_payload("Summary", ["Only one point"])
    )

    with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "invalid_provider_response")

  @patch("document_summary_assistant.summaries.gemini.request.urlopen")
  def test_non_string_key_point_is_rejected(self, urlopen_mock) -> None:
    urlopen_mock.return_value = _FakeResponse(
        _provider_payload("Summary", ["One", 2, "Three"])
    )

    with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "invalid_provider_response")


if __name__ == "__main__":
  unittest.main()
