"""
CPT Code Lookup — returns procedure descriptions for CPT codes.

Currently uses a local reference dictionary.
Replace `_CPT_DB` with a real API call (e.g. AMA API) when available.
"""

import logging

logger = logging.getLogger(__name__)

# ✅ Fix: Remove unused `import requests`
# ✅ Fix: Explicit local lookup with clear comment that this is intentional
# Replace with a real API call to the AMA CPT database in production.

_CPT_DB: dict[str, str] = {
    # Evaluation & Management — Office Visits (New Patient)
    "99201": "Office visit - new patient, straightforward medical decision making",
    "99202": "Office visit - new patient, straightforward, 15-29 min",
    "99203": "Office visit - new patient, low complexity, 30-44 min",
    "99204": "Office visit - new patient, moderate complexity, 45-59 min",
    "99205": "Office visit - new patient, high complexity, 60-74 min",
    # Evaluation & Management — Office Visits (Established Patient)
    "99211": "Office visit - established patient, minimal, 5-10 min",
    "99212": "Office visit - established patient, straightforward, 10-19 min",
    "99213": "Office visit - established patient, low complexity, 20-29 min",
    "99214": "Office visit - established patient, moderate complexity, 30-39 min",
    "99215": "Office visit - established patient, high complexity, 40-54 min",
    # Preventive Medicine
    "99381": "Initial comprehensive preventive medicine visit, infant (<1 year)",
    "99382": "Initial comprehensive preventive medicine visit, early childhood (1-4 years)",
    "99383": "Initial comprehensive preventive medicine visit, late childhood (5-11 years)",
    "99384": "Initial comprehensive preventive medicine visit, adolescent (12-17 years)",
    "99385": "Initial comprehensive preventive medicine visit, 18-39 years",
    "99386": "Initial comprehensive preventive medicine visit, 40-64 years",
    "99387": "Initial comprehensive preventive medicine visit, 65+ years",
    # Telehealth
    "99421": "Online digital E/M service - 5-10 minutes",
    "99422": "Online digital E/M service - 11-20 minutes",
    "99423": "Online digital E/M service - 21+ minutes",
    # Radiology
    "71046": "Chest X-ray, 2 views",
    "93000": "Electrocardiogram, 12-lead with interpretation and report",
    # Laboratory
    "80053": "Comprehensive metabolic panel",
    "85025": "Complete blood count (CBC) with automated differential",
    "83036": "Hemoglobin A1c",
}


def fetch_cpt_code(code: str) -> list[dict]:
    """
    Look up a CPT procedure code description.

    Args:
        code: 5-digit CPT code string (e.g. "99213")

    Returns:
        List with a single dict: [{"code": ..., "description": ...}]
        Returns a placeholder entry for unknown codes (never crashes).
    """
    if not code or not code.strip():
        logger.warning("fetch_cpt_code called with empty code")
        return []

    code = code.strip().upper()
    description = _CPT_DB.get(code)

    if description:
        logger.info(f"CPT code {code} found in local lookup")
        return [{"code": code, "description": description}]

    # ✅ Return a placeholder rather than crashing — compliance agent
    # will flag this as a mismatch if it can't find it in retrieved rules
    logger.warning(
        f"CPT code {code} not found in local lookup — "
        "consider connecting to AMA CPT API for full coverage"
    )
    return [{"code": code, "description": f"Unrecognised procedure code {code}"}]