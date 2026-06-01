from __future__ import annotations

import unittest

from backend.lawdit.signal_risk import HIGH_RISK_SIGNAL_TYPES, public_risk_level


class SignalRiskTests(unittest.TestCase):
    def test_identity_documents_are_high_risk_for_public_and_workspace_paths(self) -> None:
        self.assertIn("passport_number", HIGH_RISK_SIGNAL_TYPES)
        self.assertIn("driver_license", HIGH_RISK_SIGNAL_TYPES)
        self.assertEqual(public_risk_level({"passport_number"}), "high")
        self.assertEqual(public_risk_level({"driver_license"}), "high")

    def test_contact_only_public_results_keep_lower_review_priority(self) -> None:
        self.assertEqual(public_risk_level({"email"}), "medium")
        self.assertEqual(public_risk_level({"organization_identifier"}), "medium")
        self.assertEqual(public_risk_level(set()), "none")


if __name__ == "__main__":
    unittest.main()
