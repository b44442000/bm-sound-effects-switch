from __future__ import annotations

import json
import os
import tempfile
from typing import Any


def load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as src:
            return json.load(src)
    except (OSError, ValueError, TypeError):
        return default


def save_json_atomic(path: str, data: Any, *, indent: int = 2) -> None:
    """Write JSON without leaving a partially-written configuration file."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".bm-config-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as dst:
            json.dump(data, dst, ensure_ascii=False, indent=indent)
            dst.write("\n")
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
