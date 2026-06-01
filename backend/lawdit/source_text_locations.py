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
        "lineNumber": 1,
        "columnNumber": 1,
        "lineStarts": text_line_starts(text),
    },)


def text_line_starts(text: str) -> tuple[int, ...]:
    starts = [0]
    for index, character in enumerate(text):
        if character == "\n" and index + 1 < len(text):
            starts.append(index + 1)
    return tuple(starts)
