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

"""Tests for the NVIDIA NIM summary client."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from document_summary_assistant.errors import SummaryServiceError
from document_summary_assistant.summaries import GeneratedSummary
from document_summary_assistant.summaries import generate_summary
from document_summary_assistant.summaries import nvidia


class _ProviderError(Exception):
  """Synthetic provider failure for exception mapping tests."""


def _chunk(
    content: str | None = None,
    reasoning: str | None = None,
) -> SimpleNamespace:
  delta = SimpleNamespace(
      content=content,
      reasoning_content=reasoning,
  )
  return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _provider_json(summary: str, key_points: list[object]) -> str:
  return json.dumps(
      {
          "summary": summary,
          "key_points": key_points,
      }
  )


class NvidiaTest(unittest.TestCase):
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

  @patch("document_summary_assistant.summaries.nvidia.OpenAI")
  def test_request_and_response_follow_streaming_contract(
      self,
      client_mock,
  ) -> None:
    response_json = _provider_json(
        "Accurate summary",
        ["One", "Two", "Three"],
    )
    completion_mock = client_mock.return_value.chat.completions.create
    completion_mock.return_value = [
        _chunk(reasoning="Internal reasoning"),
        SimpleNamespace(choices=[]),
        _chunk(response_json[:20]),
        _chunk(response_json[20:]),
    ]

    with patch.dict(
        os.environ,
        {"NVIDIA_API_KEY": "secret", "NVIDIA_MODEL": "nvidia/test-model"},
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
    client_mock.assert_called_once_with(
        base_url=nvidia.NVIDIA_BASE_URL,
        api_key="secret",
        timeout=nvidia.REQUEST_TIMEOUT_SECONDS,
    )
    call_kwargs = completion_mock.call_args.kwargs
    self.assertEqual(call_kwargs["model"], "nvidia/test-model")
    self.assertEqual(call_kwargs["temperature"], 1)
    self.assertEqual(call_kwargs["top_p"], 0.95)
    self.assertEqual(call_kwargs["max_tokens"], 16_384)
    self.assertTrue(call_kwargs["stream"])
    self.assertEqual(
        call_kwargs["extra_body"],
        {"chat_template_kwargs": {"enable_thinking": True}},
    )
    self.assertEqual(call_kwargs["messages"][0]["role"], "system")
    self.assertIn(
        "DOCUMENT_START\nSource document\nDOCUMENT_END",
        call_kwargs["messages"][1]["content"],
    )

  @patch("document_summary_assistant.summaries.nvidia.OpenAI")
  def test_malformed_provider_response_is_rejected(self, client_mock) -> None:
    client_mock.return_value.chat.completions.create.return_value = [
        _chunk("not json")
    ]

    with patch.dict(os.environ, {"NVIDIA_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "medium")

    self.assertEqual(context.exception.code, "invalid_provider_response")

  @patch("document_summary_assistant.summaries.nvidia.OpenAI")
  def test_rate_limit_becomes_retryable_service_error(
      self,
      client_mock,
  ) -> None:
    client_mock.return_value.chat.completions.create.side_effect = (
        _ProviderError("rate limited")
    )

    with patch.object(nvidia, "RateLimitError", _ProviderError):
      with patch.dict(os.environ, {"NVIDIA_API_KEY": "secret"}, clear=True):
        with self.assertRaises(SummaryServiceError) as context:
          generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "provider_rate_limited")
    self.assertEqual(context.exception.status_code, 503)

  @patch("document_summary_assistant.summaries.nvidia.OpenAI")
  def test_incomplete_key_points_are_rejected(self, client_mock) -> None:
    client_mock.return_value.chat.completions.create.return_value = [
        _chunk(_provider_json("Summary", ["Only one point"]))
    ]

    with patch.dict(os.environ, {"NVIDIA_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "invalid_provider_response")

  @patch("document_summary_assistant.summaries.nvidia.OpenAI")
  def test_non_string_key_point_is_rejected(self, client_mock) -> None:
    client_mock.return_value.chat.completions.create.return_value = [
        _chunk(_provider_json("Summary", ["One", 2, "Three"]))
    ]

    with patch.dict(os.environ, {"NVIDIA_API_KEY": "secret"}, clear=True):
      with self.assertRaises(SummaryServiceError) as context:
        generate_summary("Document", "short")

    self.assertEqual(context.exception.code, "invalid_provider_response")

  def test_markdown_fenced_json_is_tolerated(self) -> None:
    response = "```json\n" + _provider_json(
        "Summary",
        ["One", "Two", "Three"],
    ) + "\n```"

    result = nvidia._parse_summary(response, expected_key_points=3)

    self.assertEqual(result.summary, "Summary")


if __name__ == "__main__":
  unittest.main()
