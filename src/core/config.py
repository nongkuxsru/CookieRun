"""Loads config/config.yaml into a simple dict-like accessor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path("config/config.yaml")


class Config:
    """Thin wrapper around the parsed YAML config with dotted-path access."""

    def __init__(self, data: dict[str, Any], loaded_path: Path | None = None):
        self._data = data
        self._loaded_path = loaded_path

    @classmethod
    def load(cls, path: str | Path = _DEFAULT_CONFIG_PATH) -> "Config":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์คอนฟิก: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data, loaded_path=path)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Fetch a nested value using a dotted path, e.g. 'emulator.adb_path'."""
        node: Any = self._data
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        """Set a nested value using a dotted path, creating intermediate dicts as needed."""
        parts = dotted_key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def save(self, path: str | Path | None = None) -> None:
        """Persist the current in-memory config back to disk as YAML."""
        target = Path(path) if path else self._loaded_path
        if not target:
            raise ValueError(
                "ไม่ทราบพาทไฟล์คอนฟิกที่จะบันทึก (ไม่ได้โหลดจากไฟล์และไม่ได้ระบุพาทเอง)"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._data, f, allow_unicode=True, sort_keys=False)

    @property
    def raw(self) -> dict[str, Any]:
        return self._data
