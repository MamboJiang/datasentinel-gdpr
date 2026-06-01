"""Redacted source-review preview packages for authorized finding review."""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

from .signal_evidence_anchors import redacted_marker
from .source_format_recognition import SourceDocument

MAX_CONTEXT_CHARS = 260
CONTEXT_MARGIN_CHARS = 90
EMAIL_CONTEXT_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_CONTEXT_RE = re.compile(r"\b(?:\+\d{1,3}[ -]?)?(?:\(?\d{2,4}\)?[ -]?){2,4}\d{2,4}\b")
LONG_DIGIT_CONTEXT_RE = re.compile(r"\b\d(?:[ -]?\d){7,}\b")


def build_source_review_preview(document: SourceDocument, signals: list[dict[str, Any]]) -> dict[str, Any]:
    context_windows = _context_windows(document.text, signals)
    anchors = [_preview_anchor(signal, context_windows) for signal in signals]
    anchors = [anchor for anchor in anchors if anchor]
    pages = _preview_pages(anchors)
    anchor_contexts = [anchor["contextWindow"] for anchor in anchors if isinstance(anchor.get("contextWindow"), dict)]

    return {
        "sourcePreviewId": _preview_id(document, anchors),
        "sourceName": document.name,
        "fileFormat": document.file_format,
        "extractionMethod": document.extraction_method,
        "recognitionDifficulty": document.recognition_difficulty,
        "redactionMode": "anchor_only",
        "rawContentExposed": False,
        "pageImagesExposed": False,
        "anchors": anchors,
        "contextWindows": anchor_contexts,
        "pages": pages,
        "textRanges": [anchor for anchor in anchors if anchor["selector"].get("type") == "textPosition"],
        "tableCells": [anchor for anchor in anchors if anchor["selector"].get("type") == "tableCell"],
        "structureBlocks": [anchor for anchor in anchors if anchor["selector"].get("type") == "structurePath"],
        "warnings": [] if anchors else ["No redacted evidence anchors were available for source review."],
    }


