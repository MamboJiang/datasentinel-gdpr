from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.source_video_ocr import extract_video_frame_content, ffmpeg_path
from backend.datasentinel.ocr_capabilities import tesseract_path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - optional test helper dependency
    Image = ImageDraw = ImageFont = None


@unittest.skipUnless(Image is not None, "Pillow is unavailable for runtime video fixture generation.")
@unittest.skipUnless(ffmpeg_path(), "FFmpeg is unavailable for runtime video frame extraction.")
@unittest.skipUnless(tesseract_path(), "Tesseract is unavailable for runtime video OCR.")
class VideoFrameOcrRuntimeTests(unittest.TestCase):
    def test_real_video_frame_ocr_feeds_deterministic_detection(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            png_path = root / "frame.png"
            video_path = root / "screen.mp4"
            _write_frame_fixture(png_path)
            subprocess.run(
                [
                    str(ffmpeg_path()),
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(png_path),
                    "-t",
                    "1",
                    "-pix_fmt",
                    "yuv420p",
                    str(video_path),
                ],
                check=True,
                timeout=15,
            )
            with mock.patch.dict(os.environ, {"DATASENTINEL_OCR_MODE": "local", "DATASENTINEL_OCR_LANGS": "eng"}):
                extracted = extract_video_frame_content(video_path.read_bytes(), "screen.mp4")

        signal_types = {signal["type"] for signal in detect_signals(extracted.text)}
        self.assertIn("email", signal_types)
        self.assertIn("video_ocr", {location["format"] for location in extracted.text_locations})
        self.assertTrue(any(location.get("regions") for location in extracted.text_locations))


def _write_frame_fixture(path: Path) -> None:
    image = Image.new("RGB", (1280, 360), "white")
    draw = ImageDraw.Draw(image)
    font = _font(54)
    draw.text((60, 110), "Privacy contact privacy.video@example.org", fill="black", font=font)
    image.save(path)


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


if __name__ == "__main__":
    unittest.main()
