"""RFC 5322/MIME email extraction with public-safe structure anchors."""

from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Any

MAX_EXTRACTED_TEXT_CHARS = 300_000
MAX_EMAIL_PARTS = 64
MAX_PART_CHARS = 120_000
HEADER_NAMES = ("from", "to", "cc", "bcc", "reply-to", "subject")


@dataclass(frozen=True)
class EmailTextExtraction:
    text: str
    locations: tuple[dict[str, Any], ...]


class EmailExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_email_text(body: bytes, name: str) -> EmailTextExtraction:
    try:
        message = BytesParser(policy=policy.default).parsebytes(body)
    except Exception as error:
        raise EmailExtractionIssue(f"{name} is not a readable RFC 5322 email message.") from error

    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    _append_headers(message, fragments, locations)
    _append_body_parts(message, fragments, locations)
    return _joined_extraction(fragments, locations, name)


def _append_headers(message: Any, fragments: list[str], locations: list[dict[str, Any]]) -> None:
    header_index = 0
    for header_name in HEADER_NAMES:
        values = message.get_all(header_name, [])
        for value in values:
            text = " ".join(str(value).split())
            if not text:
                continue
            header_index += 1
            start = _append_fragment(fragments, f"{header_name}: {text}")
            value_start = start + len(header_name) + 2
            label = f"Email header {header_index}"
            locations.append({
                "format": "eml",
                "label": label,
                "start": value_start,
                "end": value_start + len(text),
                "selector": {
                    "type": "structurePath",
                    "path": f"/headers/header[{header_index}]",
                    "partName": "headers",
                    "fieldIndex": header_index,
                    "blockLabel": label,
                },
            })


def _append_body_parts(message: Any, fragments: list[str], locations: list[dict[str, Any]]) -> None:
    body_index = 0
    for part_index, part in enumerate(_iter_text_parts(message), start=1):
        text = _part_text(part)
        if not text:
            continue
        body_index += 1
        start = _append_fragment(fragments, text)
        label = f"Email body part {body_index}"
        locations.append({
            "format": "eml",
            "label": label,
            "start": start,
            "end": start + len(text),
            "selector": {
                "type": "structurePath",
                "path": f"/body/part[{part_index}]",
                "partName": "body",
                "nodeIndex": part_index,
                "blockLabel": label,
            },
        })


def _iter_text_parts(message: Any) -> list[Any]:
    parts: list[Any] = []
    for part in message.walk():
        if len(parts) >= MAX_EMAIL_PARTS:
            break
        if part.is_multipart() or part.get_content_disposition() == "attachment" or part.get_filename():
            continue
        if part.get_content_type() in {"text/plain", "text/html"}:
            parts.append(part)
    return parts


def _part_text(part: Any) -> str:
    try:
        content = part.get_content()
    except Exception:
        payload = part.get_payload(decode=True) or b""
        content = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
    if not isinstance(content, str):
        return ""
    if part.get_content_type() == "text/html":
        content = _html_text(content)
    return "\n".join(" ".join(line.split()) for line in content.splitlines() if line.strip())[:MAX_PART_CHARS]


def _html_text(content: str) -> str:
    parser = _EmailHtmlTextParser()
    parser.feed(content)
    return "\n".join(parser.fragments)


def _append_fragment(fragments: list[str], value: str) -> int:
    start = sum(len(fragment) for fragment in fragments) + len(fragments)
    fragments.append(value)
    return start


def _joined_extraction(fragments: list[str], locations: list[dict[str, Any]], name: str) -> EmailTextExtraction:
    text = "\n".join(fragments)
    if not text.strip():
        raise EmailExtractionIssue(f"{name} has no extractable email text.", recognition_difficulty="hard")
    return EmailTextExtraction(text[:MAX_EXTRACTED_TEXT_CHARS], tuple(locations))


class _EmailHtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.fragments.append(text)
