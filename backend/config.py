"""Load local server configuration without exposing secrets to the browser."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def setting(key, default=None):
    if key in os.environ:
        return os.environ[key]
    config = ROOT / ".env.local"
    if config.exists():
        for line in config.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == key:
                return value.strip()
    return default
