from __future__ import annotations

import json
import unittest
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZipFile

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_format_recognition import extract_document_content


class StructurePathAnchorTests(unittest.TestCase):
    def test_docx_paragraph_signal_uses_structure_path_without_raw_values(self) -> None:
        body = _zip_bytes({
            "word/document.xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>Name: Claire Martin</w:t></w:r></w:p></w:body>'
                '</w:document>'
            ),
        })

        extracted = extract_document_content(
            body=body,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            name="identity.docx",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        selector = name_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "docx")
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "DOCX paragraph 1")
        self.assertEqual(selector["type"], "structurePath")
        self.assertEqual(selector["path"], "word/document.xml#paragraph:1")
        self.assertEqual(selector["partName"], "word/document.xml")
        self.assertEqual(selector["paragraphIndex"], 1)
        self.assertEqual(selector["blockLabel"], "DOCX paragraph 1")
        self.assertEqual(selector["sourceStart"], len("Name: "))
        self.assertEqual(selector["sourceEnd"], len("Name: Claire Martin"))
        self.assertNotIn("Claire Martin", serialized)

    def test_pptx_shape_signal_uses_structure_path_without_raw_values(self) -> None:
        text = "氏名：佐藤花子\n電話：+81 9012345678"
        body = _zip_bytes({
            "ppt/slides/slide1.xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f'<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>'
                '</p:sld>'
            ),
        })

        extracted = extract_document_content(
            body=body,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            name="contact.pptx",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        phone_signal = next(signal for signal in signals if signal["type"] == "phone_number")
        selector = phone_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "pptx")
        self.assertEqual(phone_signal["evidenceAnchor"]["fallback"]["label"], "Slide 1 shape 1")
        self.assertEqual(selector["type"], "structurePath")
        self.assertEqual(selector["slideNumber"], 1)
        self.assertEqual(selector["shapeIndex"], 1)
        self.assertEqual(selector["partName"], "ppt/slides/slide1.xml")
        self.assertNotIn("佐藤花子", serialized)
        self.assertNotIn("+81 9012345678", serialized)

    def test_html_text_signal_uses_structure_path_without_raw_values(self) -> None:
        html = "<section><p>الاسم: ليلى حسن</p><p>الهاتف: +971 501234567</p></section>"

        extracted = extract_document_content(body=html.encode("utf-8"), content_type="text/html", name="contact.html")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        selector = name_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "html")
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "HTML p 1")
        self.assertEqual(selector["type"], "structurePath")
        self.assertEqual(selector["path"], "/section[1]/p[1]")
        self.assertEqual(selector["tagName"], "p")
        self.assertEqual(selector["nodeIndex"], 1)
        self.assertEqual(selector["blockLabel"], "HTML p 1")
        self.assertNotIn("ليلى حسن", serialized)
        self.assertNotIn("+971 501234567", serialized)

    def test_xml_element_and_attribute_signals_use_structure_paths_without_raw_values(self) -> None:
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<case><contact 电话="+33123456789"><姓名>王芳</姓名></contact></case>'
        )

        extracted = extract_document_content(body=xml.encode("utf-8"), content_type="application/xml", name="contact.xml")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        phone_signal = next(signal for signal in signals if signal["type"] == "phone_number")
        name_selector = name_signal["evidenceAnchor"]["selector"]
        phone_selector = phone_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "xml")
        self.assertEqual(extracted.extraction_method, "xml_structure_text")
        self.assertEqual(name_selector["type"], "structurePath")
        self.assertEqual(name_selector["path"], "/element[1]/element[1]/element[1]")
        self.assertEqual(name_selector["blockLabel"], "XML element 1.1.1")
        self.assertEqual(phone_selector["path"], "/element[1]/element[1]/attribute[1]")
        self.assertEqual(phone_selector["attributeIndex"], 1)
        self.assertEqual(phone_selector["blockLabel"], "XML element 1.1 attribute 1")
        self.assertNotIn("王芳", serialized)
        self.assertNotIn("+33123456789", serialized)


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, body in entries.items():
            archive.writestr(name, body)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
