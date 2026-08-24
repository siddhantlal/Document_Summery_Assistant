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

"""Runtime configuration and local environment loading."""

from __future__ import annotations

import os
from pathlib import Path


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_PORT = 5000


def load_local_environment(path: str | Path = ".env") -> None:
  """Load simple key-value pairs without overriding the process environment.

  Args:
    path: Local environment file to read when it exists.
  """

  env_path = Path(path)
  if not env_path.is_file():
    return

  for raw_line in env_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
      value = value[1:-1]
    if key:
      os.environ.setdefault(key, value)
