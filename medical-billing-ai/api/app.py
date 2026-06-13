"""
FastAPI application — Medical Billing Compliance Auditor
Run with: uvicorn app:app --reload
"""

import logging
import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from main import run_pipeline

# ✅ Load environment variables from .env file at startup
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan (replaces deprecated @app.on_event) ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Medical Billing API starting up…")
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY not set — vector store will use FallbackDB. "
            "Set the key in your .env file for full RAG functionality."
        )
    yield
    logger.info("Medical Billing API shutting down…")


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Medical Billing Compliance API",
    description="AI-powered API for auditing medical billing compliance",
    version="1.0.0",
    lifespan=lifespan,
)

# ✅ CORS — tighten origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit dev origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response schemas ───────────────────────────────────────────────

class BillingRecord(BaseModel):
    """Schema for a billing record submission."""

    procedure_code: str
    diagnosis_code: str
    service: str = None
    patient_age: int = None
    insurance_type: str = None

    # ✅ Fix: Validate CPT format (exactly 5 digits)
    @field_validator("procedure_code")
    @classmethod
    def validate_cpt(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^\d{5}$", v):
            raise ValueError(
                "CPT code must be exactly 5 digits (e.g. 99213)"
            )
        return v

    # ✅ Fix: Validate ICD-10 format (e.g. J06.9, E11, M54.5)
    @field_validator("diagnosis_code")
    @classmethod
    def validate_icd(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z]\d{2}(\.\d{1,4})?$", v):
            raise ValueError(
                "ICD-10 code format is invalid (e.g. J06.9, E11.9)"
            )
        return v

    # ✅ Fix: Validate age range
    @field_validator("patient_age")
    @classmethod
    def validate_age(cls, v):
        if v is not None and not (0 <= v <= 120):
            raise ValueError("Patient age must be between 0 and 120")
        return v

    # ✅ Fix: Validate insurance type against known values
    @field_validator("insurance_type")
    @classmethod
    def validate_insurance(cls, v):
        allowed = {"Medicare", "Medicaid", "Commercial", "Self-Pay", "Other"}
        if v and v not in allowed:
            raise ValueError(f"Insurance type must be one of: {', '.join(sorted(allowed))}")
        return v


# ─── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Medical Billing Compliance Auditor API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers / monitoring."""
    return {
        "status": "healthy",
        "service": "medical-billing-api",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/audit-bill")
def audit_bill(bill: BillingRecord):
    """
    Audit a medical billing record for compliance.

    - **procedure_code**: 5-digit CPT code (e.g. 99213)
    - **diagnosis_code**: ICD-10 code (e.g. J06.9)
    - **service**: Free-text description of the service
    - **patient_age**: Integer 0–120
    - **insurance_type**: Medicare | Medicaid | Commercial | Self-Pay | Other
    """
    logger.info(
        f"Audit request: CPT={bill.procedure_code} ICD={bill.diagnosis_code} "
        f"insurance={bill.insurance_type} age={bill.patient_age}"
    )

    try:
        result = run_pipeline(bill.model_dump())
        logger.info(f"Audit complete: status={result.get('compliance_status')}")
        return result

    except ValueError as e:
        # Input / validation error — 422 Unprocessable Entity
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except RuntimeError as e:
        # Pipeline error — 500
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))