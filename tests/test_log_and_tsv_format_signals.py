from __future__ import annotations

import json
import unittest

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content


class LogAndTsvFormatSignalTests(unittest.TestCase):
    def test_log_key_value_labels_detect_non_regex_identity_values(self) -> None:
        body = (
            'ts=2026-06-01 level=info user=alice_private passport_number=EN3457864 '
            'booking_reference=AB12CD signature="Alice Example" action=review\n'
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="text/plain", name="access_review.log")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "log")
        self.assertTrue({"account_handle", "passport_number", "travel_record", "signature"}.issubset(signal_types))
        self.assertTrue(all(signal["evidenceAnchor"]["selector"]["type"] == "textPosition" for signal in signals))
        self.assertNotIn("alice_private", serialized)
        self.assertNotIn("EN3457864", serialized)
        self.assertNotIn("AB12CD", serialized)
        self.assertNotIn("Alice Example", serialized)

    def test_signature_metadata_log_fields_do_not_create_false_findings(self) -> None:
        text = 'signature_algorithm=SHA256 passport_policy=EN3457864 user="Alice Example" build=20260601 rows=120000\n'

        self.assertEqual(detect_signals(text), [])

    def test_operational_key_value_log_fields_do_not_create_access_context_findings(self) -> None:
        text = "ts=2026-06-01 role=worker department=platform action=login status=ok rows=120000\n"

        self.assertEqual(detect_signals(text), [])

    def test_tsv_header_row_produces_multilingual_table_cell_anchors(self) -> None:
        body = (
            "旅客\tFührerschein\tPassport Number\tBooking Reference\tPhone\n"
            "陈元昊\tB1234567\tEN3457864\tAB12CD\t+49 301234567\n"
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="text/tab-separated-values", name="travel_identity.tsv")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_by_type = {signal["type"]: signal for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertEqual(extracted.file_format, "tsv")
        self.assertTrue({"person_name", "driver_license", "passport_number", "travel_record", "phone_number"}.issubset(signal_by_type))
        self.assertEqual(signal_by_type["person_name"]["evidenceAnchor"]["selector"]["columnLabel"], "A")
        self.assertEqual(signal_by_type["driver_license"]["evidenceAnchor"]["selector"]["columnLabel"], "B")
        self.assertEqual(signal_by_type["passport_number"]["evidenceAnchor"]["selector"]["columnLabel"], "C")
        self.assertEqual(signal_by_type["travel_record"]["evidenceAnchor"]["selector"]["columnLabel"], "D")
        self.assertEqual(signal_by_type["phone_number"]["evidenceAnchor"]["selector"]["columnLabel"], "E")
        self.assertTrue(all(signal["evidenceAnchor"]["selector"]["type"] == "tableCell" for signal in signal_by_type.values()))
        self.assertNotIn("陈元昊", serialized)
        self.assertNotIn("B1234567", serialized)
        self.assertNotIn("EN3457864", serialized)
        self.assertNotIn("AB12CD", serialized)
        self.assertNotIn("+49 301234567", serialized)


if __name__ == "__main__":
    unittest.main()
