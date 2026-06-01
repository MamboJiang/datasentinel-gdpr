from __future__ import annotations

import json
import unittest

from backend.lawdit.deterministic_signals import detect_signals
from backend.lawdit.signal_evidence_anchors import apply_source_locations
from backend.lawdit.source_format_recognition import extract_document_content


class TravelIdentitySignalTests(unittest.TestCase):
    def test_multilingual_travel_license_and_signature_labels_are_redacted(self) -> None:
        cases = {
            "de": (
                "Reisender: Anna Becker\n"
                "Führerschein: B1234567\n"
                "Buchungsnummer: AB12CD\n"
                "Unterschrift: Anna Becker\n"
            ),
            "zh": (
                "旅客：陈元昊\n"
                "驾驶证号：沪C1234567\n"
                "预订编号：CN88TRIP\n"
                "签名：陈元昊\n"
            ),
        }

        for name, text in cases.items():
            with self.subTest(case=name):
                signals = detect_signals(text)
                signal_types = {signal["type"] for signal in signals}
                serialized = json.dumps(signals, ensure_ascii=False)

                self.assertTrue({"person_name", "driver_license", "travel_record", "signature"}.issubset(signal_types))
                self.assertIn("[REDACTED_DRIVER_LICENSE]", serialized)
                self.assertIn("[REDACTED_TRAVEL_RECORD]", serialized)
                self.assertIn("[REDACTED_SIGNATURE]", serialized)
                self.assertNotIn("Anna Becker", serialized)
                self.assertNotIn("陈元昊", serialized)
                self.assertNotIn("B1234567", serialized)
                self.assertNotIn("沪C1234567", serialized)

    def test_csv_travel_identity_headers_keep_table_cell_anchors(self) -> None:
        body = (
            "Passenger,Driver License,Username,Signature,Booking Reference\n"
            "Alice Example,D1234567,@alice_private,Alice Example,AB12CD"
        ).encode("utf-8")

        extracted = extract_document_content(body=body, content_type="text/csv", name="travel_review_identity.csv")
        signals = apply_source_locations(detect_signals(extracted.text), extracted.text_locations)
        signal_by_type = {signal["type"]: signal for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertTrue({"person_name", "driver_license", "account_handle", "signature", "travel_record"}.issubset(signal_by_type))
        self.assertEqual(signal_by_type["person_name"]["evidenceAnchor"]["selector"]["columnLabel"], "A")
        self.assertEqual(signal_by_type["driver_license"]["evidenceAnchor"]["selector"]["columnLabel"], "B")
        self.assertEqual(signal_by_type["account_handle"]["evidenceAnchor"]["selector"]["columnLabel"], "C")
        self.assertEqual(signal_by_type["signature"]["evidenceAnchor"]["selector"]["columnLabel"], "D")
        self.assertEqual(signal_by_type["travel_record"]["evidenceAnchor"]["selector"]["columnLabel"], "E")
        self.assertTrue(all(signal["evidenceAnchor"]["selector"]["type"] == "tableCell" for signal in signal_by_type.values()))
        self.assertNotIn("Alice Example", serialized)
        self.assertNotIn("D1234567", serialized)
        self.assertNotIn("@alice_private", serialized)
        self.assertNotIn("AB12CD", serialized)

    def test_signature_algorithm_metadata_does_not_create_person_or_signature_signal(self) -> None:
        signals = detect_signals("signature_algorithm: SHA256\nSignature algorithm: SHA256\n")

        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
