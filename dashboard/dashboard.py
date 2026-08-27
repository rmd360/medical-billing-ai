"""
Streamlit Dashboard — Medical Billing Compliance Auditor
Run with: streamlit run dashboard.py
"""

import json
import logging
import os
import re
from datetime import datetime

import requests
import streamlit as st

logger = logging.getLogger(__name__)

API_URL = os.getenv("MEDICAL_BILLING_API_URL", "http://127.0.0.1:8001/audit-bill")
_CPT_PATTERN = re.compile(r"^\d{5}$")
_ICD_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Medical Billing Compliance",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styles ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.compliant-box {
    background: #e8f5e9;
    padding: 15px;
    border-left: 4px solid #4caf50;
    border-radius: 5px;
    margin-bottom: 10px;
}
.violation-box {
    background: #ffebee;
    padding: 15px;
    border-left: 4px solid #f44336;
    border-radius: 5px;
    margin-bottom: 10px;
}
.disclaimer {
    background: #fff8e1;
    padding: 12px;
    border-left: 4px solid #ffc107;
    border-radius: 5px;
    font-size: 0.85em;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)


# ─── Helper functions (✅ Fix: defined BEFORE they are called) ─────────────────

def generate_text_report(result: dict, payload: dict) -> str:
    """Render a plain-text compliance report."""
    return (
        "MEDICAL BILLING COMPLIANCE REPORT\n"
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "\nSUBMISSION DETAILS:\n"
        f"  Procedure Code : {payload.get('procedure_code')}\n"
        f"  Diagnosis Code : {payload.get('diagnosis_code')}\n"
        f"  Service        : {payload.get('service') or 'N/A'}\n"
        f"  Insurance Type : {payload.get('insurance_type') or 'N/A'}\n"
        f"  Patient Age    : {payload.get('patient_age') or 'N/A'}\n"
        "\nCOMPLIANCE ASSESSMENT:\n"
        f"  Status         : {result.get('compliance_status')}\n"
        f"  Confidence     : {result.get('confidence_score', 0):.1%}\n"
        f"  Code Validity  : {result.get('code_validity', 'Unknown')}\n"
        "\nVIOLATIONS:\n"
        f"{_format_violations(result.get('violations', []))}\n"
        "\nRECOMMENDED CORRECTIONS:\n"
        f"{_format_list(result.get('recommended_corrections', []))}\n"
        "\nPOLICY REFERENCES:\n"
        f"{_format_citations(result.get('policy_citations', []))}\n"
        "\nAGENT REASONING:\n"
        f"{result.get('agent_reasoning', 'Not available')}\n"
    )


def _format_violations(violations: list) -> str:
    if not violations:
        return "  No violations found."
    return "\n".join(
        f"  [{v.get('severity', 'N/A')}] {v.get('type', 'Issue')}: "
        f"{v.get('description', 'N/A')}"
        for v in violations
    )


def _format_list(items: list) -> str:
    if not items:
        return "  None."
    return "\n".join(f"  {i+1}. {item}" for i, item in enumerate(items))


def _format_citations(citations: list) -> str:
    if not citations:
        return "  No policy citations available."
    return "\n".join(
        f"  - {c.get('source', 'N/A')}: {c.get('text', 'N/A')}"
        for c in citations
    )


def _confidence_color(score: float) -> str:
    if score >= 0.90:
        return "🟢"
    if score >= 0.70:
        return "🟡"
    return "🔴"


def _format_api_error(response: requests.Response) -> str:
    """Return a useful, user-facing message from a failed API response."""
    try:
        detail = response.json().get("detail", "Request failed")
    except (ValueError, AttributeError):
        return f"Request failed with status {response.status_code}."

    if isinstance(detail, list):
        return "; ".join(
            error.get("msg", "Invalid input")
            for error in detail
            if isinstance(error, dict)
        ) or "Invalid input."
    return str(detail)


# ─── Session state init ───────────────────────────────────────────────────────

if "submission_history" not in st.session_state:
    st.session_state.submission_history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_payload" not in st.session_state:
    st.session_state.last_payload = None


