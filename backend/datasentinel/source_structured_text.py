"""Source-local structured document extraction with structure-path locations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZipFile

from .source_text_decoding import decode_text_body

MAX_EXTRACTED_TEXT_CHARS = 300_000


@dataclass(frozen=True)
class StructuredTextExtraction:
    text: str
    locations: tuple[dict[str, Any], ...]


class StructuredExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_docx_text(body: bytes, name: str, *, max_xml_bytes: int, max_member_bytes: int) -> StructuredTextExtraction:
    try:
        with ZipFile(BytesIO(body)) as archive:
            _validate_ooxml_budget(archive, name, max_xml_bytes, max_member_bytes)
            return _extract_ooxml_blocks(
                archive,
                name,
                _is_docx_text_part,
                "docx",
                _docx_selector,
            )
    except (BadZipFile, LargeZipFile) as error:
        raise StructuredExtractionIssue(f"{name} is not a readable Office Open XML package.") from error


def extract_pptx_text(body: bytes, name: str, *, max_xml_bytes: int, max_member_bytes: int) -> StructuredTextExtraction:
    try:
        with ZipFile(BytesIO(body)) as archive:
            _validate_ooxml_budget(archive, name, max_xml_bytes, max_member_bytes)
            return _extract_ooxml_blocks(
                archive,
                name,
                _is_pptx_text_part,
                "pptx",
                _pptx_selector,
            )
    except (BadZipFile, LargeZipFile) as error:
        raise StructuredExtractionIssue(f"{name} is not a readable Office Open XML package.") from error


def extract_html_text(body: bytes, name: str, file_format: str = "html", content_type: str = "") -> StructuredTextExtraction:
    parser = _HtmlStructureParser(file_format)
    parser.feed(decode_text_body(body, content_type))
    return _joined_extraction(parser.fragments, parser.locations, name, empty_difficulty="hard", empty_label="extractable HTML text")


def extract_xml_text(body: bytes, name: str, content_type: str = "") -> StructuredTextExtraction:
    try:
        source: bytes | str = decode_text_body(body, content_type) if "charset=" in content_type.lower() else body
        root = ElementTree.fromstring(source)
    except ElementTree.ParseError as error:
        raise StructuredExtractionIssue(f"{name} contains malformed XML.") from error

    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    _append_xml_element(root, (1,), fragments, locations)
    return _joined_extraction(fragments, locations, name, empty_difficulty="hard", empty_label="extractable XML scalar text")


def _extract_ooxml_blocks(
    archive: ZipFile,
    name: str,
    predicate: Any,
    file_format: str,
    selector_builder: Any,
) -> StructuredTextExtraction:
    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    for part_name in _matching_members(archive, predicate):
        try:
            root = ElementTree.fromstring(archive.read(part_name))
        except ElementTree.ParseError as error:
            raise StructuredExtractionIssue(f"{name} contains malformed Office XML.") from error
        blocks = _block_elements(root, file_format)
        if not blocks:
            blocks = [root]
        for block_index, block in enumerate(blocks, start=1):
            text = _block_text(block)
            if not text:
                continue
            start = _append_fragment(fragments, text)
            selector = selector_builder(part_name, block_index)
            locations.append({
                "format": file_format,
                "label": selector["label"],
                "start": start,
                "end": start + len(text),
                "selector": selector["selector"],
            })
    return _joined_extraction(fragments, locations, name)


def _block_elements(root: ElementTree.Element, file_format: str) -> list[ElementTree.Element]:
    if file_format == "docx":
        return [element for element in root.iter() if _local_name(element.tag) == "p"]
    return [element for element in root.iter() if _local_name(element.tag) == "sp"]


def _block_text(block: ElementTree.Element) -> str:
    return "\n".join(
        text.strip()
        for text in (element.text for element in block.iter() if _local_name(element.tag) == "t")
        if text and text.strip()
    )


def _docx_selector(part_name: str, paragraph_index: int) -> dict[str, Any]:
    label = f"DOCX paragraph {paragraph_index}"
    return {
        "label": label,
        "selector": {
            "type": "structurePath",
            "path": f"{part_name}#paragraph:{paragraph_index}",
            "partName": part_name,
            "paragraphIndex": paragraph_index,
            "blockLabel": label,
        },
    }


def _pptx_selector(part_name: str, shape_index: int) -> dict[str, Any]:
    slide_number = _slide_number(part_name)
    label = f"Slide {slide_number} shape {shape_index}" if slide_number else f"PPTX shape {shape_index}"
    selector: dict[str, Any] = {
        "type": "structurePath",
        "path": f"{part_name}#shape:{shape_index}",
        "partName": part_name,
        "shapeIndex": shape_index,
        "blockLabel": label,
    }
    if slide_number:
        selector["slideNumber"] = slide_number
    return {"label": label, "selector": selector}


def _slide_number(part_name: str) -> int | None:
    match = re.search(r"slide(\d+)\.xml$", part_name)
    if not match:
        return None
    return int(match.group(1))


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _joined_extraction(
    fragments: list[str],
    locations: list[dict[str, Any]],
    name: str,
    *,
    empty_difficulty: str = "hard",
    empty_label: str = "extractable Office text",
) -> StructuredTextExtraction:
    text = "\n".join(fragments)
    if not text.strip():
        raise StructuredExtractionIssue(f"{name} has no {empty_label}.", recognition_difficulty=empty_difficulty)
    return StructuredTextExtraction(text[:MAX_EXTRACTED_TEXT_CHARS], tuple(locations))


def _validate_ooxml_budget(archive: ZipFile, name: str, max_xml_bytes: int, max_member_bytes: int) -> None:
    total = 0
    for info in archive.infolist():
        if info.is_dir() or not info.filename.endswith(".xml"):
            continue
        if info.file_size > max_member_bytes:
            raise StructuredExtractionIssue(f"{name} has an Office XML part over the prelaunch extraction limit.")
        total += info.file_size
        if total > max_xml_bytes:
            raise StructuredExtractionIssue(f"{name} exceeds the prelaunch Office XML extraction limit.")


def _matching_members(archive: ZipFile, predicate: Any) -> list[str]:
    return sorted(info.filename for info in archive.infolist() if not info.is_dir() and predicate(info.filename))


def _is_docx_text_part(filename: str) -> bool:
    return filename == "word/document.xml" or (
        filename.startswith("word/")
        and filename.endswith(".xml")
        and Path(filename).name.startswith(("header", "footer", "footnotes", "endnotes", "comments"))
    )


def _is_pptx_text_part(filename: str) -> bool:
    return (
        filename.startswith("ppt/slides/slide")
        or filename.startswith("ppt/notesSlides/notesSlide")
    ) and filename.endswith(".xml")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _append_xml_element(
    element: ElementTree.Element,
    ordinal_path: tuple[int, ...],
    fragments: list[str],
    locations: list[dict[str, Any]],
) -> None:
    label = _local_name(element.tag)
    for attribute_index, (attribute_name, attribute_value) in enumerate(element.attrib.items(), start=1):
        _append_xml_scalar(
            _local_name(attribute_name),
            attribute_value,
            ordinal_path,
            fragments,
            locations,
            attribute_index=attribute_index,
        )

    if element.text and element.text.strip():
        _append_xml_scalar(label, element.text.strip(), ordinal_path, fragments, locations)

    for child_index, child in enumerate(list(element), start=1):
        _append_xml_element(child, (*ordinal_path, child_index), fragments, locations)


def _append_xml_scalar(
    label: str,
    value: str,
    ordinal_path: tuple[int, ...],
    fragments: list[str],
    locations: list[dict[str, Any]],
    *,
    attribute_index: int | None = None,
) -> None:
    cleaned_value = " ".join(value.split())
    if not cleaned_value:
        return

    fragment = f"{label}: {cleaned_value}"
    start = _append_fragment(fragments, fragment)
    value_start = start + len(label) + 2
    selector = _xml_selector(ordinal_path, attribute_index)
    locations.append({
        "format": "xml",
        "label": selector["blockLabel"],
        "start": value_start,
        "end": value_start + len(cleaned_value),
        "selector": selector,
    })


def _xml_selector(ordinal_path: tuple[int, ...], attribute_index: int | None) -> dict[str, Any]:
    element_path = "/" + "/".join(f"element[{index}]" for index in ordinal_path)
    element_ordinal = ".".join(str(index) for index in ordinal_path)
    selector: dict[str, Any] = {
        "type": "structurePath",
        "path": element_path if attribute_index is None else f"{element_path}/attribute[{attribute_index}]",
        "elementIndex": ordinal_path[-1],
        "blockLabel": f"XML element {element_ordinal}" if attribute_index is None else f"XML element {element_ordinal} attribute {attribute_index}",
    }
    if attribute_index is not None:
        selector["attributeIndex"] = attribute_index
    return selector


class _HtmlStructureParser(HTMLParser):
    def __init__(self, file_format: str) -> None:
        super().__init__(convert_charrefs=True)
        self.file_format = file_format
        self.fragments: list[str] = []
        self.locations: list[dict[str, Any]] = []
        self.stack: list[tuple[str, int]] = []
        self.tag_counts: dict[tuple[str, ...], int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        parent_path = tuple(item[0] for item in self.stack)
        key = (*parent_path, tag.lower())
        index = self.tag_counts.get(key, 0) + 1
        self.tag_counts[key] = index
        self.stack.append((tag.lower(), index))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        while self.stack:
            current, _index = self.stack.pop()
            if current == lowered:
                break

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        start = _append_fragment(self.fragments, text)
        selector = self._selector()
        self.locations.append({
            "format": self.file_format,
            "label": selector["blockLabel"],
            "start": start,
            "end": start + len(text),
            "selector": selector,
        })

    def _selector(self) -> dict[str, Any]:
        path = "/" + "/".join(f"{tag}[{index}]" for tag, index in self.stack)
        tag_name = self.stack[-1][0] if self.stack else "text"
        node_index = self.stack[-1][1] if self.stack else len(self.fragments)
        label = f"HTML {tag_name} {node_index}"
        return {
            "type": "structurePath",
            "path": path,
            "tagName": tag_name,
            "nodeIndex": node_index,
            "blockLabel": label,
        }
