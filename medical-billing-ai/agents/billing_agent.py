"""
Billing Agent — fetches external code data for a given billing record.
"""

import logging
from services.icd_api import fetch_icd_data
from services.cpt_api import fetch_cpt_code

logger = logging.getLogger(__name__)


def gather_billing_context(bill: dict) -> tuple[list, list]:
    """
    Fetch ICD-10 and CPT code data from external/local sources.

    Args:
        bill: Dict containing at minimum 'procedure_code' and 'diagnosis_code'

    Returns:
        Tuple of (icd_data, cpt_data) — each a list of dicts

    Raises:
        ValueError: If required codes are missing
    """
    # ✅ Fix: Use .get() with .strip() — never direct key access
    icd_code = (bill.get("diagnosis_code") or "").strip()
    cpt_code = (bill.get("procedure_code") or "").strip()

    if not icd_code or not cpt_code:
        raise ValueError(
            "Both 'diagnosis_code' and 'procedure_code' are required"
        )

    logger.info(f"Fetching context for CPT={cpt_code}, ICD={icd_code}")

    # ✅ Fix: Default to empty list if API returns None
    icd_data = fetch_icd_data(icd_code) or []
    cpt_data = fetch_cpt_code(cpt_code) or []

    if not icd_data:
        logger.warning(f"No ICD data returned for code: {icd_code}")
    if not cpt_data:
        logger.warning(f"No CPT data returned for code: {cpt_code}")

    logger.info(
        f"Context fetched — {len(icd_data)} ICD result(s), "
        f"{len(cpt_data)} CPT result(s)"
    )
    return icd_data, cpt_data