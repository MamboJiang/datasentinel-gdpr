"""BOM and charset-aware decoding for source text bytes."""

from __future__ import annotations

import codecs

_UTF16_LE_ALIASES = {"utf16le", "utf-16le", "utf_16_le"}
_UTF16_BE_ALIASES = {"utf16be", "utf-16be", "utf_16_be"}
_UTF8_ALIASES = {"utf8", "utf-8", "utf_8"}


def decode_text_body(body: bytes, content_type: str = "") -> str:
    for encoding in _candidate_encodings(body, content_type):
        try:
            return body.decode(encoding)
        except UnicodeError:
            continue
    return body.decode("utf-8", errors="replace")


def _candidate_encodings(body: bytes, content_type: str) -> tuple[str, ...]:
    candidates: list[str] = []
    _append(candidates, _charset_encoding(content_type))
    _append(candidates, _bom_encoding(body))
    _append(candidates, "utf-8-sig")
    if _looks_utf16(body):
        _append(candidates, "utf-16")
        _append(candidates, "utf-16-le")
        _append(candidates, "utf-16-be")
    return tuple(candidates)


def _charset_encoding(content_type: str) -> str | None:
    for parameter in content_type.split(";")[1:]:
        key, separator, value = parameter.partition("=")
        if separator and key.strip().lower() == "charset":
            return _normalized_encoding(value.strip().strip('"').strip("'"))
    return None


def _normalized_encoding(value: str) -> str | None:
    normalized = value.lower().replace("_", "-")
    if normalized in _UTF16_LE_ALIASES:
        normalized = "utf-16-le"
    elif normalized in _UTF16_BE_ALIASES:
        normalized = "utf-16-be"
    elif normalized in _UTF8_ALIASES:
        normalized = "utf-8-sig"
    try:
        codecs.lookup(normalized)
    except LookupError:
        return None
    return normalized


def _bom_encoding(body: bytes) -> str | None:
    if body.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if body.startswith(codecs.BOM_UTF16_LE) or body.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"
    return None


def _looks_utf16(body: bytes) -> bool:
    if len(body) < 4:
        return False
    if body.startswith(codecs.BOM_UTF16_LE) or body.startswith(codecs.BOM_UTF16_BE):
        return True
    sample = body[:200]
    even_nuls = sample[0::2].count(0)
    odd_nuls = sample[1::2].count(0)
    return max(even_nuls, odd_nuls) >= max(2, len(sample) // 6)


def _append(candidates: list[str], encoding: str | None) -> None:
    if encoding and encoding not in candidates:
        candidates.append(encoding)
