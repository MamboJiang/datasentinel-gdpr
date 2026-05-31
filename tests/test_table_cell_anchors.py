from __future__ import annotations

import json
import unittest
from io import BytesIO
from zipfile import ZipFile

from backend.datasentinel.deterministic_signals import detect_signals
from backend.datasentinel.signal_evidence_anchors import apply_source_locations
from backend.datasentinel.source_format_recognition import extract_document_content


class TableCellAnchorTests(unittest.TestCase):
    def test_csv_header_rows_produce_label_context_and_table_cell_anchors(self) -> None:
        body = (
            "Name,Date of Birth,Address\n"
            'Alice Example,1988-04-03,"18 Rue Example, Paris"\n'
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="text/csv", name="people.csv")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        birth_signal = next(signal for signal in signals if signal["type"] == "date_of_birth")
        address_signal = next(signal for signal in signals if signal["type"] == "address")

        self.assertEqual(extracted.file_format, "csv")
        self.assertTrue({"person_name", "date_of_birth", "address"}.issubset(signal_types))
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "row 2 column A")
        self.assertEqual(name_signal["evidenceAnchor"]["selector"], {
            "type": "tableCell",
            "row": 2,
            "column": 1,
            "columnLabel": "A",
            "start": extracted.text.index("Alice Example"),
            "end": extracted.text.index("Alice Example") + len("Alice Example"),
            "sourceStart": 0,
            "sourceEnd": len("Alice Example"),
        })
        self.assertEqual(birth_signal["evidenceAnchor"]["selector"]["column"], 2)
        self.assertEqual(address_signal["evidenceAnchor"]["selector"]["column"], 3)
        self.assertNotIn("Alice Example", serialized)
        self.assertNotIn("1988-04-03", serialized)
        self.assertNotIn("18 Rue Example", serialized)

    def test_semicolon_csv_sniffing_preserves_multilingual_table_cell_anchors(self) -> None:
        body = (
            "Nombre;Teléfono\n"
            "Ana Silva;+351912345678\n"
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="text/csv", name="contacts.csv")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        phone_signal = next(signal for signal in signals if signal["type"] == "phone_number")

        self.assertEqual(extracted.file_format, "csv")
        self.assertTrue({"person_name", "phone_number"}.issubset(signal_types))
        self.assertEqual(name_signal["evidenceAnchor"]["selector"]["columnLabel"], "A")
        self.assertEqual(phone_signal["evidenceAnchor"]["selector"]["columnLabel"], "B")
        self.assertEqual(phone_signal["evidenceAnchor"]["selector"]["row"], 2)
        self.assertNotIn("Ana Silva", serialized)
        self.assertNotIn("+351912345678", serialized)

    def test_csv_label_value_rows_produce_table_cell_anchors_without_raw_values(self) -> None:
        body = (
            "field,value\n"
            "Name,Alice Example\n"
            "Phone,+49 301234567\n"
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="text/csv", name="contacts")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        phone_signal = next(signal for signal in signals if signal["type"] == "phone_number")
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "csv")
        self.assertEqual(name_signal["evidenceAnchor"]["format"], "csv")
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "row 2 column B")
        self.assertEqual(name_signal["evidenceAnchor"]["selector"], {
            "type": "tableCell",
            "row": 2,
            "column": 2,
            "columnLabel": "B",
            "start": extracted.text.index("Alice Example"),
            "end": extracted.text.index("Alice Example") + len("Alice Example"),
            "sourceStart": 0,
            "sourceEnd": len("Alice Example"),
        })
        self.assertEqual(phone_signal["evidenceAnchor"]["selector"]["row"], 3)
        self.assertNotIn("Alice Example", serialized)
        self.assertNotIn("+49 301234567", serialized)

    def test_xlsx_label_value_rows_produce_sheet_cell_anchors_without_raw_values(self) -> None:
        body = _xlsx_bytes([
            ("Name", "Sophie de Vries"),
            ("BSN", "123456782"),
        ])

        extracted = extract_document_content(
            body=body,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            name="identity.xlsx",
        )
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        name_signal = next(signal for signal in signals if signal["type"] == "person_name")
        selector = name_signal["evidenceAnchor"]["selector"]
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "xlsx")
        self.assertEqual(name_signal["evidenceAnchor"]["fallback"]["label"], "Sheet1 row 1 column B")
        self.assertEqual(selector["type"], "tableCell")
        self.assertEqual(selector["sheetName"], "Sheet1")
        self.assertEqual(selector["row"], 1)
        self.assertEqual(selector["column"], 2)
        self.assertEqual(selector["columnLabel"], "B")
        self.assertEqual(selector["sourceStart"], 0)
        self.assertEqual(selector["sourceEnd"], len("Sophie de Vries"))
        self.assertNotIn("Sophie de Vries", serialized)
        self.assertNotIn("123456782", serialized)


def _xlsx_bytes(rows: list[tuple[str, str]]) -> bytes:
    shared_values = [value for row in rows for value in row]
    shared = "\n".join(f"<si><t>{value}</t></si>" for value in shared_values)
    sheet_rows = []
    shared_index = 0
    for row_number, _row in enumerate(rows, start=1):
        sheet_rows.append(
            f'<row r="{row_number}">'
            f'<c r="A{row_number}" t="s"><v>{shared_index}</v></c>'
            f'<c r="B{row_number}" t="s"><v>{shared_index + 1}</v></c>'
            "</row>"
        )
        shared_index += 2
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            f'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{shared}</sst>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>',
        )
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