# ─── Sidebar — session history ────────────────────────────────────────────────

with st.sidebar:
    st.header("📋 Session History")

    if st.session_state.submission_history:
        for i, item in enumerate(st.session_state.submission_history[:10]):
            icon = "✅" if item["status"] == "Compliant" else "⚠️"
            with st.expander(f"{icon} {item['time']} — {item['procedure_code']}"):
                st.write(f"**Procedure:** {item['procedure_code']}")
                st.write(f"**Diagnosis:** {item['diagnosis_code']}")
                st.write(f"**Status:** {item['status']}")
                st.write(f"**Confidence:** {item['confidence']:.1%}")
    else:
        st.info("No submissions yet")

    st.markdown("---")

    # ✅ Added: HIPAA / disclaimer notice
    st.markdown("""
    <div class="disclaimer">
    ⚠️ <strong>Disclaimer:</strong> This tool provides AI-assisted compliance
    guidance only. It does not constitute professional medical billing advice.
    Do not enter real patient PHI. Consult a certified medical billing specialist
    for final compliance decisions.
    </div>
    """, unsafe_allow_html=True)


# ─── Page header ──────────────────────────────────────────────────────────────

st.title("🏥 Medical Billing Compliance Auditor")
st.markdown("---")

# ─── Two-column layout ────────────────────────────────────────────────────────

col_form, col_status = st.columns([1, 1])

# Left column — input form
with col_form:
    st.header("📝 Enter Billing Information")

    with st.form("billing_form"):
        procedure_code = st.text_input(
            "Procedure Code (CPT) *",
            placeholder="e.g., 99213",
            help="Current Procedural Terminology code — 5 digits",
        )
        diagnosis_code = st.text_input(
            "Diagnosis Code (ICD-10) *",
            placeholder="e.g., J06.9",
            help="International Classification of Diseases code",
        )
        service = st.text_input(
            "Service Description",
            placeholder="e.g., Office visit - established patient",
        )

        col_age, col_ins = st.columns(2)
        with col_age:
            patient_age = st.number_input(
                "Patient Age", min_value=0, max_value=120, value=None, step=1
            )
        with col_ins:
            insurance_type = st.selectbox(
                "Insurance Type",
                ["Medicare", "Medicaid", "Commercial", "Self-Pay", "Other"],
            )

        submitted = st.form_submit_button(
            "🔍 Check Compliance", use_container_width=True
        )

# Right column — live quick status
with col_status:
    st.header("📊 Quick Status")

    if st.session_state.last_result:
        r = st.session_state.last_result
        confidence = r.get("confidence_score", 0)
        violations = r.get("violations", [])

        st.metric(
            "Compliance Status",
            r.get("compliance_status", "Unknown"),
        )
        st.metric(
            "Confidence Score",
            f"{_confidence_color(confidence)} {confidence:.1%}",
        )
        st.metric("Issues Found", len(violations))
        st.metric("Code Validity", r.get("code_validity", "Unknown"))
    else:
        st.info("Submit a billing record to see results here.")


# ─── Form submission handler ──────────────────────────────────────────────────

