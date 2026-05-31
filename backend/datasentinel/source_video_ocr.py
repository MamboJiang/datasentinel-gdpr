"""Bounded local OCR for raw video media frames."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .source_image_ocr import ImageOcrIssue, extract_image_content
from .ocr_capabilities import ocr_mode, tesseract_path


@dataclass(frozen=True)
class VideoFrameOcrResult:
    text: str
    text_locations: tuple[dict[str, Any], ...] = field(default=(), kw_only=True)


class VideoFrameOcrIssue(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def extract_video_frame_content(
    body: bytes,
    name: str,
    *,
    max_frames: int = 4,
    timeout_seconds: int = 18,
) -> VideoFrameOcrResult:
    if ocr_mode() != "local":
        raise VideoFrameOcrIssue(f"{name} requires video frame OCR, but local OCR is disabled on this host.")
    if not tesseract_path():
        raise VideoFrameOcrIssue(f"{name} requires video frame OCR, but Tesseract is not installed on this host.")
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise VideoFrameOcrIssue(f"{name} requires video frame OCR, but FFmpeg is not installed on this host.")

    suffix = Path(name).suffix.lower() or ".mp4"
    with tempfile.TemporaryDirectory() as directory:
        temp_root = Path(directory)
        video_path = temp_root / f"input{suffix}"
        video_path.write_bytes(body)
        frame_pattern = temp_root / "frame-%03d.png"
        _extract_frames(ffmpeg, video_path, frame_pattern, max_frames, timeout_seconds, name)
        return _ocr_frames(sorted(temp_root.glob("frame-*.png")), name)


def _extract_frames(
    ffmpeg: str,
    video_path: Path,
    frame_pattern: Path,
    max_frames: int,
    timeout_seconds: int,
    name: str,
) -> None:
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-vf",
                "fps=1/2",
                "-frames:v",
                str(max_frames),
                str(frame_pattern),
            ],
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise VideoFrameOcrIssue(f"{name} video frame extraction timed out.") from error
    if result.returncode != 0:
        raise VideoFrameOcrIssue(f"{name} video frame extraction failed.")


def _ocr_frames(frame_paths: list[Path], name: str) -> VideoFrameOcrResult:
    if not frame_paths:
        raise VideoFrameOcrIssue(f"{name} produced no reviewable video frames.")

    fragments: list[str] = []
    locations: list[dict[str, Any]] = []
    offset = 0
    for frame_index, frame_path in enumerate(frame_paths, start=1):
        try:
            image_result = extract_image_content(frame_path.read_bytes(), frame_path.name, timeout_seconds=8)
        except ImageOcrIssue:
            continue
        text = image_result.text.strip()
        if not text:
            continue
        if fragments:
            fragments.append("\n")
            offset += 1
        start = offset
        fragments.append(text)
        offset += len(text)
        locations.append(_frame_location(text, start, offset, frame_index, image_result.text_locations))

    combined = "".join(fragments)
    if not combined.strip():
        raise VideoFrameOcrIssue(f"{name} has no extractable video-frame OCR text.")
    return VideoFrameOcrResult(combined, text_locations=tuple(locations))


def _frame_location(
    text: str,
    start: int,
    end: int,
    frame_index: int,
    image_locations: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    location: dict[str, Any] = {
        "format": "video_ocr",
        "label": f"Frame {frame_index} OCR text",
        "start": start,
        "end": end,
        "frameIndex": frame_index,
        "page": frame_index,
    }
    regions = _frame_regions(image_locations)
    if regions:
        location["regions"] = regions
    return location


def _frame_regions(image_locations: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    if not image_locations:
        return ()
    regions = image_locations[0].get("regions")
    if not isinstance(regions, (list, tuple)):
        return ()
    return tuple(region for region in regions if isinstance(region, dict))
