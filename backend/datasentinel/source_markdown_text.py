"""Markdown text extraction with table-cell locations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .source_text_decoding import decode_text_body


@dataclass(frozen=True)
class MarkdownTextExtraction:
    text: str
    locations: tuple[dict[str, Any], ...]


class MarkdownExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_markdown_text(body: bytes, name: str, *, content_type: str = "", file_format: str = "markdown") -> MarkdownTextExtraction:
    decoded = decode_text_body(body, content_type)
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    lines = decoded.splitlines()
    index = 0

    while index < len(lines):
        if _is_table_start(lines, index):
            header = _parse_pipe_row(lines[index])
            index += 2
            while index < len(lines) and _looks_like_pipe_row(lines[index]):
                cells = _parse_pipe_row(lines[index])
                if _is_separator_cells(cells):
                    index += 1
                    continue
                _append_table_row(file_format, header, index + 1, cells, fragments, locations)
                index += 1
            continue

        line = lines[index].strip()
        if line:
            start = _append_fragment(fragments, line)
            locations.append({
                "format": file_format,
                "label": f"Line {index + 1}",
                "start": start,
                "end": start + len(line),
            })
        index += 1

    text = "\n".join(fragments)
    if not text.strip():
        raise MarkdownExtractionIssue(f"{name} has no extractable Markdown text.", recognition_difficulty="hard")
    return MarkdownTextExtraction(text, tuple(locations))


def _is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    header = _parse_pipe_row(lines[index])
    separator = _parse_pipe_row(lines[index + 1])
    return len([cell for cell in header if cell]) >= 2 and _is_separator_cells(separator)


def _looks_like_pipe_row(line: str) -> bool:
    return "|" in line and len(_parse_pipe_row(line)) >= 2


def _parse_pipe_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in text:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(character)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _is_separator_cells(cells: list[str]) -> bool:
    nonempty = [cell.replace(" ", "") for cell in cells if cell.strip()]
    if len(nonempty) < 2:
        return False
    return all(_is_separator_cell(cell) for cell in nonempty)


def _is_separator_cell(cell: str) -> bool:
    stripped = cell.strip(":")
    return len(stripped) >= 3 and set(stripped) == {"-"}


def _append_table_row(
    file_format: str,
    header: list[str],
    line_number: int,
    cells: list[str],
    fragments: list[str],
    locations: list[dict[str, Any]],
) -> None:
    for column, value in enumerate(cells, start=1):
        value = value.strip()
        if not value:
            continue
        label = header[column - 1].strip() if column <= len(header) else ""
        fragment = f"{label}: {value}" if label else value
        start = _append_fragment(fragments, fragment)
        value_start = start + len(label) + 2 if label else start
        locations.append(_table_cell_location(
            file_format=file_format,
            start=value_start,
            end=value_start + len(value),
            row=line_number,
            column=column,
        ))


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _table_cell_location(*, file_format: str, start: int, end: int, row: int, column: int) -> dict[str, Any]:
    column_label = _column_label(column)
    return {
        "format": file_format,
        "label": f"row {row} column {column_label}",
        "start": start,
        "end": end,
        "selector": {
            "type": "tableCell",
            "row": row,
            "column": column,
            "columnLabel": column_label,
        },
    }


def _column_label(column: int) -> str:
    label = ""
    current = max(column, 1)
    while current:
        current, remainder = divmod(current - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label
