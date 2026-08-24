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

"""Application factory for the Document Summary Assistant."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask
from werkzeug.exceptions import RequestEntityTooLarge

from document_summary_assistant import web
from document_summary_assistant.config import MAX_UPLOAD_BYTES


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
  """Create and configure the Flask application.

  Args:
    config: Optional Flask configuration overrides, primarily for tests.

  Returns:
    A configured Flask application.
  """

  app = Flask(__name__)
  app.config.from_mapping(MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES)
  if config:
    app.config.from_mapping(config)

  app.register_blueprint(web.blueprint)
  app.register_error_handler(
      RequestEntityTooLarge,
      web.handle_large_upload,
  )
  return app
