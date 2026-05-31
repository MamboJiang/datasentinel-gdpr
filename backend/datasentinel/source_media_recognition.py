"""Media format boundaries for prelaunch source scans."""

from __future__ import annotations

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_VIDEO_TRANSCRIPT_SUFFIXES = {".srt", ".vtt"}
SUPPORTED_VIDEO_MEDIA_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
SUPPORTED_MEDIA_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_TRANSCRIPT_SUFFIXES | SUPPORTED_VIDEO_MEDIA_SUFFIXES
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/bmp", "image/webp"}
VIDEO_TRANSCRIPT_CONTENT_TYPES = {"text/vtt", "application/x-subrip"}
VIDEO_CONTENT_TYPE_PREFIXES = {"video/"}
MEDIA_ACCEPT_HEADER = "image/png;q=0.7, image/jpeg;q=0.7, image/tiff;q=0.7, text/vtt;q=0.7, application/x-subrip;q=0.7"


def is_image(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_IMAGE_SUFFIXES or content_type in IMAGE_CONTENT_TYPES


def is_video_transcript(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_VIDEO_TRANSCRIPT_SUFFIXES or content_type in VIDEO_TRANSCRIPT_CONTENT_TYPES


def is_video_media(content_type: str, suffix: str) -> bool:
    return suffix in SUPPORTED_VIDEO_MEDIA_SUFFIXES or any(content_type.startswith(prefix) for prefix in VIDEO_CONTENT_TYPE_PREFIXES)


def clean_video_transcript(body: bytes, name: str) -> str:
    text = body.decode("utf-8", errors="ignore")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.upper() == "WEBVTT" or stripped.isdigit() or "-->" in stripped:
            continue
        lines.append(stripped)
    text = "\n".join(lines)
    if not text.strip():
        raise ValueError(f"{name} has no extractable transcript text.")
    return text
