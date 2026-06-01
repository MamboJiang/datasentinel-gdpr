"""Deterministic redacted signal detection for prelaunch scans."""

from __future__ import annotations

import re
from typing import Any

from .signal_inline_labels import inline_label_value_spans
from .signal_label_rules import rule_for_label
from .signal_regex_rules import regex_signals
from .signal_stacked_labels import stacked_label_signals
from .signal_evidence_anchors import (
    safe_public_source_path,
    sanitize_public_signal,
    text_position_anchor,
    trim_span,
)

MAX_SIGNAL_SCAN_CHARS = 200_000
MAX_SIGNALS_PER_DOCUMENT = 32

LABEL_RE = re.compile(r"^\s*(?P<label>[^:：\r\n]{1,72})\s*[:：]\s*(?P<value>.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"^[\s._/\\|()[\]{}-]+$")

WEAKER_OVERLAP_SUPPRESSIONS = {
    "expense_amount": {"salary_compensation"},
    "iban_like": {"bank_account"},
    "phone_number": {
        "bank_account",
        "date_of_birth",
        "employee_id",
        "national_identifier",
        "passport_number",
        "payment_card",
        "tax_id",
    },
}

def detect_signals(text: str) -> list[dict[str, Any]]:
    """Return public-safe signal records without raw adjacent source context."""
    scanned_text = text[:MAX_SIGNAL_SCAN_CHARS]
    signals: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    line_records: list[tuple[str, int, int]] = []

    line_start = 0
    current_line_number = 1
    for line in scanned_text.splitlines(keepends=True):
        visible_line = line.rstrip("\r\n")
        line_records.append((visible_line, line_start, current_line_number))
        for label_signal in _signals_from_label_line(visible_line, line_start, current_line_number):
            _append_signal(signals, seen, label_signal)
            if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
                return signals
        line_start += len(line)
        current_line_number += 1

    for stacked_signal in stacked_label_signals(line_records, _has_filled_value):
        _append_signal(signals, seen, stacked_signal)
        if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
            return signals

    for regex_signal in regex_signals(scanned_text):
        _append_signal(signals, seen, regex_signal)
        if len(signals) >= MAX_SIGNALS_PER_DOCUMENT:
            return signals

    return signals


def _signals_from_label_line(line: str, line_start: int, line_number: int) -> list[dict[str, Any]]:
    inline_signals = [
        signal
        for signal in (
            _signal_from_label_span(line, line_start, line_number, label, value_start, value_end)
            for label, value_start, value_end in inline_label_value_spans(line)
        )
        if signal
    ]
    if inline_signals:
        return inline_signals

    fallback = _signal_from_label_line(line, line_start, line_number)
    return [fallback] if fallback else []


def _signal_from_label_span(line: str, line_start: int, line_number: int, label: str, value_start: int, value_end: int) -> dict[str, Any] | None:
    value = line[value_start:value_end].strip()
    if not _has_filled_value(value):
        return None

    rule = rule_for_label(label, value)
    if not rule:
        return None

    snippet = f"{label}: {rule.marker}"
    return _signal(
        rule.signal_type,
        rule.detector,
        rule.confidence,
        snippet,
        evidence_anchor=text_position_anchor(
            rule.signal_type,
            rule.detector,
            line_start + value_start,
            line_start + value_end,
            line_number,
            snippet,
        ),
    )


def _signal_from_label_line(line: str, line_start: int, line_number: int) -> dict[str, Any] | None:
    match = LABEL_RE.match(line)
    if not match:
        return None

    label = _clean_label(match.group("label"))
    value = match.group("value").strip()
    if not _has_filled_value(value):
        return None

    rule = rule_for_label(label, value)
    if not rule:
        return None

    snippet = f"{label}: {rule.marker}"
    value_start, value_end = trim_span(line, match.start("value"), match.end("value"))
    return _signal(
        rule.signal_type,
        rule.detector,
        rule.confidence,
        snippet,
        evidence_anchor=text_position_anchor(
            rule.signal_type,
            rule.detector,
            line_start + value_start,
            line_start + value_end,
            line_number,
            snippet,
        ),
    )


def _overlaps_existing_signal(signal: dict[str, Any], signals: list[dict[str, Any]]) -> bool:
    span = _signal_text_span(signal)
    if not span:
        return False
    for existing in signals:
        if existing.get("type") != signal.get("type"):
            continue
        existing_span = _signal_text_span(existing)
        if existing_span and existing_span[0] < span[1] and span[0] < existing_span[1]:
            return True
    return False


def _signal_text_span(signal: dict[str, Any]) -> tuple[int, int] | None:
    anchor = signal.get("evidenceAnchor")
    if not isinstance(anchor, dict):
        return None
    selector = anchor.get("selector")
    if not isinstance(selector, dict) or selector.get("type") != "textPosition":
        return None
    start = selector.get("start")
    end = selector.get("end")
    if isinstance(start, int) and isinstance(end, int):
        return start, end
    return None


def _has_filled_value(value: str) -> bool:
    cleaned = value.strip()
    if len(cleaned) < 2:
        return False
    if PLACEHOLDER_RE.fullmatch(cleaned):
        return False
    normalized = cleaned.strip(" _.-/").lower()
    if normalized in {"n/a", "na", "none", "select", "select one", "choose one", "pending", "todo"}:
        return False
    return any(character.isalnum() for character in cleaned)


def _append_signal(signals: list[dict[str, Any]], seen: set[tuple[str, str]], signal: dict[str, Any]) -> None:
    key = (signal["type"], signal["snippet"])
    if key in seen:
        return
    if _overlaps_existing_signal(signal, signals):
        return
    if _suppressed_by_contextual_overlap(signal, signals):
        return
    seen.add(key)
    signals.append(signal)


def _suppressed_by_contextual_overlap(signal: dict[str, Any], signals: list[dict[str, Any]]) -> bool:
    blockers = WEAKER_OVERLAP_SUPPRESSIONS.get(str(signal.get("type")))
    if not blockers:
        return False
    span = _signal_text_span(signal)
    if not span:
        return False
    for existing in signals:
        if existing.get("type") not in blockers:
            continue
        existing_span = _signal_text_span(existing)
        if existing_span and existing_span[0] < span[1] and span[0] < existing_span[1]:
            return True
    return False


def _signal(signal_type: str, detector: str, confidence: float, snippet: str, *, evidence_anchor: dict[str, Any] | None = None) -> dict[str, Any]:
    signal = {"type": signal_type, "detector": detector, "confidence": confidence, "snippet": snippet[:180], "page": None}
    if evidence_anchor:
        signal["evidenceAnchor"] = evidence_anchor
    return signal


def _clean_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").split()).strip()
