import unittest

from agents.compliance_agent import check_compliance


class ComplianceValidationTests(unittest.TestCase):
    def test_no_retrieval_evidence_does_not_trigger_cpt_mismatch(self):
        bill = {"procedure_code": "99213", "diagnosis_code": "J06.9"}

        issues = check_compliance(bill, [])

        self.assertFalse(
            any("not found in retrieved guidelines" in issue for issue in issues),
            "Missing retrieval evidence should not be treated as a code mismatch",
        )

    def test_valid_cpt_icd_format_is_not_flagged_when_guidelines_are_unavailable(self):
        bill = {"procedure_code": "99213", "diagnosis_code": "J06.9"}

        issues = check_compliance(bill, [])

        self.assertIn("Billing appears compliant", issues)


if __name__ == "__main__":
    unittest.main()
