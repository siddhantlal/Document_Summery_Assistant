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

"""Tests for local runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from document_summary_assistant.config import load_local_environment


class ConfigTest(unittest.TestCase):
  def test_local_environment_loader_preserves_existing_values(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
      env_path = Path(directory) / ".env"
      env_path.write_text(
          "NEW_TEST_SETTING=loaded\nEXISTING_TEST_SETTING=file-value\n",
          encoding="utf-8",
      )
      existing_environment = {"EXISTING_TEST_SETTING": "shell-value"}
      with patch.dict(os.environ, existing_environment, clear=False):
        os.environ.pop("NEW_TEST_SETTING", None)
        load_local_environment(env_path)
        self.assertEqual(os.environ["NEW_TEST_SETTING"], "loaded")
        self.assertEqual(
            os.environ["EXISTING_TEST_SETTING"],
            "shell-value",
        )
        os.environ.pop("NEW_TEST_SETTING", None)


if __name__ == "__main__":
  unittest.main()
