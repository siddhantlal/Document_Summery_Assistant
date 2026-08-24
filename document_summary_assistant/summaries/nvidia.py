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

"""NVIDIA NIM client and structured summary response validation."""

from __future__ import annotations

from collections.abc import Iterable
import json
import os
from typing import Any

from openai import APIConnectionError
from openai import APIStatusError
from openai import APITimeoutError
from openai import AuthenticationError
from openai import OpenAI
from openai import PermissionDeniedError
from openai import RateLimitError

from document_summary_assistant.errors import SummaryServiceError
from document_summary_assistant.summaries.models import GeneratedSummary
from document_summary_assistant.summaries.models import SUMMARY_LENGTHS
from document_summary_assistant.summaries.prompts import build_messages


DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MAX_GENERATION_TOKENS = 16_384
REQUEST_TIMEOUT_SECONDS = 120


def is_configured() -> bool:
  """Return whether NVIDIA API credentials are present."""

  return bool(os.getenv("NVIDIA_API_KEY", "").strip())


def generate_summary(
    document_text: str,
    summary_length: str,
) -> GeneratedSummary:
  """Generate and validate a structured summary with NVIDIA NIM.

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

  api_key = os.getenv("NVIDIA_API_KEY", "").strip()
  if not api_key:
    raise SummaryServiceError(
        "summary_not_configured",
        "Summary generation is not configured on the server.",
        503,
    )

  model = os.getenv("NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL).strip()
  if not model:
    model = DEFAULT_NVIDIA_MODEL

  try:
    client = OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    stream = client.chat.completions.create(
        model=model,
        messages=build_messages(
            document_text,
            SUMMARY_LENGTHS[summary_length],
        ),
        temperature=1,
        top_p=0.95,
        max_tokens=MAX_GENERATION_TOKENS,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": True,
            }
        },
        stream=True,
    )
    response_text = _collect_response(stream)
  except RateLimitError as exc:
    raise SummaryServiceError(
        "provider_rate_limited",
        "The summary service is busy. Please try again shortly.",
        503,
    ) from exc
  except (AuthenticationError, PermissionDeniedError) as exc:
    raise SummaryServiceError(
        "summary_not_configured",
        "The summary service credentials are not valid.",
        503,
    ) from exc
  except (APIConnectionError, APITimeoutError) as exc:
    raise SummaryServiceError(
        "provider_timeout",
        "The summary service timed out. Please try again.",
        504,
    ) from exc
  except APIStatusError as exc:
    raise SummaryServiceError(
        "provider_error",
        "The summary service could not process the document.",
    ) from exc

  return _parse_summary(
      response_text,
      SUMMARY_LENGTHS[summary_length].key_points,
  )


def _collect_response(chunks: Iterable[Any]) -> str:
  """Collect final content while discarding private reasoning chunks."""

  content_parts: list[str] = []
  for chunk in chunks:
    if not chunk.choices:
      continue
    content = chunk.choices[0].delta.content
    if content:
      content_parts.append(content)
  return "".join(content_parts)


def _parse_summary(
    response_text: str,
    expected_key_points: int,
) -> GeneratedSummary:
  try:
    result = _decode_json_object(response_text)
    raw_summary = result["summary"]
    raw_key_points = result["key_points"]
    if not isinstance(raw_summary, str) or not isinstance(raw_key_points, list):
      raise TypeError("Summary fields have unexpected types.")
    if not all(isinstance(point, str) for point in raw_key_points):
      raise TypeError("Key points must be strings.")
    summary = raw_summary.strip()
    key_points = tuple(point.strip() for point in raw_key_points)
  except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
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


def _decode_json_object(response_text: str) -> dict[str, Any]:
  """Decode a JSON object, tolerating an accidental Markdown fence."""

  candidate = response_text.strip()
  if candidate.startswith("```") and candidate.endswith("```"):
    lines = candidate.splitlines()
    candidate = "\n".join(lines[1:-1]).strip()

  try:
    result = json.loads(candidate)
  except json.JSONDecodeError:
    object_start = candidate.find("{")
    object_end = candidate.rfind("}") + 1
    if object_start < 0 or object_end <= object_start:
      raise
    result = json.loads(candidate[object_start:object_end])

  if not isinstance(result, dict):
    raise TypeError("The provider response must be a JSON object.")
  return result
