"""
Medical Billing Compliance Pipeline
Entry point for running the full audit pipeline.
"""

import sys
import os
import logging

# ✅ Fix: sys.path must be set BEFORE any local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.billing_agent import gather_billing_context
from agents.compliance_agent import check_compliance, classify_violations
from rag.embedding_pipeline import convert_to_documents
from rag.vector_store import build_vector_store, get_cached_store
from rag.retrieval import retrieve_rules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Fix: Required fields validated upfront
REQUIRED_FIELDS = ["procedure_code", "diagnosis_code"]


def run_pipeline(bill: dict) -> dict:
    """
    Run the complete billing compliance pipeline.

    Args:
        bill: Dict with keys: procedure_code, diagnosis_code,
              service, patient_age, insurance_type

    Returns:
        Comprehensive compliance report dict with:
        - compliance_status
        - confidence_score
        - code_validity
        - violations
        - recommended_corrections
        - policy_citations
        - agent_reasoning
    """
    # ✅ Fix: Validate input before touching any downstream code
    missing = [f for f in REQUIRED_FIELDS if not bill.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    try:
        logger.info(
            f"Starting pipeline for CPT={bill.get('procedure_code')} "
            f"ICD={bill.get('diagnosis_code')}"
        )

        # Step 1 — Fetch external code data
        icd_data, cpt_data = gather_billing_context(bill)

        # ✅ Fix: Guard against None returns from APIs
        icd_data = icd_data or []
        cpt_data = cpt_data or []

        # Step 2 — Convert to LangChain Documents
        docs = convert_to_documents(icd_data, source="icd_api") + \
               convert_to_documents(cpt_data, source="cpt_api")

        # Step 3 — Build / reuse cached vector store
        # ✅ Fix: Don't rebuild the FAISS index on every call
        db = get_cached_store(docs)

        # Step 4 — Retrieve relevant rules via similarity search
        rules = retrieve_rules(db, str(bill), k=5)

        # Step 5 — Compliance check & violation classification
        issues = check_compliance(bill, rules)
        violations = classify_violations(bill, rules, issues)

        # Step 6 — Derived outputs
        policy_citations = _extract_policy_citations(rules)
        compliance_status = "Compliant" if not violations else "Non-Compliant"
        confidence_score = _calculate_confidence(violations, rules)
        corrections = _generate_corrections(violations)
        reasoning = _generate_reasoning_trace(bill, issues, violations)

        code_validity = (
            "Invalid"
            if any(v.get("type") == "Invalid Code Format" for v in violations)
            else "Valid"
        )

        result = {
            "compliance_status": compliance_status,
            "confidence_score": confidence_score,
            "code_validity": code_validity,
            "violations": violations,
            "issues_detected": issues,
            "recommended_corrections": corrections,
            "policy_citations": policy_citations,
            "agent_reasoning": reasoning,
        }

        logger.info(
            f"Pipeline complete — status={compliance_status}, "
            f"confidence={confidence_score:.2f}, violations={len(violations)}"
        )
        return result

    except ValueError:
        raise  # Re-raise validation errors for FastAPI to catch
    except Exception as e:
        logger.exception("Unexpected error in pipeline")
        raise RuntimeError(f"Pipeline failed: {str(e)}") from e


# ─── Private helpers ──────────────────────────────────────────────────────────

def _extract_policy_citations(rules: list) -> list:
    """Extract policy citations from retrieved rules (RAG grounding)."""
    citations = []
    for rule in rules[:3]:
        if hasattr(rule, "metadata") and hasattr(rule, "page_content"):
            citations.append({
                "source": rule.metadata.get("source", "Medical API"),
                "code": rule.metadata.get("code", ""),
                "text": rule.page_content[:300],
            })

    return citations or [
        {
            "source": "CMS Guidelines",
            "code": "",
            "text": (
                "Billing codes must match documented medical necessity "
                "and the services actually rendered."
            ),
        }
    ]


def _calculate_confidence(violations: list, rules: list) -> float:
    """
    Calculate AI confidence in the assessment.

    Starts at 0.95 and is reduced by:
    - Sparse rule retrieval (fewer than 3 rules)
    - Violation severity
    """
    # ✅ Fix: Penalise sparse retrieval instead of assuming full confidence
    base = 0.95 if len(rules) >= 3 else 0.75

    severity_weights = {"High": 0.25, "Medium": 0.10, "Low": 0.03}
    for violation in violations:
        base -= severity_weights.get(violation.get("severity", "Low"), 0.03)

    return round(max(0.40, min(0.95, base)), 2)


def _generate_corrections(violations: list) -> list:
    """Generate recommended corrections based on violations found."""
    correction_map = {
        "Procedure Code Mismatch": (
            "Verify the procedure code matches the documented service provided"
        ),
        "Diagnosis Mismatch": (
            "Ensure the diagnosis code reflects the primary condition treated"
        ),
        "Invalid Code Format": (
            "Replace with a valid, currently active procedure/diagnosis code"
        ),
        "Modifier Required": (
            "Add the appropriate modifier to the code (consult billing guidelines)"
        ),
        "Medical Necessity": (
            "Document additional clinical justification for the service"
        ),
    }

    corrections = []
    for v in violations:
        v_type = v.get("type", "")
        corrections.append(
            correction_map.get(v_type, f"Address the {v_type.lower()} issue")
        )

    return corrections or ["Billing appears compliant — no corrections needed"]


def _generate_reasoning_trace(bill: dict, issues: list, violations: list) -> str:
    """Generate a human-readable trace of how the AI reached its decision."""
    # ✅ Fix: Build issues text separately to avoid chr(10) hack in f-string
    issues_text = "\n".join(f"   - {issue}" for issue in issues) or "   - None"

    high = sum(1 for v in violations if v.get("severity") == "High")
    medium = sum(1 for v in violations if v.get("severity") == "Medium")
    low = sum(1 for v in violations if v.get("severity") == "Low")

    conclusion = "Compliant" if not violations else "Non-Compliant"

    return (
        f"ANALYSIS PROCESS:\n"
        f"1. Code Analysis:\n"
        f"   - Procedure Code : {bill.get('procedure_code')} "
        f"{'✓' if not any(v.get('type') == 'Procedure Code Mismatch' for v in violations) else '✗'}\n"
        f"   - Diagnosis Code : {bill.get('diagnosis_code')} "
        f"{'✓' if not any(v.get('type') == 'Diagnosis Mismatch' for v in violations) else '✗'}\n"
        f"   - Insurance Type : {bill.get('insurance_type', 'N/A')}\n"
        f"   - Patient Age    : {bill.get('patient_age', 'N/A')}\n\n"
        f"2. Issues Identified: {len(violations)} finding(s)\n"
        f"{issues_text}\n\n"
        f"3. Severity Breakdown: "
        f"{high} high | {medium} medium | {low} low\n\n"
        f"4. Conclusion: {conclusion} with medical billing regulations"
    )