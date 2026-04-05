"""
schemas.py
Pydantic models for request validation and response serialization.
"""

from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


# ─── Request Models ───────────────────────────────────────────────────────────

class LabResults(BaseModel):
    hemoglobin: float = Field(..., description="g/dL")
    WBC: float = Field(..., description="×10³/µL")
    platelets: float = Field(..., description="×10³/µL")
    blood_sugar: float = Field(..., description="mg/dL")
    cholesterol: float = Field(..., description="mg/dL")


class CaseInput(BaseModel):
    age: int = Field(..., ge=0, le=130, description="Patient age in years")
    gender: str = Field(..., description="Patient gender")
    symptoms: list[str] = Field(..., min_length=1, description="Reported symptoms")
    diagnosis: str = Field(..., description="Clinician's preliminary diagnosis")
    medications: list[str] = Field(..., description="Current medications")
    lab_results: LabResults


# ─── Response Models ──────────────────────────────────────────────────────────

class AlertType(str, Enum):
    DIAGNOSIS_MISMATCH = "diagnosis_mismatch"
    DRUG_INTERACTION = "drug_interaction"
    LAB_ABNORMALITY = "lab_abnormality"


class Alert(BaseModel):
    type: AlertType
    message: str
    recommended_action: str


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseAnalysisResponse(BaseModel):
    risk_level: RiskLevel
    alerts: list[Alert]