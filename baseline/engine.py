"""A deterministic, network-free baseline billing assessor."""

import re

_CPT_PATTERN = re.compile(r"^\d{5}$")
_ICD_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")


def assess_bill(bill: dict) -> dict:
    """Assess code formats and return a stable result for benchmarking."""
    procedure_code = str(bill.get("procedure_code", "")).strip().upper()
    diagnosis_code = str(bill.get("diagnosis_code", "")).strip().upper()
    violations = []

    if not _CPT_PATTERN.fullmatch(procedure_code):
        violations.append("Invalid procedure code format")
    if not _ICD_PATTERN.fullmatch(diagnosis_code):
        violations.append("Invalid diagnosis code format")

    return {
        "compliance_status": "Compliant" if not violations else "Non-Compliant",
        "violations": violations,
        "engine": "deterministic-baseline",
    }