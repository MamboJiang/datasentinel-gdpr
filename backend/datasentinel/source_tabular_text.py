"""Source-local tabular text extraction with cell-level locations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZipFile

from .source_text_decoding import decode_text_body


@dataclass(frozen=True)
class TabularTextExtraction:
    text: str
    locations: tuple[dict[str, Any], ...]


class TabularExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_delimited_text(body: bytes, name: str, *, delimiter: str, file_format: str, content_type: str = "") -> TabularTextExtraction:
    decoded = decode_text_body(body, content_type)
    rows = _read_rows(decoded, delimiter, file_format)
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    header = _header_row(rows)

    for row_index, row in enumerate(rows, start=1):
        cells = [cell.strip() for cell in row]
        nonempty = [(index + 1, value) for index, value in enumerate(cells) if value]
        if not nonempty:
            continue
        if header and row_index == header["row"]:
            continue
        if header and not header["label_value_table"]:
            _append_header_value_row(file_format, header["cells"], row_index, cells, fragments, locations)
            continue
        if len(nonempty) >= 2 and _looks_like_label_value_row(nonempty):
            label_column, label = nonempty[0]
            value_column, value = nonempty[1]
            start = _append_fragment(fragments, f"{label}: {value}")
            value_start = start + len(label) + 2
            locations.append(_table_cell_location(
                file_format=file_format,
                start=value_start,
                end=value_start + len(value),
                row=row_index,
                column=value_column,
            ))
            locations.append(_table_cell_location(
                file_format=file_format,
                start=start,
                end=start + len(label),
                row=row_index,
                column=label_column,
            ))
            continue

        for column_index, value in nonempty:
            start = _append_fragment(fragments, value)
            locations.append(_table_cell_location(
                file_format=file_format,
                start=start,
                end=start + len(value),
                row=row_index,
                column=column_index,
            ))

    text = "\n".join(fragments)
    if not text.strip():
        raise TabularExtractionIssue(f"{name} has no extractable tabular text.", recognition_difficulty="hard")
    return TabularTextExtraction(text, tuple(locations))


def _read_rows(decoded: str, delimiter: str, file_format: str) -> list[list[str]]:
    if file_format == "csv":
        try:
            dialect = csv.Sniffer().sniff(decoded[:8192], delimiters=",;\t|")
            return list(csv.reader(StringIO(decoded), dialect))
        except csv.Error:
            pass
    return list(csv.reader(StringIO(decoded), delimiter=delimiter))


def _header_row(rows: list[list[str]]) -> dict[str, Any] | None:
    for row_index, row in enumerate(rows, start=1):
        cells = [cell.strip() for cell in row]
        nonempty = [cell for cell in cells if cell]
        if not nonempty:
            continue
        if len(nonempty) < 2:
            return None
        normalized = [_normalize_header(cell) for cell in cells]
        return {
            "row": row_index,
            "cells": cells,
            "label_value_table": _looks_like_label_value_header(normalized),
        }
    return None


def _looks_like_label_value_header(normalized: list[str]) -> bool:
    if len(normalized) < 2:
        return False
    first = normalized[0]
    second = normalized[1]
    return first in {"field", "field name", "label", "key", "attribute", "property"} and second in {"value", "data", "content"}


def _append_header_value_row(
    file_format: str,
    header_cells: list[str],
    row_index: int,
    cells: list[str],
    fragments: list[str],
    locations: list[dict[str, Any]],
) -> None:
    for column_index, value in enumerate(cells, start=1):
        value = value.strip()
        if not value:
            continue
        label = header_cells[column_index - 1].strip() if column_index <= len(header_cells) else ""
        if not label:
            start = _append_fragment(fragments, value)
            locations.append(_table_cell_location(
                file_format=file_format,
                start=start,
                end=start + len(value),
                row=row_index,
                column=column_index,
            ))
            continue
        fragment = f"{label}: {value}"
        start = _append_fragment(fragments, fragment)
        value_start = start + len(label) + 2
        locations.append(_table_cell_location(
            file_format=file_format,
            start=value_start,
            end=value_start + len(value),
            row=row_index,
            column=column_index,
        ))


def _normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def extract_xlsx_text(body: bytes, name: str, *, max_xml_bytes: int, max_member_bytes: int) -> TabularTextExtraction:
    try:
        with ZipFile(BytesIO(body)) as archive:
            _validate_xlsx_budget(archive, name, max_xml_bytes, max_member_bytes)
            shared_strings = _xlsx_shared_strings(archive, name)
            fragments: list[str] = []
            locations: list[dict[str, Any]] = []
            for sheet_number, part_name in enumerate(_matching_members(archive, _is_xlsx_sheet_part), start=1):
                sheet_name = f"Sheet{sheet_number}"
                _append_xlsx_sheet(
                    archive.read(part_name),
                    shared_strings,
                    name,
                    sheet_name,
                    fragments,
                    locations,
                )
    except (BadZipFile, LargeZipFile) as error:
        raise TabularExtractionIssue(f"{name} is not a readable Office Open XML package.") from error

    text = "\n".join(fragments)
    if not text.strip():
        raise TabularExtractionIssue(f"{name} has no extractable Office text.", recognition_difficulty="hard")
    return TabularTextExtraction(text, tuple(locations))


def _append_xlsx_sheet(
    xml_bytes: bytes,
    shared_strings: list[str],
    name: str,
    sheet_name: str,
    fragments: list[str],
    locations: list[dict[str, Any]],
) -> None:
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as error:
        raise TabularExtractionIssue(f"{name} contains malformed worksheet XML.") from error

    rows: dict[int, list[tuple[int, str]]] = {}
    for cell in root.iter():
        if _local_name(cell.tag) != "c":
            continue
        value = _xlsx_cell_text(cell, shared_strings)
        if not value:
            continue
        row, column = _cell_reference(cell.attrib.get("r"))
        rows.setdefault(row, []).append((column, value.strip()))

    for row_index in sorted(rows):
        nonempty = [(column, value) for column, value in sorted(rows[row_index]) if value]
        if not nonempty:
            continue
        if len(nonempty) >= 2 and _looks_like_label_value_row(nonempty):
            label_column, label = nonempty[0]
            value_column, value = nonempty[1]
            start = _append_fragment(fragments, f"{label}: {value}")
            value_start = start + len(label) + 2
            locations.append(_table_cell_location(
                file_format="xlsx",
                start=value_start,
                end=value_start + len(value),
                row=row_index,
                column=value_column,
                sheet_name=sheet_name,
            ))
            locations.append(_table_cell_location(
                file_format="xlsx",
                start=start,
                end=start + len(label),
                row=row_index,
                column=label_column,
                sheet_name=sheet_name,
            ))
            continue
        for column_index, value in nonempty:
            for line in [line.strip() for line in value.splitlines() if line.strip()]:
                start = _append_fragment(fragments, line)
                locations.append(_table_cell_location(
                    file_format="xlsx",
                    start=start,
                    end=start + len(line),
                    row=row_index,
                    column=column_index,
                    sheet_name=sheet_name,
                ))


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _looks_like_label_value_row(nonempty: list[tuple[int, str]]) -> bool:
    label = nonempty[0][1]
    value = nonempty[1][1]
    return 0 < len(label) <= 72 and len(value) >= 2 and ":" not in label and "：" not in label


def _table_cell_location(
    *,
    file_format: str,
    start: int,
    end: int,
    row: int,
    column: int,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    column_label = _column_label(column)
    label = f"{sheet_name + ' ' if sheet_name else ''}row {row} column {column_label}"
    selector: dict[str, Any] = {
        "type": "tableCell",
        "row": row,
        "column": column,
        "columnLabel": column_label,
    }
    if sheet_name:
        selector["sheetName"] = sheet_name
    return {
        "format": file_format,
        "label": label,
        "start": start,
        "end": end,
        "selector": selector,
    }


def _xlsx_cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        index_text = _first_child_text(cell, "v")
        if index_text and index_text.isdigit():
            index = int(index_text)
            if index < len(shared_strings):
                return shared_strings[index]
        return ""
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter() if _local_name(node.tag) == "t")
    return _first_child_text(cell, "v") or ""


def _xlsx_shared_strings(archive: ZipFile, name: str) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except ElementTree.ParseError as error:
        raise TabularExtractionIssue(f"{name} contains malformed shared strings.") from error

    values: list[str] = []
    for item in root:
        if _local_name(item.tag) != "si":
            continue
        values.append("".join(node.text or "" for node in item.iter() if _local_name(node.tag) == "t"))
    return values


def _validate_xlsx_budget(archive: ZipFile, name: str, max_xml_bytes: int, max_member_bytes: int) -> None:
    total = 0
    for info in archive.infolist():
        if info.is_dir() or not info.filename.endswith(".xml"):
            continue
        if info.file_size > max_member_bytes:
            raise TabularExtractionIssue(f"{name} has an Office XML part over the prelaunch extraction limit.")
        total += info.file_size
        if total > max_xml_bytes:
            raise TabularExtractionIssue(f"{name} exceeds the prelaunch Office XML extraction limit.")


def _matching_members(archive: ZipFile, predicate: Any) -> list[str]:
    return sorted(info.filename for info in archive.infolist() if not info.is_dir() and predicate(info.filename))


def _is_xlsx_sheet_part(filename: str) -> bool:
    return filename.startswith("xl/worksheets/sheet") and filename.endswith(".xml")


def _first_child_text(element: ElementTree.Element, local_name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == local_name:
            return child.text
    return None


def _cell_reference(reference: str | None) -> tuple[int, int]:
    if not reference:
        return 1, 1
    letters = "".join(character for character in reference if character.isalpha())
    digits = "".join(character for character in reference if character.isdigit())
    column = 0
    for character in letters.upper():
        column = column * 26 + ord(character) - ord("A") + 1
    return int(digits or "1"), max(column, 1)


def _column_label(column: int) -> str:
    label = ""
    current = max(column, 1)
    while current:
        current, remainder = divmod(current - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
