"""Source-local JSON extraction with structure-path locations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .source_text_decoding import decode_text_body

MAX_EXTRACTED_TEXT_CHARS = 300_000


@dataclass(frozen=True)
class JsonTextExtraction:
    text: str
    locations: tuple[dict[str, Any], ...]


class JsonExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_json_text(body: bytes, name: str, file_format: str, content_type: str = "") -> JsonTextExtraction:
    decoded = decode_text_body(body, content_type)
    records = _parse_ndjson(decoded, name) if file_format in {"jsonl", "ndjson"} else [_parse_json(decoded, name)]
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []

    for record_index, record in enumerate(records, start=1):
        line_number = record_index if file_format in {"jsonl", "ndjson"} else None
        _append_json_value(
            record,
            fragments,
            locations,
            file_format=file_format,
            path_parts=(),
            field_path=(),
            record_index=record_index if file_format in {"jsonl", "ndjson"} else None,
            line_number=line_number,
            label=None,
        )

    return _joined_extraction(fragments, locations, name)


def _parse_json(decoded: str, name: str) -> Any:
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as error:
        raise JsonExtractionIssue(f"{name} contains malformed JSON.") from error


def _parse_ndjson(decoded: str, name: str) -> list[Any]:
    records: list[Any] = []
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise JsonExtractionIssue(f"{name} contains malformed NDJSON at line {line_number}.") from error
    if not records:
        raise JsonExtractionIssue(f"{name} has no extractable JSON records.", recognition_difficulty="hard")
    return records


def _append_json_value(
    value: Any,
    fragments: list[str],
    locations: list[dict[str, Any]],
    *,
    file_format: str,
    path_parts: tuple[str, ...],
    field_path: tuple[int, ...],
    record_index: int | None,
    line_number: int | None,
    label: str | None,
) -> None:
    if isinstance(value, dict):
        for field_index, (key, child) in enumerate(value.items(), start=1):
            _append_json_value(
                child,
                fragments,
                locations,
                file_format=file_format,
                path_parts=(*path_parts, f"field[{field_index}]"),
                field_path=(*field_path, field_index),
                record_index=record_index,
                line_number=line_number,
                label=str(key),
            )
        return

    if isinstance(value, list):
        for item_index, child in enumerate(value, start=1):
            _append_json_value(
                child,
                fragments,
                locations,
                file_format=file_format,
                path_parts=(*path_parts, f"item[{item_index}]"),
                field_path=field_path,
                record_index=record_index,
                line_number=line_number,
                label=label,
            )
        return

    scalar_text = _scalar_text(value)
    if not scalar_text:
        return

    fragment = f"{label}: {scalar_text}" if label else scalar_text
    start = _append_fragment(fragments, fragment)
    value_start = start + len(label) + 2 if label else start
    selector = _selector(
        file_format=file_format,
        path_parts=path_parts,
        field_path=field_path,
        record_index=record_index,
        line_number=line_number,
    )
    locations.append({
        "format": file_format,
        "label": selector["blockLabel"],
        "start": value_start,
        "end": value_start + len(scalar_text),
        "selector": selector,
    })


def _selector(
    *,
    file_format: str,
    path_parts: tuple[str, ...],
    field_path: tuple[int, ...],
    record_index: int | None,
    line_number: int | None,
) -> dict[str, Any]:
    path_prefix = (f"record[{record_index}]",) if record_index is not None else ()
    path = "/" + "/".join((*path_prefix, *path_parts)) if path_parts or path_prefix else "/value"
    ordinal = ".".join(str(part) for part in field_path) if field_path else "value"
    label_prefix = "NDJSON record" if file_format == "ndjson" else "JSONL record" if file_format == "jsonl" else "JSON"
    block_label = f"{label_prefix} {record_index} field {ordinal}" if record_index is not None else f"JSON field {ordinal}"
    selector: dict[str, Any] = {
        "type": "structurePath",
        "path": path,
        "blockLabel": block_label,
    }
    if record_index is not None:
        selector["recordIndex"] = record_index
    if line_number is not None:
        selector["lineNumber"] = line_number
    if field_path:
        selector["fieldIndex"] = field_path[-1]
    return selector


def _scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _joined_extraction(
    fragments: list[str],
    locations: list[dict[str, Any]],
    name: str,
) -> JsonTextExtraction:
    text = "\n".join(fragments)
    if not text.strip():
        raise JsonExtractionIssue(f"{name} has no extractable JSON scalar text.", recognition_difficulty="hard")
    bounded_text = text[:MAX_EXTRACTED_TEXT_CHARS]
    bounded_locations = tuple(location for location in locations if location["start"] < len(bounded_text))
    return JsonTextExtraction(bounded_text, bounded_locations)