def _preview_anchor(signal: dict[str, Any], context_windows: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    anchor = signal.get("evidenceAnchor")
    if not isinstance(anchor, dict):
        return None
    selector = anchor.get("selector")
    if not isinstance(selector, dict):
        return None

    anchor_id = str(anchor.get("anchorId") or "")
    preview = {
        "anchorId": anchor_id,
        "label": str(anchor.get("label") or signal.get("type") or "Evidence"),
        "format": str(anchor.get("format") or "text"),
        "redactedText": str(anchor.get("redactedText") or signal.get("snippet") or "")[:180],
        "fallbackLabel": _fallback_label(anchor),
        "selector": _safe_selector(selector),
        "confidence": signal.get("confidence"),
        "rawContentExposed": False,
    }
    if anchor_id in context_windows:
        preview["contextWindow"] = context_windows[anchor_id]
    return preview


def _fallback_label(anchor: dict[str, Any]) -> str:
    fallback = anchor.get("fallback")
    if isinstance(fallback, dict) and isinstance(fallback.get("label"), str):
        return fallback["label"]
    return "Source location"


def _safe_selector(selector: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in (
        "type",
        "start",
        "end",
        "sourceStart",
        "sourceEnd",
        "page",
        "row",
        "column",
        "columnLabel",
        "sheetName",
        "path",
        "partName",
        "paragraphIndex",
        "slideNumber",
        "shapeIndex",
        "tagName",
        "nodeIndex",
        "recordIndex",
        "lineNumber",
        "columnNumber",
        "fieldIndex",
        "elementIndex",
        "attributeIndex",
        "blockLabel",
        "frameIndex",
    ):
        if key in selector:
            safe[key] = selector[key]
    region = selector.get("pageRegion")
    if isinstance(region, dict):
        safe["pageRegion"] = {
            key: region[key]
            for key in ("x", "y", "width", "height", "pageWidth", "pageHeight", "unit", "origin", "confidence", "ocrConfidence")
            if key in region
        }
    return safe


def _context_windows(text: str, signals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not text:
        return {}

    spans = _signal_spans(text, signals)
    windows: dict[str, dict[str, Any]] = {}
    for span in spans:
        window = _context_window(text, span, spans)
        if window:
            windows[span["anchorId"]] = window
    return windows


def _signal_spans(text: str, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for signal in signals:
        anchor = signal.get("evidenceAnchor")
        if not isinstance(anchor, dict):
            continue
        selector = anchor.get("selector")
        if not isinstance(selector, dict):
            continue
        start = selector.get("start")
        end = selector.get("end")
        anchor_id = anchor.get("anchorId")
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(anchor_id, str):
            continue
        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))
        if start == end:
            continue
        spans.append({
            "anchorId": anchor_id,
            "start": start,
            "end": end,
            "marker": redacted_marker(str(anchor.get("redactedText") or signal.get("snippet") or "")),
        })
    return sorted(spans, key=lambda span: (span["start"], span["end"]))


def _context_window(text: str, target: dict[str, Any], spans: list[dict[str, Any]]) -> dict[str, Any] | None:
    start = int(target["start"])
    end = int(target["end"])
    context_start, context_end = _context_bounds(text, start, end)
    overlapping = [
        span for span in spans
        if span["start"] < context_end and context_start < span["end"]
    ]
    redacted_text, highlight = _redacted_context_text(text, context_start, context_end, target["anchorId"], overlapping)
    redacted_text, highlight = _trim_context(redacted_text, highlight)
    if not redacted_text:
        return None

    return {
        "anchorId": target["anchorId"],
        "redactedContext": redacted_text,
        "contextStart": context_start,
        "contextEnd": context_end,
        "highlightStart": highlight[0],
        "highlightEnd": highlight[1],
        "redactionMode": "signal_span_context",
        "rawContentExposed": False,
    }


def _context_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)

    context_start = max(line_start, start - CONTEXT_MARGIN_CHARS)
    context_end = min(line_end, end + CONTEXT_MARGIN_CHARS)
    if context_end - context_start > MAX_CONTEXT_CHARS:
        target_mid = (start + end) // 2
        context_start = max(line_start, target_mid - MAX_CONTEXT_CHARS // 2)
        context_end = min(line_end, context_start + MAX_CONTEXT_CHARS)
        context_start = max(line_start, context_end - MAX_CONTEXT_CHARS)
    return context_start, context_end


def _redacted_context_text(
    text: str,
    context_start: int,
    context_end: int,
    target_anchor_id: str,
    spans: list[dict[str, Any]],
) -> tuple[str, tuple[int, int]]:
    fragments: list[str] = []
    cursor = context_start
    highlight = (0, 0)

    for span in spans:
        span_start = max(context_start, int(span["start"]))
        span_end = min(context_end, int(span["end"]))
        if span_end <= cursor:
            continue
        if span_start > cursor:
            fragments.append(_scrub_plain_context(text[cursor:span_start]))

        marker = str(span["marker"])
        current_offset = sum(len(fragment) for fragment in fragments)
        fragments.append(marker)
        if span["anchorId"] == target_anchor_id:
            highlight = (current_offset, current_offset + len(marker))
        cursor = span_end

    if cursor < context_end:
        fragments.append(_scrub_plain_context(text[cursor:context_end]))

    redacted = "".join(fragments).strip()
    if highlight == (0, 0):
        marker = str(next((span["marker"] for span in spans if span["anchorId"] == target_anchor_id), ""))
        marker_index = redacted.find(marker) if marker else -1
        if marker_index >= 0:
            highlight = (marker_index, marker_index + len(marker))
    return redacted, highlight


def _scrub_plain_context(value: str) -> str:
    scrubbed = EMAIL_CONTEXT_RE.sub("[REDACTED_EMAIL]", value)
    scrubbed = PHONE_CONTEXT_RE.sub("[REDACTED_PHONE]", scrubbed)
    scrubbed = LONG_DIGIT_CONTEXT_RE.sub("[REDACTED_NUMBER]", scrubbed)
    return _scrub_label_values(scrubbed)


def _scrub_label_values(value: str) -> str:
    pieces = re.split(r"([;,|\t])", value)
    scrubbed: list[str] = []
    for piece in pieces:
        if piece in {";", ",", "|", "\t"}:
            scrubbed.append(piece)
            continue
        separator_index = _label_separator_index(piece)
        if separator_index is None:
            scrubbed.append(piece)
            continue
        value_part = piece[separator_index + 1:].strip()
        if not value_part or value_part.startswith("[REDACTED_"):
            scrubbed.append(piece)
            continue
        scrubbed.append(f"{piece[:separator_index + 1]} [REDACTED_CONTEXT]")
    return "".join(scrubbed)


def _label_separator_index(value: str) -> int | None:
    colon = value.find(":")
    full_width_colon = value.find("：")
    candidates = [index for index in (colon, full_width_colon) if index >= 0]
    return min(candidates) if candidates else None


def _trim_context(value: str, highlight: tuple[int, int]) -> tuple[str, tuple[int, int]]:
    leading = len(value) - len(value.lstrip())
    trimmed = value.strip()
    if not trimmed:
        return "", (0, 0)
    start, end = highlight
    if end <= leading:
        return trimmed, (0, 0)
    return trimmed, (max(0, start - leading), max(0, end - leading))


def _preview_pages(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages: dict[int, dict[str, Any]] = {}
    for anchor in anchors:
        selector = anchor["selector"]
        region = selector.get("pageRegion")
        if not isinstance(region, dict):
            continue
        page_number = selector.get("page") if isinstance(selector.get("page"), int) else 1
        frame_index = selector.get("frameIndex") if isinstance(selector.get("frameIndex"), int) else None
        page = pages.setdefault(page_number, _page_record(page_number, region, frame_index))
        page["regions"].append({
            "anchorId": anchor["anchorId"],
            "label": anchor["label"],
            "redactedText": anchor["redactedText"],
            "region": region,
            "rawContentExposed": False,
        })
    return [pages[number] for number in sorted(pages)]


def _page_record(page_number: int, region: dict[str, Any], frame_index: int | None = None) -> dict[str, Any]:
    unit = str(region.get("unit") or "pt")
    origin = str(region.get("origin") or "bottom_left")
    return {
        "page": page_number,
        "label": f"Frame {frame_index}" if frame_index else f"Page {page_number}",
        "unit": unit,
        "origin": origin,
        "coordinateSystem": "image_pixels_top_left" if origin == "top_left" or unit == "px" else "pdf_user_space_points_bottom_left",
        "width": region.get("pageWidth"),
        "height": region.get("pageHeight"),
        "regions": [],
        "pageImageExposed": False,
    }


def _preview_id(document: SourceDocument, anchors: list[dict[str, Any]]) -> str:
    anchor_ids = ",".join(anchor["anchorId"] for anchor in anchors)
    fingerprint = sha256(f"{document.name}:{document.file_format}:{anchor_ids}".encode("utf-8")).hexdigest()[:12]
    return f"source_preview_{fingerprint}"