if submitted:
    st.session_state.last_result = None
    st.session_state.last_payload = None

    if not procedure_code or not diagnosis_code:
        st.error("⚠️ Procedure Code and Diagnosis Code are both required.")
    elif not _CPT_PATTERN.fullmatch(procedure_code.strip()):
        st.error("⚠️ CPT code must be exactly 5 digits (for example, 99213).")
    elif not _ICD_PATTERN.fullmatch(diagnosis_code.strip().upper()):
        st.error("⚠️ ICD-10 code format is invalid (for example, J06.9).")
    else:
        payload = {
            "procedure_code": procedure_code.strip(),
            "diagnosis_code": diagnosis_code.strip(),
            "service": service.strip() if service else None,
            "patient_age": int(patient_age) if patient_age is not None else None,
            "insurance_type": insurance_type,
        }

        with st.spinner("🔄 Analysing billing compliance…"):
            try:
                response = requests.post(API_URL, json=payload, timeout=30)

                # ✅ Fix: Handle 422 validation errors from FastAPI
                if response.status_code == 422:
                    st.error(f"⚠️ Invalid input: {_format_api_error(response)}")
                    st.stop()

                response.raise_for_status()
                result = response.json()

                # Cache results
                st.session_state.last_result = result
                st.session_state.last_payload = payload
                st.session_state.submission_history.insert(0, {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "procedure_code": procedure_code,
                    "diagnosis_code": diagnosis_code,
                    "status": result.get("compliance_status", "Unknown"),
                    "confidence": result.get("confidence_score", 0),
                })

            except requests.Timeout:
                st.error("⏱️ Request timed out. Is the backend running?")
                st.stop()
            except requests.ConnectionError:
                st.error(
                    "🔌 Cannot connect to the backend. "
                    "Start it with: `uvicorn app:app --reload`"
                )
                st.stop()
            except requests.HTTPError as e:
                st.error(f"❌ Server error: {_format_api_error(response)}")
                st.stop()
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                st.stop()

        st.success("✅ Analysis complete!")


# ─── Results display ──────────────────────────────────────────────────────────

if st.session_state.last_result:
    result = st.session_state.last_result
    payload = st.session_state.last_payload or {}

    st.markdown("---")
    st.subheader("🎯 Compliance Assessment")

    # Status banner
    status = result.get("compliance_status")
    if status == "Compliant":
        st.markdown(
            '<div class="compliant-box"><strong>✅ Status: Compliant</strong></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="violation-box"><strong>⚠️ Status: Non-Compliant</strong></div>',
            unsafe_allow_html=True,
        )

    # Metrics row
    confidence = result.get("confidence_score", 0)
    m1, m2, m3 = st.columns(3)
    m1.metric("Confidence", f"{confidence:.1%}")
    m2.metric("Issues Found", len(result.get("violations", [])))
    m3.metric("Code Status", result.get("code_validity", "Unknown"))

    # Violations
    violations = result.get("violations", [])
    if violations:
        st.subheader("⚠️ Violations & Issues")
        for v in violations:
            severity = v.get("severity", "Medium")
            icon_map = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
            col_desc, col_sev = st.columns([4, 1])
            with col_desc:
                st.write(
                    f"**{v.get('type', 'Issue')}**: {v.get('description', 'N/A')}"
                )
            with col_sev:
                st.write(f"{icon_map.get(severity, '•')} {severity}")

    # Recommended corrections
    corrections = result.get("recommended_corrections", [])
    if corrections:
        st.subheader("💡 Recommended Corrections")
        for i, correction in enumerate(corrections, 1):
            st.write(f"{i}. {correction}")

    # Policy citations (RAG grounding)
    citations = result.get("policy_citations", [])
    if citations:
        st.subheader("📚 Policy References")
        with st.expander("View Policy Citations"):
            for citation in citations:
                st.write(
                    f"**{citation.get('source', 'N/A')}**"
                    f"{' — ' + citation.get('code') if citation.get('code') else ''}: "
                    f"{citation.get('text', 'N/A')}"
                )

    # Agent reasoning
    reasoning = result.get("agent_reasoning", "")
    if reasoning:
        st.subheader("🤖 Agent Analysis Trace")
        with st.expander("View Reasoning Process"):
            st.code(reasoning, language=None)

    # ✅ Fix: Download buttons shown directly — no nested button hack
    st.subheader("📥 Export Report")
    exp1, exp2 = st.columns(2)

    with exp1:
        st.download_button(
            label="📄 Download JSON",
            data=json.dumps(result, indent=2),
            file_name=f"compliance_{payload.get('procedure_code', 'report')}.json",
            mime="application/json",
            use_container_width=True,
        )
    with exp2:
        st.download_button(
            label="📝 Download Text Report",
            data=generate_text_report(result, payload),
            file_name=f"compliance_{payload.get('procedure_code', 'report')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        