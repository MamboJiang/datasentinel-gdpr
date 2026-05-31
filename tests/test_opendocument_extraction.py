from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_documents import read_source_documents
from backend.datasentinel.source_format_recognition import extract_document_content


class OpenDocumentExtractionTests(unittest.TestCase):
    def test_odt_multilingual_labels_get_structure_path_anchors(self) -> None:
        body = _odf_bytes(_document_xml(
            """
            <office:text>
              <text:p>Nombre: Laura Garcia</text:p>
              <text:p>Teléfono: +34123456789</text:p>
            </office:text>
            """
        ))

        extracted = extract_document_content(
            body=body,
            content_type="application/vnd.oasis.opendocument.text",
            name="spanish_contact.odt",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]

        self.assertEqual(extracted.file_format, "odt")
        self.assertEqual(extracted.extraction_method, "odf_odt_text")
        self.assertEqual(extracted.recognition_difficulty, "moderate")
        self.assertTrue(all(selector["type"] == "structurePath" for selector in selectors))
        self.assertTrue(all(selector["partName"] == "content.xml" for selector in selectors))
        self.assertNotIn("Laura Garcia", json.dumps(signals, ensure_ascii=False))
        self.assertNotIn("+34123456789", json.dumps(signals, ensure_ascii=False))

    def test_ods_label_value_cells_get_table_cell_anchors(self) -> None:
        body = _odf_bytes(_document_xml(
            """
            <office:spreadsheet>
              <table:table table:name="Sensitive raw sheet">
                <table:table-row>
                  <table:table-cell><text:p>Naam</text:p></table:table-cell>
                  <table:table-cell><text:p>Sophie de Vries</text:p></table:table-cell>
                </table:table-row>
                <table:table-row>
                  <table:table-cell><text:p>BSN</text:p></table:table-cell>
                  <table:table-cell><text:p>123456782</text:p></table:table-cell>
                </table:table-row>
                <table:table-row>
                  <table:table-cell><text:p>Salaris</text:p></table:table-cell>
                  <table:table-cell><text:p>EUR 62000</text:p></table:table-cell>
                </table:table-row>
              </table:table>
            </office:spreadsheet>
            """
        ))

        extracted = extract_document_content(
            body=body,
            content_type="application/vnd.oasis.opendocument.spreadsheet",
            name="dutch_compensation.ods",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]

        self.assertEqual(extracted.file_format, "ods")
        self.assertEqual(extracted.extraction_method, "odf_ods_text")
        self.assertTrue({"person_name", "national_identifier", "salary_compensation"}.issubset(signal_types))
        self.assertTrue(all(selector["type"] == "tableCell" for selector in selectors))
        self.assertTrue(all(selector["sheetName"] == "Sheet1" for selector in selectors))
        self.assertNotIn("Sensitive raw sheet", json.dumps(signals, ensure_ascii=False))
        self.assertNotIn("Sophie de Vries", json.dumps(signals, ensure_ascii=False))

    def test_odp_presentation_text_gets_structure_path_anchors(self) -> None:
        body = _odf_bytes(_document_xml(
            """
            <office:presentation>
              <draw:page draw:name="Slide with raw title">
                <draw:frame><draw:text-box>
                  <text:p>Imię i nazwisko: Anna Kowalska</text:p>
                  <text:p>Telefon: +48 501234567</text:p>
                </draw:text-box></draw:frame>
              </draw:page>
            </office:presentation>
            """
        ))

        extracted = extract_document_content(
            body=body,
            content_type="application/vnd.oasis.opendocument.presentation",
            name="polish_identity.odp",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        selectors = [signal["evidenceAnchor"]["selector"] for signal in signals]

        self.assertEqual(extracted.file_format, "odp")
        self.assertEqual(extracted.extraction_method, "odf_odp_text")
        self.assertTrue(all(selector["type"] == "structurePath" for selector in selectors))
        self.assertNotIn("Slide with raw title", json.dumps(signals, ensure_ascii=False))
        self.assertNotIn("Anna Kowalska", json.dumps(signals, ensure_ascii=False))

    def test_local_source_accepts_opendocument_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "contact.odt").write_bytes(_odf_bytes(_document_xml(
                "<office:text><text:p>Nombre: Laura Garcia</text:p></office:text>"
            )))

            batch = read_source_documents(
                {"sourceType": "local_repo", "config": {"rootPath": str(root)}},
                {},
            )

        self.assertEqual(batch.unsupported_files, 0)
        self.assertEqual(batch.documents[0].file_format, "odt")
        self.assertEqual(batch.documents[0].recognition_difficulty, "moderate")


def _document_xml(inner_body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0">
  <office:body>{inner_body}</office:body>
</office:document-content>"""


def _odf_bytes(content_xml: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument")
        archive.writestr("content.xml", content_xml)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
