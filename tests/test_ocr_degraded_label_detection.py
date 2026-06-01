from __future__ import annotations

import json
import unittest

from backend.lawdit.deterministic_signals import detect_signals


class OcrDegradedLabelDetectionTests(unittest.TestCase):
    def test_passport_label_survives_missing_ocr_separator_without_false_positive(self) -> None:
        signals = detect_signals("Passport EN3457864\n")
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals)

        self.assertIn("passport_number", signal_types)
        self.assertNotIn("EN3457864", serialized)
        self.assertEqual(detect_signals("Passport applications are due Friday\n"), [])
        self.assertEqual(detect_signals("Passport pending review\n"), [])

    def test_travel_overlay_ocr_text_detects_all_identity_fields(self) -> None:
        text = "姓名：梁思源\n地址：Paulinestr. 13 Heilbronn 74076\nPassport EN3457864\n"

        signals = detect_signals(text)
        signal_types = {signal["type"] for signal in signals}
        serialized = json.dumps(signals, ensure_ascii=False)

        self.assertTrue({"person_name", "address", "passport_number"}.issubset(signal_types))
        self.assertNotIn("梁思源", serialized)
        self.assertNotIn("Paulinestr. 13 Heilbronn 74076", serialized)
        self.assertNotIn("EN3457864", serialized)

    def test_clean_receipt_and_sku_amounts_do_not_trigger_personal_amounts(self) -> None:
        text = "STORE RECEIPT\nTotal EUR 62000\nSKU AB12345678\nBatch FR1234567890\n"

        signal_types = {signal["type"] for signal in detect_signals(text)}

        self.assertNotIn("expense_amount", signal_types)
        self.assertNotIn("tax_id", signal_types)

    def test_clean_stacked_product_labels_do_not_trigger_person_names(self) -> None:
        text = "Release Name\nPhoenix\nBuild Owner\nPlatform Team\nPassport applications\nDue Friday\n"

        self.assertEqual(detect_signals(text), [])


if __name__ == "__main__":
    unittest.main()
