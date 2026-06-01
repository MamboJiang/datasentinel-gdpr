"""Public-safe evidence anchors for deterministic signal payloads."""

from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

REDACTED_MARKER_RE = re.compile(r"\[REDACTED_[A-Z0-9_]+\]")
SOURCE_REFERENCE_PREFIX = "source_reference:"


def text_position_anchor(signal_type: str, detector: str, start: int, end: int, line_number: int, redacted_text: str) -> dict[str, Any]:
    anchor_key = f"{signal_type}:{detector}:{start}:{end}"
    safe_text = redacted_text[:180]
    return {
        "anchorId": "anchor_" + sha256(anchor_key.encode("utf-8")).hexdigest()[:12],
        "format": "text",
        "label": display_type(signal_type),
        "redactedText": safe_text,
        "selector": {"type": "textPosition", "start": start, "end": end},
        "fallback": {"label": f"Line {line_number}", "redactedText": safe_text},
    }


def apply_source_locations(signals: list[dict[str, Any]], text_locations: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    if not text_locations:
        return signals
    return [_with_source_location(signal, text_locations) for signal in signals]


def sanitize_public_signal(signal: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(signal)
    signal_type = str(sanitized.get("type") or "value")
    snippet = str(sanitized.get("snippet") or "")
    marker = redacted_marker(snippet)
    sanitized["snippet"] = f"{display_type(signal_type)}: {marker}"[:180]
    if isinstance(sanitized.get("evidenceAnchor"), dict):
        sanitized["evidenceAnchor"] = sanitize_anchor(sanitized["evidenceAnchor"], sanitized["snippet"])
    return sanitized


def safe_public_source_path(source_path: str) -> str:
    if source_path.startswith(SOURCE_REFERENCE_PREFIX):
        return source_path
    if is_unsafe_source_path(source_path):
        return f"{SOURCE_REFERENCE_PREFIX}{sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
    return source_path


def trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def line_number(text: str, start: int) -> int:
    return text.count("\n", 0, min(start, len(text))) + 1


def display_type(signal_type: str) -> str:
    return signal_type.replace("_", " ").title()


def redacted_marker(snippet: str) -> str:
    marker = REDACTED_MARKER_RE.search(snippet)
    return marker.group(0) if marker else "[REDACTED_VALUE]"


def sanitize_anchor(anchor: dict[str, Any], sanitized_snippet: str) -> dict[str, Any]:
    sanitized = dict(anchor)
    sanitized["redactedText"] = sanitized_snippet[:180]
    fallback = sanitized.get("fallback")
    if isinstance(fallback, dict):
        sanitized["fallback"] = {**fallback, "redactedText": sanitized_snippet[:180]}
    return sanitized


def _with_source_location(signal: dict[str, Any], text_locations: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    anchor = signal.get("evidenceAnchor")
    if not isinstance(anchor, dict):
        return signal
    selector = anchor.get("selector")
    if not isinstance(selector, dict) or selector.get("type") != "textPosition":
        return signal

    start = selector.get("start")
    end = selector.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return signal

    location = _matching_location(text_locations, start, end)
    if not location:
        return signal

    localized = dict(signal)
    localized_anchor = dict(anchor)
    localized_selector = _localized_selector(selector, location)
    localized_anchor["format"] = str(location.get("format") or localized_anchor.get("format") or "text")
    localized_anchor["fallback"] = {
        **(localized_anchor.get("fallback") if isinstance(localized_anchor.get("fallback"), dict) else {}),
        "label": str(location.get("label") or "Source location"),
        "redactedText": str(localized_anchor.get("redactedText") or localized.get("snippet") or "")[:180],
    }
    location_start = int(location["start"])
    localized_selector["sourceStart"] = start - location_start
    localized_selector["sourceEnd"] = end - location_start
    if isinstance(location.get("page"), int):
        localized_selector["page"] = location["page"]
    if isinstance(location.get("frameIndex"), int):
        localized_selector["frameIndex"] = location["frameIndex"]
    page_region = _matching_region(location, localized_selector["sourceStart"], localized_selector["sourceEnd"])
    if page_region:
        localized_selector["pageRegion"] = page_region
    localized_anchor["selector"] = localized_selector
    localized["evidenceAnchor"] = localized_anchor
    return localized


def _localized_selector(selector: dict[str, Any], location: dict[str, Any]) -> dict[str, Any]:
    location_selector = location.get("selector")
    if isinstance(location_selector, dict) and isinstance(location_selector.get("type"), str):
        localized = dict(location_selector)
        localized["start"] = selector["start"]
        localized["end"] = selector["end"]
        return localized
    return dict(selector)


def _matching_location(text_locations: tuple[dict[str, Any], ...], start: int, end: int) -> dict[str, Any] | None:
    for location in text_locations:
        location_start = location.get("start")
        location_end = location.get("end")
        if isinstance(location_start, int) and isinstance(location_end, int) and location_start <= start and end <= location_end:
            return location
    return None


def _matching_region(location: dict[str, Any], source_start: int, source_end: int) -> dict[str, Any] | None:
    regions = location.get("regions")
    if not isinstance(regions, (list, tuple)):
        return None
    matches = [
        region for region in regions
        if isinstance(region, dict)
        and isinstance(region.get("start"), int)
        and isinstance(region.get("end"), int)
        and region["start"] < source_end
        and source_start < region["end"]
    ]
    if not matches:
        return None
    return _region_union(matches)


def _region_union(regions: list[dict[str, Any]]) -> dict[str, Any] | None:
    boxes = [
        region for region in regions
        if all(isinstance(region.get(key), (int, float)) for key in ("x", "y", "width", "height"))
    ]
    if not boxes:
        return None
    left = min(float(region["x"]) for region in boxes)
    bottom = min(float(region["y"]) for region in boxes)
    right = max(float(region["x"]) + float(region["width"]) for region in boxes)
    top = max(float(region["y"]) + float(region["height"]) for region in boxes)
    first = boxes[0]
    page_region: dict[str, Any] = {
        "x": round(left, 2),
        "y": round(bottom, 2),
        "width": round(right - left, 2),
        "height": round(top - bottom, 2),
        "unit": str(first.get("unit") or "pt"),
        "origin": str(first.get("origin") or "bottom_left"),
        "confidence": str(first.get("confidence") or "estimated"),
    }
    for key in ("pageWidth", "pageHeight"):
        if isinstance(first.get(key), (int, float)):
            page_region[key] = round(float(first[key]), 2)
    ocr_confidences = [float(region["ocrConfidence"]) for region in boxes if isinstance(region.get("ocrConfidence"), (int, float))]
    if ocr_confidences:
        page_region["ocrConfidence"] = round(min(ocr_confidences), 2)
    return page_region


def is_unsafe_source_path(source_path: str) -> bool:
    lowered = source_path.lower()
    return (
        "://" in source_path
        or lowered.startswith("www.")
        or source_path.startswith("/")
        or source_path.startswith("~/")
        or bool(re.match(r"^[A-Za-z]:[\\/]", source_path))
    )
