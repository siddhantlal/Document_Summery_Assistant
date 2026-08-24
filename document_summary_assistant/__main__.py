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

"""Local development entry point."""

from __future__ import annotations

import os

from document_summary_assistant import create_app
from document_summary_assistant.config import DEFAULT_PORT
from document_summary_assistant.config import load_local_environment


def main() -> None:
  """Run the local development server."""

  load_local_environment()
  port = int(os.getenv("PORT", str(DEFAULT_PORT)))
  create_app().run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
  main()
