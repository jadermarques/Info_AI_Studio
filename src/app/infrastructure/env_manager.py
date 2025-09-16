"""Utilities to manage values inside the .env file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def update_env_values(values: Mapping[str, str], env_path: Path | None = None) -> Path:
    """Persist values to a .env file, preserving existing comments and keys."""

    path = env_path or Path(".env")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    updated: list[str] = []
    handled: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated.append(line)
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key in values:
            value = values[key]
            updated.append(f"{key}={value}")
            handled.add(key)
            os.environ[key] = value
        else:
            updated.append(line)

    for key, value in values.items():
        if key in handled:
            continue
        updated.append(f"{key}={value}")
        os.environ[key] = value

    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return path