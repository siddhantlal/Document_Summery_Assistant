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

"""Immutable summary results and generation targets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryLength:
  """Generation targets for one user-selectable summary length."""

  words: int
  key_points: int
  max_tokens: int


@dataclass(frozen=True)
class GeneratedSummary:
  """Validated summary content returned by the provider."""

  summary: str
  key_points: tuple[str, ...]


SUMMARY_LENGTHS = {
    "short": SummaryLength(words=100, key_points=3, max_tokens=700),
    "medium": SummaryLength(words=200, key_points=5, max_tokens=1_200),
    "long": SummaryLength(words=350, key_points=7, max_tokens=1_800),
}
