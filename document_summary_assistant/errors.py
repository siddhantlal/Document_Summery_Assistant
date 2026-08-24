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

"""Safe errors shared across application service boundaries."""

from __future__ import annotations


class PublicError(Exception):
  """An expected failure that is safe to expose through the public API."""

  def __init__(
      self,
      code: str,
      message: str,
      status_code: int = 422,
  ) -> None:
    super().__init__(message)
    self.code = code
    self.message = message
    self.status_code = status_code


class DocumentProcessingError(PublicError):
  """A safe, user-facing document processing failure."""


class SummaryServiceError(PublicError):
  """A safe, user-facing summary provider failure."""

  def __init__(
      self,
      code: str,
      message: str,
      status_code: int = 502,
  ) -> None:
    super().__init__(code, message, status_code)
