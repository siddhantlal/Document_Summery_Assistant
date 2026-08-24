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

"""Gemini REST client and structured response validation."""

from __future__ import annotations

import json
import os
import socket
from typing import Any
from urllib import error, parse, request

from document_summary_assistant.errors import SummaryServiceError
from document_summary_assistant.summaries.models import GeneratedSummary
from document_summary_assistant.summaries.models import SUMMARY_LENGTHS
from document_summary_assistant.summaries.prompts import build_payload


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
REQUEST_TIMEOUT_SECONDS = 60


def is_configured() -> bool:
  """Return whether Gemini credentials are present."""

  return bool(os.getenv("GEMINI_API_KEY", "").strip())


def generate_summary(
    document_text: str,
    summary_length: str,
) -> GeneratedSummary:
  """Generate and validate a structured summary with Gemini.

  Args:
    document_text: Non-empty text extracted from the uploaded document.
    summary_length: One of the configured summary length names.

  Returns:
    A validated immutable summary result.

  Raises:
    SummaryServiceError: If input, configuration, transport, or output fails.
  """

  if summary_length not in SUMMARY_LENGTHS:
    raise SummaryServiceError(
        "invalid_length",
        "Choose a short, medium, or long summary.",
        400,
    )
  if not document_text.strip():
    raise SummaryServiceError(
        "empty_document",
        "The document did not contain text to summarize.",
        400,
    )

  api_key = os.getenv("GEMINI_API_KEY", "").strip()
  if not api_key:
    raise SummaryServiceError(
        "summary_not_configured",
        "Summary generation is not configured on the server.",
        503,
    )

  model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
  if not model:
    model = DEFAULT_GEMINI_MODEL
  length_config = SUMMARY_LENGTHS[summary_length]
  payload = build_payload(document_text, length_config)
  endpoint = GEMINI_ENDPOINT.format(model=parse.quote(model, safe=""))
  api_request = request.Request(
      endpoint,
      data=json.dumps(payload).encode("utf-8"),
      headers={
          "Content-Type": "application/json",
          "x-goog-api-key": api_key,
      },
      method="POST",
  )

  try:
    with request.urlopen(
        api_request,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
      response_payload = json.loads(response.read().decode("utf-8"))
  except error.HTTPError as exc:
    if exc.code == 429:
      raise SummaryServiceError(
          "provider_rate_limited",
          "The summary service is busy. Please try again shortly.",
          503,
      ) from exc
    if exc.code in {401, 403}:
      raise SummaryServiceError(
          "summary_not_configured",
          "The summary service credentials are not valid.",
          503,
      ) from exc
    raise SummaryServiceError(
        "provider_error",
        "The summary service could not process the document.",
    ) from exc
  except (error.URLError, TimeoutError, socket.timeout) as exc:
    raise SummaryServiceError(
        "provider_timeout",
        "The summary service timed out. Please try again.",
        504,
    ) from exc
  except (UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SummaryServiceError(
        "invalid_provider_response",
        "The summary service returned an invalid response.",
    ) from exc

  return _parse_summary(response_payload, length_config.key_points)


def _parse_summary(
    payload: dict[str, Any],
    expected_key_points: int,
) -> GeneratedSummary:
  try:
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    raw_summary = result["summary"]
    raw_key_points = result["key_points"]
    if not isinstance(raw_summary, str) or not isinstance(raw_key_points, list):
      raise TypeError("Summary fields have unexpected types.")
    if not all(isinstance(point, str) for point in raw_key_points):
      raise TypeError("Key points must be strings.")
    summary = raw_summary.strip()
    key_points = tuple(point.strip() for point in raw_key_points)
  except (
      KeyError,
      IndexError,
      TypeError,
      AttributeError,
      json.JSONDecodeError,
  ) as exc:
    raise SummaryServiceError(
        "invalid_provider_response",
        "The summary service returned an invalid response.",
    ) from exc

  if (
      not summary
      or len(key_points) != expected_key_points
      or any(not point for point in key_points)
  ):
    raise SummaryServiceError(
        "invalid_provider_response",
        "The summary service returned an incomplete response.",
    )

  return GeneratedSummary(summary=summary, key_points=key_points)
