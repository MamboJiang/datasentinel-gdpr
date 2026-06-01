"""Bounded RTF text extraction for prelaunch source scans."""

from __future__ import annotations

from dataclasses import dataclass

MAX_EXTRACTED_TEXT_CHARS = 300_000
SKIPPED_DESTINATIONS = {
    "annotation",
    "colortbl",
    "fonttbl",
    "footer",
    "generator",
    "header",
    "info",
    "object",
    "pict",
    "stylesheet",
}


@dataclass(frozen=True)
class RtfTextExtraction:
    text: str


class RtfExtractionIssue(Exception):
    def __init__(self, detail: str, *, recognition_difficulty: str = "unsupported") -> None:
        super().__init__(detail)
        self.detail = detail
        self.recognition_difficulty = recognition_difficulty


def extract_rtf_text(body: bytes, name: str) -> RtfTextExtraction:
    decoded = body.decode("latin-1", errors="ignore")
    text = _rtf_to_text(decoded)
    if not text.strip():
        raise RtfExtractionIssue(f"{name} has no extractable RTF text.", recognition_difficulty="hard")
    return RtfTextExtraction(text[:MAX_EXTRACTED_TEXT_CHARS])


def _rtf_to_text(document: str) -> str:
    output: list[str] = []
    skip_depth: int | None = None
    depth = 0
    index = 0
    output_size = 0
    while index < len(document) and output_size < MAX_EXTRACTED_TEXT_CHARS:
        before_size = len(output)
        character = document[index]
        if character == "{":
            depth += 1
            index += 1
            continue
        if character == "}":
            if skip_depth is not None and depth <= skip_depth:
                skip_depth = None
            depth = max(depth - 1, 0)
            index += 1
            continue
        if character == "\\":
            destination = _control_destination(document, index)
            index = _handle_control(document, index, output, depth, skip_depth)
            if skip_depth is None and destination in SKIPPED_DESTINATIONS:
                skip_depth = depth
            output_size += sum(len(part) for part in output[before_size:])
            continue
        if skip_depth is None:
            output.append(character)
        output_size += sum(len(part) for part in output[before_size:])
        index += 1
    return _normalize_text("".join(output))


def _handle_control(document: str, index: int, output: list[str], depth: int, skip_depth: int | None) -> int:
    if index + 1 >= len(document):
        return index + 1
    marker = document[index + 1]
    if marker in "{}\\":
        if skip_depth is None:
            output.append(marker)
        return index + 2
    if marker == "'":
        if skip_depth is None and index + 3 < len(document):
            try:
                output.append(bytes.fromhex(document[index + 2:index + 4]).decode("latin-1", errors="ignore"))
            except ValueError:
                pass
        return index + 4

    end = index + 1
    while end < len(document) and document[end].isalpha():
        end += 1
    control = document[index + 1:end]
    sign = 1
    if end < len(document) and document[end] == "-":
        sign = -1
        end += 1
    number_start = end
    while end < len(document) and document[end].isdigit():
        end += 1
    number = int(document[number_start:end] or "0") * sign
    has_space_delimiter = end < len(document) and document[end] == " "
    if has_space_delimiter:
        end += 1

    if skip_depth is None:
        _append_control_text(output, control, number)
        if control == "u" and not has_space_delimiter and end < len(document):
            end += 1
    return end


def _append_control_text(output: list[str], control: str, number: int) -> None:
    if control in {"par", "line"}:
        output.append("\n")
    elif control == "tab":
        output.append("\t")
    elif control == "u":
        codepoint = number if number >= 0 else 65536 + number
        if 0 <= codepoint <= 0x10FFFF:
            output.append(chr(codepoint))


def _control_destination(document: str, index: int) -> str | None:
    if index >= len(document) or document[index] != "\\":
        return None
    end = index + 1
    while end < len(document) and document[end].isalpha():
        end += 1
    return document[index + 1:end] or None


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.replace("\r", "\n").split("\n")]
    return "\n".join(line for line in lines if line)
