"""
Compliance Agent — checks billing records against retrieved rules
and classifies any detected violations.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ─── CPT/ICD format patterns ──────────────────────────────────────────────────
_CPT_PATTERN = re.compile(r"^\d{5}$")
_ICD_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")


def check_compliance(bill: dict, retrieved_rules: list) -> list[str]:
    """
    Check billing record against retrieved rule documents.

    Args:
        bill: Billing record dict
        retrieved_rules: LangChain Documents returned by vector similarity search

    Returns:
        List of plain-text issue descriptions
    """
    issues = []
    proc = (bill.get("procedure_code") or "").strip().upper()
    diag = (bill.get("diagnosis_code") or "").strip().upper()

    # Only compare against retrieval evidence when rules are available and
    # actually contain identifiable code tokens. Missing retrieval data must not
    # be treated as a code mismatch.
    rule_codes: set[str] = set()
    for rule in retrieved_rules:
        content = rule.page_content if hasattr(rule, "page_content") else str(rule)
        tokens = re.findall(r"[A-Z]?\d{2,5}(?:\.\d{1,4})?", content.upper())
        rule_codes.update(tokens)

    logger.debug(f"Rule codes extracted from retrieval: {rule_codes}")

    if proc and retrieved_rules and rule_codes and proc not in rule_codes:
        issues.append(f"Procedure code {proc} not found in retrieved guidelines")

    if diag and retrieved_rules and rule_codes and diag not in rule_codes:
        issues.append(f"Diagnosis code {diag} not found in retrieved guidelines")

    # Insurance-specific checks
    insurance = bill.get("insurance_type", "")
    age = bill.get("patient_age")

    if insurance == "Medicare" and age is not None and age < 65:
        issues.append(
            "Patient age may not meet Medicare eligibility criteria (typically 65+)"
        )

    if insurance == "Medicaid" and age is not None and age > 64:
        issues.append(
            "Patient age may not meet standard Medicaid criteria — verify eligibility"
        )

    if not issues:
        issues.append("Billing appears compliant")

    return issues


def classify_violations(
    bill: dict, retrieved_rules: list, issues: list
) -> list[dict]:
    """
    Classify detected issues into structured violation objects.

    Args:
        bill: Billing record dict
        retrieved_rules: Retrieved rule documents (unused here but available for extension)
        issues: Plain-text issues from check_compliance()

    Returns:
        List of violation dicts: {type, description, severity}
    """
    violations = []

    for issue in issues:
        if "not found in retrieved guidelines" in issue and "Procedure" in issue:
            violations.append({
                "type": "Procedure Code Mismatch",
                "description": (
                    "Procedure code may not be supported or is not documented "
                    "in the available service records"
                ),
                "severity": "High",
            })

        elif "not found in retrieved guidelines" in issue and "Diagnosis" in issue:
            violations.append({
                "type": "Diagnosis Mismatch",
                "description": (
                    "Diagnosis code does not align with the procedure performed "
                    "or is absent from retrieved guidelines"
                ),
                "severity": "Medium",
            })

        elif "Medicare eligibility" in issue:
            violations.append({
                "type": "Insurance Eligibility",
                "description": issue,
                "severity": "High",
            })

        elif "Medicaid" in issue:
            violations.append({
                "type": "Insurance Eligibility",
                "description": issue,
                "severity": "Medium",
            })

    # ✅ Fix: Validate CPT format using regex (not just length)
    proc = (bill.get("procedure_code") or "").strip().upper()
    if proc and not _CPT_PATTERN.match(proc):
        violations.append({
            "type": "Invalid Code Format",
            "description": (
                f"Procedure code '{proc}' does not match the required 5-digit CPT format"
            ),
            "severity": "High",
        })

    # ✅ Fix: Validate ICD-10 format using regex
    diag = (bill.get("diagnosis_code") or "").strip().upper()
    if diag and not _ICD_PATTERN.match(diag):
        violations.append({
            "type": "Invalid Code Format",
            "description": (
                f"Diagnosis code '{diag}' does not match the ICD-10 format (e.g. J06.9)"
            ),
            "severity": "High",
        })

    logger.info(
        f"Classified {len(violations)} violation(s) from {len(issues)} issue(s)"
    )
    return violations