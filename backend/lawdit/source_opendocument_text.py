"""Bounded OpenDocument text extraction with source-local anchors."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZipFile

MAX_EXTRACTED_TEXT_CHARS = 300_000
MAX_REPEAT_COUNT = 256


@dataclass(frozen=True)
class OpenDocumentTextExtraction:
    text: str
    file_format: str
    extraction_method: str
    locations: tuple[dict[str, Any], ...]


class OpenDocumentExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_opendocument_text(
    body: bytes,
    name: str,
    file_format: str,
    *,
    max_xml_bytes: int,
    max_member_bytes: int,
) -> OpenDocumentTextExtraction:
    try:
        with ZipFile(BytesIO(body)) as archive:
            _validate_package(archive, name, max_xml_bytes, max_member_bytes)
            content_xml = archive.read("content.xml")
    except (BadZipFile, LargeZipFile) as error:
        raise OpenDocumentExtractionIssue(f"{name} is not a readable OpenDocument package.") from error

    root = _parse_content(content_xml, name)
    if file_format == "ods":
        text, locations = _extract_spreadsheet(root, name)
    else:
        text, locations = _extract_blocks(root, name, file_format)
    return OpenDocumentTextExtraction(text, file_format, f"odf_{file_format}_text", locations)


def _extract_blocks(root: ElementTree.Element, name: str, file_format: str) -> tuple[str, tuple[dict[str, Any], ...]]:
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    for block_index, block in enumerate(_text_blocks(root), start=1):
        text = _element_text(block)
        if not text:
            continue
        start = _append_fragment(fragments, text)
        label = f"{file_format.upper()} paragraph {block_index}"
        locations.append({
            "format": file_format,
            "label": label,
            "start": start,
            "end": start + len(text),
            "selector": {
                "type": "structurePath",
                "path": f"content.xml#paragraph:{block_index}",
                "partName": "content.xml",
                "paragraphIndex": block_index,
                "blockLabel": label,
            },
        })
    return _joined_extraction(fragments, locations, name, "extractable OpenDocument text")


def _extract_spreadsheet(root: ElementTree.Element, name: str) -> tuple[str, tuple[dict[str, Any], ...]]:
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    for sheet_number, table in enumerate(_tables(root), start=1):
        row_number = 0
        sheet_name = f"Sheet{sheet_number}"
        for row in [child for child in table if _local_name(child.tag) == "table-row"]:
            for _index in range(_repeat_count(row, "number-rows-repeated")):
                row_number += 1
                _append_spreadsheet_row(row, sheet_name, row_number, fragments, locations)
    return _joined_extraction(fragments, locations, name, "extractable OpenDocument spreadsheet text")


def _append_spreadsheet_row(
    row: ElementTree.Element,
    sheet_name: str,
    row_number: int,
    fragments: list[str],
    locations: list[dict[str, Any]],
) -> None:
    cells = _row_cells(row)
    if not cells:
        return
    if len(cells) >= 2 and _looks_like_label_value_row(cells):
        label_column, label = cells[0]
        value_column, value = cells[1]
        start = _append_fragment(fragments, f"{label}: {value}")
        value_start = start + len(label) + 2
        locations.append(_table_cell_location(value_start, value_start + len(value), row_number, value_column, sheet_name))
        locations.append(_table_cell_location(start, start + len(label), row_number, label_column, sheet_name))
        return
    for column_number, value in cells:
        start = _append_fragment(fragments, value)
        locations.append(_table_cell_location(start, start + len(value), row_number, column_number, sheet_name))


def _row_cells(row: ElementTree.Element) -> list[tuple[int, str]]:
    cells: list[tuple[int, str]] = []
    column_number = 0
    for cell in [child for child in row if _local_name(child.tag) in {"table-cell", "covered-table-cell"}]:
        text = _element_text(cell)
        for _index in range(_repeat_count(cell, "number-columns-repeated")):
            column_number += 1
            if text:
                cells.append((column_number, text))
    return cells


def _table_cell_location(start: int, end: int, row: int, column: int, sheet_name: str) -> dict[str, Any]:
    column_label = _column_label(column)
    return {
        "format": "ods",
        "label": f"{sheet_name} row {row} column {column_label}",
        "start": start,
        "end": end,
        "selector": {
            "type": "tableCell",
            "row": row,
            "column": column,
            "columnLabel": column_label,
            "sheetName": sheet_name,
        },
    }


def _text_blocks(root: ElementTree.Element) -> list[ElementTree.Element]:
    return [element for element in root.iter() if _local_name(element.tag) in {"h", "p"} and _element_text(element)]


def _tables(root: ElementTree.Element) -> list[ElementTree.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == "table"]


def _element_text(element: ElementTree.Element) -> str:
    return " ".join(text.strip() for text in element.itertext() if text and text.strip())


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _joined_extraction(
    fragments: list[str],
    locations: list[dict[str, Any]],
    name: str,
    empty_label: str,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    text = "\n".join(fragments)
    if not text.strip():
        raise OpenDocumentExtractionIssue(f"{name} has no {empty_label}.", recognition_difficulty="hard")
    return text[:MAX_EXTRACTED_TEXT_CHARS], tuple(locations)


def _validate_package(archive: ZipFile, name: str, max_xml_bytes: int, max_member_bytes: int) -> None:
    if "content.xml" not in archive.namelist():
        raise OpenDocumentExtractionIssue(f"{name} does not contain OpenDocument content.xml.")
    total = 0
    for info in archive.infolist():
        if info.is_dir() or not info.filename.endswith(".xml"):
            continue
        if info.file_size > max_member_bytes:
            raise OpenDocumentExtractionIssue(f"{name} has an OpenDocument XML part over the prelaunch extraction limit.")
        total += info.file_size
        if total > max_xml_bytes:
            raise OpenDocumentExtractionIssue(f"{name} exceeds the prelaunch OpenDocument XML extraction limit.")


def _parse_content(content_xml: bytes, name: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(content_xml)
    except ElementTree.ParseError as error:
        raise OpenDocumentExtractionIssue(f"{name} contains malformed OpenDocument XML.") from error


def _repeat_count(element: ElementTree.Element, local_attribute: str) -> int:
    value = next((value for key, value in element.attrib.items() if _local_name(key) == local_attribute), "1")
    if not value.isdigit():
        return 1
    if len(value) > 6:
        return MAX_REPEAT_COUNT
    return min(max(int(value), 1), MAX_REPEAT_COUNT)


def _looks_like_label_value_row(nonempty: list[tuple[int, str]]) -> bool:
    label = nonempty[0][1]
    value = nonempty[1][1]
    return 0 < len(label) <= 72 and len(value) >= 2 and ":" not in label and "：" not in label


def _column_label(column: int) -> str:
    label = ""
    current = max(column, 1)
    while current:
        current, remainder = divmod(current - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
