"""JSON serialization helpers for MCP tool responses."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_jsonable(obj: Any) -> Any:
    """Convert nested objects to JSON-safe structures."""
    return json.loads(json.dumps(obj, default=_json_default))


def success(data: Any) -> str:
    return json.dumps({"ok": True, "data": to_jsonable(data)}, indent=2)


def failure(error: str, hint: str | None = None) -> str:
    payload: dict[str, Any] = {"ok": False, "error": error}
    if hint:
        payload["hint"] = hint
    return json.dumps(payload, indent=2)
