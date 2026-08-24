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

"""Public document summarization interface."""

from document_summary_assistant.summaries.gemini import generate_summary
from document_summary_assistant.summaries.gemini import is_configured
from document_summary_assistant.summaries.models import GeneratedSummary
from document_summary_assistant.summaries.models import SUMMARY_LENGTHS
from document_summary_assistant.summaries.models import SummaryLength


__all__ = [
    "GeneratedSummary",
    "SUMMARY_LENGTHS",
    "SummaryLength",
    "generate_summary",
    "is_configured",
]
