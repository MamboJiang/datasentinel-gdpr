"""Source-local text range helpers for extracted document streams."""

from __future__ import annotations

from typing import Any


def text_stream_location(text: str, file_format: str, label: str) -> tuple[dict[str, Any], ...]:
    if not text.strip():
        return ()
    return ({
        "format": file_format,
        "label": label,
        "start": 0,
        "end": len(text),
    },)
