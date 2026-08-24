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

"""Public document validation and extraction interface."""

from document_summary_assistant.documents.image import ocr_available
from document_summary_assistant.documents.models import ExtractedDocument
from document_summary_assistant.documents.service import extract_document


__all__ = ["ExtractedDocument", "extract_document", "ocr_available"]
