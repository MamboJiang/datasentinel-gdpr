from __future__ import annotations

import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import DOWNLOAD_ACCEPT_HEADER, extract_document_content
from backend.lawdit.source_media_recognition import is_image, is_video_media

try:
    from PIL import Image
except Exception:  # pragma: no cover - depends on local test environment
    Image = None  # type: ignore[assignment]


class ImageOcrFormatSupportTests(unittest.TestCase):
    def test_drive_download_accept_header_includes_declared_image_ocr_formats(self) -> None:
        self.assertIn("image/bmp", DOWNLOAD_ACCEPT_HEADER)
        self.assertIn("image/webp", DOWNLOAD_ACCEPT_HEADER)
        self.assertIn("video/x-m4v", DOWNLOAD_ACCEPT_HEADER)
        self.assertIn("video/x-matroska", DOWNLOAD_ACCEPT_HEADER)
        self.assertIn("video/x-msvideo", DOWNLOAD_ACCEPT_HEADER)
        self.assertTrue(is_image("image/x-ms-bmp", ""))
        self.assertTrue(is_image("image/x-tiff", ""))
        self.assertTrue(is_image("", ".webp"))
        self.assertTrue(is_video_media("video/x-m4v", ""))
        self.assertTrue(is_video_media("video/x-matroska", ""))
        self.assertTrue(is_video_media("video/x-msvideo", ""))
        self.assertTrue(is_video_media("", ".avi"))

    @unittest.skipUnless(Image is not None, "Pillow is unavailable for OCR format fixture generation.")
    def test_non_png_image_formats_use_png_normalization_fallback_without_raw_values(self) -> None:
        tsv = _identity_tsv()
        formats = (
            ("jpg", "JPEG", "image/jpeg"),
            ("tif", "TIFF", "image/tiff"),
            ("bmp", "BMP", "image/bmp"),
            ("webp", "WEBP", "image/webp"),
        )

        for suffix, image_format, content_type in formats:
            with self.subTest(suffix=suffix):
                body = _image_bytes(image_format)
                observed_paths: list[str] = []

                def fake_tesseract(command: list[str], **kwargs: object) -> mock.Mock:
                    observed_paths.append(command[1])
                    if Path(command[1]).name == "source_normalized.png":
                        return mock.Mock(returncode=0, stdout=tsv)
                    return mock.Mock(returncode=1, stdout="")

                with mock.patch.dict(
                    "os.environ",
                    {"LAWDIT_OCR_MODE": "local", "LAWDIT_OCR_LANGS": "eng+deu+chi_sim"},
                ), mock.patch(
                    "backend.lawdit.ocr_capabilities.shutil.which",
                    return_value="/usr/bin/tesseract",
                ), mock.patch(
                    "backend.lawdit.source_image_ocr.subprocess.run",
                    side_effect=fake_tesseract,
                ):
                    extracted = extract_document_content(body=body, content_type=content_type, name=f"travel_identity.{suffix}")

                signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
                signal_types = {signal["type"] for signal in signals}
                passport = next(signal for signal in signals if signal["type"] == "passport_number")
                selector = passport["evidenceAnchor"]["selector"]
                serialized = json.dumps(signals)

                self.assertEqual(extracted.file_format, "image_ocr")
                self.assertEqual(extracted.extraction_method, "tesseract_image_ocr")
                self.assertEqual(extracted.recognition_difficulty, "hard")
                self.assertTrue({"person_name", "address", "passport_number"}.issubset(signal_types))
                self.assertTrue(any(path.endswith(f"source.{suffix}") for path in observed_paths))
                self.assertTrue(any(path.endswith("source_normalized.png") for path in observed_paths))
                self.assertEqual(selector["pageRegion"]["origin"], "top_left")
                self.assertNotIn("Laura Garcia", serialized)
                self.assertNotIn("Paulinestr. 13 Heilbronn 74076", serialized)
                self.assertNotIn("EN3457864", serialized)


def _image_bytes(image_format: str) -> bytes:
    image = Image.new("RGB", (320, 180), "white")
    buffer = BytesIO()
    try:
        image.save(buffer, format=image_format)
    except Exception as error:
        raise unittest.SkipTest(f"Pillow cannot write {image_format} fixtures: {error}") from error
    return buffer.getvalue()


def _identity_tsv() -> str:
    rows = [
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
        "1\t1\t0\t0\t0\t0\t0\t0\t320\t180\t-1\t",
        "5\t1\t1\t1\t1\t1\t20\t20\t54\t18\t92\tName:",
        "5\t1\t1\t1\t1\t2\t80\t20\t60\t18\t92\tLaura",
        "5\t1\t1\t1\t1\t3\t146\t20\t68\t18\t92\tGarcia",
        "5\t1\t1\t1\t2\t1\t20\t52\t76\t18\t91\tAddress:",
        "5\t1\t1\t1\t2\t2\t102\t52\t92\t18\t91\tPaulinestr.",
        "5\t1\t1\t1\t2\t3\t200\t52\t24\t18\t91\t13",
        "5\t1\t1\t1\t2\t4\t230\t52\t72\t18\t91\tHeilbronn",
        "5\t1\t1\t1\t2\t5\t20\t76\t56\t18\t91\t74076",
        "5\t1\t1\t1\t3\t1\t20\t108\t76\t18\t93\tPassport:",
        "5\t1\t1\t1\t3\t2\t102\t108\t92\t18\t93\tEN3457864",
    ]
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    unittest.main()
