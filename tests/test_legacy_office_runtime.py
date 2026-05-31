from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.source_format_recognition import extract_document_content
from backend.datasentinel.source_legacy_office import office_converter_path


@unittest.skipUnless(office_converter_path(), "LibreOffice is unavailable for runtime legacy Office conversion.")
class LegacyOfficeRuntimeTests(unittest.TestCase):
    def test_real_doc_conversion_feeds_deterministic_detection(self) -> None:
        converter = office_converter_path()
        self.assertIsNotNone(converter)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_txt = root / "legacy-seed.txt"
            source_txt.write_text("Legacy file owner privacy.legacy-runtime@example.org", encoding="utf-8")
            subprocess.run(
                [
                    str(converter),
                    "--headless",
                    "--nologo",
                    "--norestore",
                    "--nofirststartwizard",
                    f"-env:UserInstallation={(root / 'profile-generate').as_uri()}",
                    "--convert-to",
                    "doc",
                    "--outdir",
                    str(root),
                    str(source_txt),
                ],
                check=True,
                capture_output=True,
                timeout=25,
            )
            doc_path = root / "legacy-seed.doc"
            self.assertTrue(doc_path.exists(), "LibreOffice did not create a legacy DOC fixture.")
            extracted = extract_document_content(
                body=doc_path.read_bytes(),
                content_type="application/msword",
                name="legacy-seed.doc",
            )

        signal_types = {signal["type"] for signal in detect_signals(extracted.text)}
        self.assertEqual(extracted.file_format, "doc")
        self.assertEqual(extracted.extraction_method, "libreoffice_legacy_office_text")
        self.assertEqual(extracted.recognition_difficulty, "hard")
        self.assertIn("email", signal_types)
        self.assertTrue(extracted.text_locations)


if __name__ == "__main__":
    unittest.main()
